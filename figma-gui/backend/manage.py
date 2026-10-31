"""Explicit CLI provisioning. No default account or public registration endpoint."""
import argparse
import getpass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .app import HASHER, connect
from .config import Settings
from .simulator import SESSIONS, live_metrics


def migrate(settings):
    root = Path(__file__).resolve().parents[2]
    with connect(settings) as conn:
        conn.execute((root / 'db/schema.sql').read_text())
        conn.execute(Path(__file__).with_name('schema.sql').read_text())
    print('Database schema ready (additive migration).')


def create_user(settings, username, name, role, password):
    username = username.strip().lower()
    if not username or len(username) > 254:
        raise ValueError('Username must contain 1–254 characters.')
    if len(password) < 12 or len(password) > 1024:
        raise ValueError('Use a password between 12 and 1024 characters.')
    with connect(settings) as conn:
        if conn.execute('SELECT 1 FROM technician_user WHERE lower(username)=%s', (username,)).fetchone():
            raise ValueError('That username already exists; no credentials changed.')
        conn.execute('INSERT INTO technician_user(name,username,password_hash,role) VALUES (%s,%s,%s,%s)',
                     (name, username, HASHER.hash(password), role))


def seed_demo(settings):
    # Does not create accounts. Never deletes vehicle data. Each fixture is inserted once.
    with connect(settings) as conn:
        for n, fixture in enumerate(SESSIONS):
            note = 'FIGMA DEMO ' + fixture['id']
            if conn.execute('SELECT 1 FROM vehicle_session WHERE session_notes=%s', (note,)).fetchone():
                continue
            start = datetime.strptime(fixture['date'], '%b %d, %Y').replace(tzinfo=timezone.utc)
            mins, secs = map(int, fixture['duration'].split(':'))
            duration = mins * 60 + secs
            sid = conn.execute('''INSERT INTO vehicle_session(driver_identifier,start_timestamp,end_timestamp,
                session_notes,source_type,status) VALUES ('SIMULATED',%s,%s,%s,'SIMULATION','COMPLETED') RETURNING session_id''',
                (start, start + timedelta(seconds=duration), note)).fetchone()['session_id']
            for t in range(121):
                val = live_metrics(t)
                temp = round(32 + (fixture['max_temp'] - 32) * t / 120, 1)
                conn.execute('''INSERT INTO telemetry_log(session_id,"timestamp",speed_mph,motor_rpm,battery_percent,
                    motor_temperature,power_draw_watts,signal_status,trip_distance_km)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'FIGMA DEMO',%s)''',
                    (sid, start + timedelta(seconds=t * duration / 120), val['speed'], val['rpm'], val['battery'],
                     temp, round(val['speed'] * 180 + n * 250), t * 0.08))
    print('Four clearly labeled simulated sessions are ready.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('migrate')
    sub.add_parser('seed-demo')
    u = sub.add_parser('create-user')
    u.add_argument('--username', required=True)
    u.add_argument('--name', required=True)
    u.add_argument('--role', choices=['TECHNICIAN', 'ADMIN'], default='TECHNICIAN')
    args = p.parse_args()
    settings = Settings.from_env()
    if args.command == 'migrate':
        migrate(settings)
    elif args.command == 'seed-demo':
        seed_demo(settings)
    else:
        password = getpass.getpass('New password (12+ characters): ')
        if password != getpass.getpass('Confirm password: '):
            p.error('Passwords do not match.')
        try:
            create_user(settings, args.username, args.name, args.role, password)
        except ValueError as exc:
            p.error(str(exc))
        print('Account created. Sign in using your username and password.')

if __name__ == '__main__':
    main()
