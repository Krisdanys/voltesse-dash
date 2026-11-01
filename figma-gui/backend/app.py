"""Real authenticated API for the laptop Technician GUI.

Existing driver application remains independent. DATABASE mode reads its schema.
SIMULATION mode reuses the Streamlit formulas, explicitly labeled in every response.
"""
import hashlib
import hmac
import os
import secrets
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import jwt
import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from .config import Settings
from .simulator import live_metrics, live_temperature_history

HASHER = PasswordHasher()  # Argon2id, unique cryptographic salt per password
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))
COOKIE = 'voltesse_session'
ISSUER = 'voltesse-technician'

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

class Preferences(BaseModel):
    warning_temp: int = Field(ge=40, le=110)
    warning_battery: int = Field(ge=5, le=40)


def connect(settings):
    return psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=5, prepare_threshold=None)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_for(settings, token_id):
    return hmac.new(settings.secret.encode(), ('csrf:' + token_id).encode(), hashlib.sha256).hexdigest()


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()
    app = FastAPI(title='Voltesse Technician API', docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings

    @app.middleware('http')
    async def security_headers(request, call_next):
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.url.path.startswith('/api/'):
            origin = request.headers.get('origin')
            if (origin and origin not in settings.origins) or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'Untrusted request origin.'}, status_code=403)
            if request.headers.get('x-requested-with') != 'VoltesseGUI':
                return JSONResponse({'detail': 'Missing application request header.'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        if settings.secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        # Never leak DSNs, SQL, or credentials to a browser.
        return JSONResponse({'detail': 'Database unavailable. Check backend configuration.'}, status_code=503)

    def current_user(request: Request):
        try:
            claims = jwt.decode(request.cookies.get(COOKIE, ''), settings.secret,
                                algorithms=['HS256'], issuer=ISSUER, audience='technician-gui',
                                options={'require': ['exp', 'iat', 'jti', 'sub']})
            uid = int(claims['sub'])
            token_id = claims['jti']
            if not isinstance(token_id, str):
                raise ValueError('Invalid token ID')
        except (jwt.PyJWTError, ValueError, TypeError):
            raise HTTPException(401, 'Please sign in.')
        with connect(settings) as conn:
            user = conn.execute('''SELECT u.technician_id, u.username, u.name, u.role
                FROM web_auth_session s JOIN technician_user u USING (technician_id)
                WHERE s.token_hash=%s AND s.technician_id=%s AND s.expires_at > now()''',
                (digest(token_id), uid)).fetchone()
        if not user:
            raise HTTPException(401, 'Session expired. Please sign in.')
        if user['role'] not in ('ADMIN', 'TECHNICIAN'):
            raise HTTPException(403, 'Technician access required.')
        if request.method not in ('GET', 'HEAD'):
            if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), csrf_for(settings, token_id)):
                raise HTTPException(403, 'Invalid request token.')
        user['token_id'] = token_id
        return user

    User = Annotated[dict, Depends(current_user)]

    @app.get('/api/health')
    def health():
        return {'status': 'ok'}

    @app.post('/api/auth/login')
    def login(body: Login, request: Request, response: Response):
        username = body.username.strip().lower()
        # Account + IP buckets are persisted, bounded, and locked before checking passwords.
        # Ignore forwarded IP headers: local proxy traffic shares a conservative IP limit.
        ip = request.client.host if request.client else 'unknown'
        buckets = sorted([(digest('user:' + username), 5), (digest('ip:' + ip), 30)])
        error = None
        user = None
        with connect(settings) as conn:
            conn.execute("DELETE FROM web_login_throttle WHERE window_start < now() - interval '15 minutes'")
            conn.execute('DELETE FROM web_auth_session WHERE expires_at <= now()')
            locked = []
            for key, limit in buckets:
                conn.execute('INSERT INTO web_login_throttle(bucket,attempts) VALUES (%s,0) ON CONFLICT DO NOTHING', (key,))
                row = conn.execute('SELECT * FROM web_login_throttle WHERE bucket=%s FOR UPDATE', (key,)).fetchone()
                locked.append((row, limit))
            if any(row['attempts'] >= limit for row, limit in locked):
                error = 429
            else:
                user = conn.execute('SELECT * FROM technician_user WHERE username=%s', (username,)).fetchone()
                try:
                    valid = HASHER.verify(user['password_hash'] if user else DUMMY_HASH, body.password)
                except (VerificationError, InvalidHashError):
                    valid = False
                if not user or not valid or user['role'] not in ('ADMIN', 'TECHNICIAN'):
                    for key, _ in buckets:
                        conn.execute('UPDATE web_login_throttle SET attempts=attempts+1 WHERE bucket=%s', (key,))
                    error = 401
                else:
                    conn.execute('DELETE FROM web_login_throttle WHERE bucket=%s', (digest('user:' + username),))
                    conn.execute('UPDATE technician_user SET last_login_at=now() WHERE technician_id=%s', (user['technician_id'],))
                    if HASHER.check_needs_rehash(user['password_hash']):
                        conn.execute('UPDATE technician_user SET password_hash=%s WHERE technician_id=%s',
                                     (HASHER.hash(body.password), user['technician_id']))
                    token_id = secrets.token_urlsafe(32)
                    now = datetime.now(timezone.utc)
                    expiry = now + timedelta(minutes=settings.minutes)
                    conn.execute('INSERT INTO web_auth_session VALUES (%s,%s,%s)',
                                 (digest(token_id), user['technician_id'], expiry))
        # Raise outside the transaction so failures persist.
        if error == 429:
            raise HTTPException(429, 'Too many sign-in attempts. Try again in 15 minutes.', headers={'Retry-After': '900'})
        if error:
            raise HTTPException(401, 'Incorrect username or password.')
        token = jwt.encode({'sub': str(user['technician_id']), 'jti': token_id, 'iat': now, 'exp': expiry,
                            'iss': ISSUER, 'aud': 'technician-gui'}, settings.secret, algorithm='HS256')
        response.set_cookie(COOKIE, token, max_age=settings.minutes * 60, httponly=True,
                            secure=settings.secure, samesite='strict', path='/api')
        return {'username': user['username'], 'name': user['name'], 'role': user['role'],
                'csrf_token': csrf_for(settings, token_id)}

    @app.get('/api/auth/me')
    def me(user: User):
        return {k: user[k] for k in ('username', 'name', 'role')} | {'csrf_token': csrf_for(settings, user['token_id'])}

    @app.post('/api/auth/logout')
    def logout(response: Response, user: User):
        with connect(settings) as conn:
            conn.execute('DELETE FROM web_auth_session WHERE token_hash=%s', (digest(user['token_id']),))
        response.delete_cookie(COOKIE, path='/api', secure=settings.secure, httponly=True, samesite='strict')
        return {'ok': True}

    @app.get('/api/settings')
    def get_settings(user: User):
        with connect(settings) as conn:
            row = conn.execute('SELECT warning_temp,warning_battery FROM technician_preferences WHERE technician_id=%s',
                               (user['technician_id'],)).fetchone()
        return row or {'warning_temp': 60, 'warning_battery': 20}

    @app.put('/api/settings')
    def put_settings(body: Preferences, user: User):
        with connect(settings) as conn:
            conn.execute('''INSERT INTO technician_preferences VALUES (%s,%s,%s)
                ON CONFLICT (technician_id) DO UPDATE SET warning_temp=EXCLUDED.warning_temp,
                warning_battery=EXCLUDED.warning_battery''',
                (user['technician_id'], body.warning_temp, body.warning_battery))
        return body

    @app.get('/api/live')
    def live(user: User, t: int = Query(default=30, ge=0, le=120)):
        if settings.mode == 'SIMULATION':
            values = live_metrics(t)
            times, temps = live_temperature_history(t)
            return {'mode': 'SIMULATION', 'status': 'Simulated vehicle data', 'stale': False,
                    'metrics': values | {'power': round(values['speed'] * 180)},
                    'history': [{'seconds': x, 'temperature': y} for x, y in zip(times, temps)],
                    'timestamp': None}
        with connect(settings) as conn:
            latest = conn.execute('''SELECT t.*, s.source_type FROM telemetry_log t JOIN vehicle_session s USING (session_id)
                WHERE t.signal_status IS DISTINCT FROM 'FIGMA DEMO'
                ORDER BY t."timestamp" DESC, t.log_id DESC LIMIT 1''').fetchone()
            if not latest:
                return {'mode': 'DATABASE', 'status': 'No vehicle readings available', 'metrics': None, 'history': [], 'stale': True}
            rows = conn.execute('''SELECT extract(epoch FROM ("timestamp" - %s::timestamptz)) AS seconds,
                motor_temperature AS temperature FROM telemetry_log WHERE session_id=%s
                AND "timestamp" BETWEEN %s::timestamptz - interval '60 seconds' AND %s::timestamptz
                ORDER BY "timestamp"''', (latest['timestamp'], latest['session_id'], latest['timestamp'], latest['timestamp'])).fetchall()
        stale = (datetime.now(timezone.utc) - latest['timestamp']).total_seconds() > 5
        return {'mode': 'DATABASE', 'status': latest['signal_status'] or 'Database telemetry', 'stale': stale,
                'timestamp': latest['timestamp'], 'source_type': latest['source_type'], 'history': rows,
                'metrics': {'speed': latest['speed_mph'], 'rpm': latest['motor_rpm'], 'battery': latest['battery_percent'],
                            'temperature': latest['motor_temperature'], 'power': latest['power_draw_watts']}}

    @app.get('/api/sessions')
    def sessions(user: User):
        with connect(settings) as conn:
            return conn.execute('''SELECT s.session_id AS id, s.driver_identifier, s.start_timestamp,
                s.source_type, s.status, extract(epoch FROM (coalesce(s.end_timestamp, now())-s.start_timestamp)) AS duration_seconds,
                max(t.motor_temperature) AS max_temp, count(t.log_id) AS sample_count
                FROM vehicle_session s LEFT JOIN telemetry_log t USING(session_id)
                GROUP BY s.session_id ORDER BY s.start_timestamp DESC LIMIT 20''').fetchall()

    @app.get('/api/sessions/{session_id}/diagnostics')
    def diagnostics(session_id: int, user: User):
        with connect(settings) as conn:
            session = conn.execute('SELECT session_id,source_type,status FROM vehicle_session WHERE session_id=%s', (session_id,)).fetchone()
            if not session:
                raise HTTPException(404, 'Session not found.')
            # Aggregated SQL views from the existing project schema; no invented trend lines.
            charts = {}
            for key, view, x, y in [
                ('efficiency', 'v_efficiency_by_speed', 'speed_bucket_mph', 'wh_per_mile'),
                ('power_temp', 'v_power_by_temperature', 'temperature_bucket_c', 'avg_power_watts'),
                ('battery', 'v_battery_over_distance', 'trip_distance_km', 'battery_percent'),
                ('power_rpm', 'v_power_by_rpm', 'rpm_bucket', 'avg_power_watts'),
                ('temperature', 'v_temperature_over_time', 'seconds_into_session', 'motor_temperature'),
            ]:
                # Identifiers are constants above, never supplied by the client.
                rows = conn.execute(f'SELECT {x} AS x, {y} AS y FROM {view} WHERE session_id=%s ORDER BY {x} LIMIT 2000',
                                    (session_id,)).fetchall()
                if key == 'battery':
                    rows = [{'x': float(r['x']) / 1.609344, 'y': r['y']} for r in rows]
                if key == 'temperature':
                    rows = [{'x': float(r['x']) / 60, 'y': r['y']} for r in rows]
                charts[key] = rows
        return {'session': session, 'charts': charts}

    @app.get('/api/backups')
    def backups(user: User):
        with connect(settings) as conn:
            return conn.execute('''SELECT backup_id, backup_timestamp,backup_status,backup_type
                FROM backup_log ORDER BY backup_timestamp DESC LIMIT 20''').fetchall()

    @app.post('/api/backups', status_code=201)
    def backup(user: User):
        directory = settings.backup_dir
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with connect(settings) as conn:
            # Separate connection held for the duration: serialize resource-heavy backups.
            if not conn.execute('SELECT pg_try_advisory_lock(947261) AS locked').fetchone()['locked']:
                raise HTTPException(409, 'A backup is already running.')
            backup_id = conn.execute("INSERT INTO backup_log(backup_type,initiated_by) VALUES ('MANUAL',%s) RETURNING backup_id",
                                     (user['technician_id'],)).fetchone()['backup_id']
            conn.commit()
            path = None
            try:
                fd, name = tempfile.mkstemp(prefix=f'voltesse_{backup_id}_', suffix='.dump', dir=directory)
                os.close(fd)  # mkstemp uses 0600 permissions
                path = Path(name)
                info = conninfo_to_dict(settings.database_url)
                env = os.environ.copy()
                mapping = {'host':'PGHOST','port':'PGPORT','user':'PGUSER','password':'PGPASSWORD',
                           'dbname':'PGDATABASE','sslmode':'PGSSLMODE','sslrootcert':'PGSSLROOTCERT',
                           'sslcert':'PGSSLCERT','sslkey':'PGSSLKEY'}
                for key, value in info.items():
                    if key in mapping:
                        env[mapping[key]] = value
                env['PGCONNECT_TIMEOUT'] = '5'
                subprocess.run(['pg_dump', '--format=custom', '--no-owner', '--file', str(path)],
                               env=env, check=True, capture_output=True, timeout=120)
                conn.execute("UPDATE backup_log SET backup_status='SUCCESS',file_reference=%s WHERE backup_id=%s", (path.name, backup_id))
                conn.commit()
            except (OSError, subprocess.SubprocessError):
                if path:
                    path.unlink(missing_ok=True)
                conn.execute("UPDATE backup_log SET backup_status='FAILED' WHERE backup_id=%s", (backup_id,))
                conn.commit()
                raise HTTPException(503, 'Backup failed. Check pg_dump installation and database connectivity on the backend host.')
            finally:
                conn.execute('SELECT pg_advisory_unlock(947261)')
        return {'backup_id': backup_id, 'backup_status': 'SUCCESS'}

    dist = os.getenv('WEB_DIST')
    if dist:
        app.mount('/', StaticFiles(directory=Path(dist), html=True), name='web')
    return app
