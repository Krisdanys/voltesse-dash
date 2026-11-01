"""Isolated PostgreSQL schema per test; existing data is never truncated."""
import os
import secrets
import shutil
import subprocess
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import jwt
import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo, conninfo_to_dict
from backend.app import COOKIE, HASHER, connect, create_app
from backend.config import Settings
from backend.manage import create_user, migrate, seed_demo

HEADERS={'X-Requested-With':'VoltesseGUI','Origin':'http://localhost:5173'}
@pytest.fixture()
def setup(tmp_path,monkeypatch):
    # Some embedded PostgreSQL protocol adapters ignore startup options.
    # Explicit SET also verifies every tested query uses the isolated schema.
    original_connect=psycopg.connect
    def scoped_connect(conninfo="",**kwargs):
        kwargs.setdefault("prepare_threshold",None)
        conn=original_connect(conninfo,**kwargs)
        opts=conninfo_to_dict(conninfo).get("options", "")
        if opts.startswith("-c search_path=test_"):
            conn.execute("SET search_path TO " + opts.split("=",1)[1])
            conn.commit()
        return conn
    monkeypatch.setattr(psycopg,"connect",scoped_connect)
    url=os.getenv('TEST_DATABASE_URL')
    if not url: pytest.skip('Set TEST_DATABASE_URL to run PostgreSQL integration tests.')
    schema='test_'+uuid4().hex
    with psycopg.connect(url,autocommit=True) as conn: conn.execute(f'CREATE SCHEMA {schema}')
    settings=Settings(make_conninfo(url,options=f'-c search_path={schema}'),secrets.token_urlsafe(48),False,backup_dir=tmp_path/'backups')
    migrate(settings)
    password=secrets.token_urlsafe(20)
    create_user(settings,'tech@example.test','Test Technician','TECHNICIAN',password)
    client=TestClient(create_app(settings),headers=HEADERS)
    yield settings,client,password
    client.close()
    with psycopg.connect(url,autocommit=True) as conn: conn.execute(f'DROP SCHEMA {schema} CASCADE')

def sign_in(client,password):
    r=client.post('/api/auth/login',json={'username':'tech@example.test','password':password})
    assert r.status_code==200,r.text
    client.headers['X-CSRF-Token']=r.json()['csrf_token']
    return r

def test_hash_and_no_default_account(setup):
    settings,client,password=setup
    with connect(settings) as conn:
        row=conn.execute('SELECT * FROM technician_user').fetchone()
        assert row['password_hash'].startswith('$argon2id$')
        assert password not in row['password_hash']
        assert HASHER.verify(row['password_hash'],password)
    assert client.post('/api/auth/login',json={'username':'demo@voltesse.test','password':'Demo123!'}).status_code==401

@pytest.mark.parametrize('path',['/auth/me','/live','/sessions','/sessions/1/diagnostics','/settings','/backups'])
def test_data_requires_login(setup,path):
    _,client,_=setup
    assert client.get('/api'+path).status_code==401

def test_wrong_unknown_and_sql_credentials(setup):
    _,client,_=setup
    for name in ['tech@example.test','missing',"' OR 1=1 --"]:
        r=client.post('/api/auth/login',json={'username':name,'password':'incorrect password'})
        assert r.status_code==401
        assert r.json()=={'detail':'Incorrect username or password.'}

def test_cookie_logout_and_replay(setup):
    settings,client,password=setup
    header=sign_in(client,password).headers['set-cookie']
    assert 'HttpOnly' in header and 'SameSite=strict' in header and 'Path=/api' in header
    token=client.cookies.get(COOKIE)
    assert client.get('/api/auth/me').status_code==200
    assert client.post('/api/auth/logout').status_code==200
    client.cookies.set(COOKIE,token,path='/api')
    assert client.get('/api/live').status_code==401
    with connect(settings) as conn: assert conn.execute('SELECT count(*) AS n FROM web_auth_session').fetchone()['n']==0

def test_secure_expired_and_tampered_cookie(setup):
    settings,_,password=setup
    client=TestClient(create_app(replace(settings,secure=True)),base_url='https://localhost',headers=HEADERS)
    assert 'Secure' in sign_in(client,password).headers['set-cookie']
    token=client.cookies.get(COOKIE)
    claims=jwt.decode(token,settings.secret,algorithms=['HS256'],audience='technician-gui')
    claims['exp']=datetime.now(timezone.utc)-timedelta(seconds=1)
    client.cookies.clear()
    client.cookies.set(COOKIE,jwt.encode(claims,settings.secret,algorithm='HS256'),path='/api')
    assert client.get('/api/live').status_code==401
    client.cookies.set(COOKIE,token+'tampered',path='/api')
    assert client.get('/api/live').status_code==401

def test_csrf_origin_header(setup):
    _,client,password=setup
    sign_in(client,password)
    data={'warning_temp':80,'warning_battery':30}
    csrf=client.headers.pop('X-CSRF-Token')
    assert client.put('/api/settings',json=data).status_code==403
    client.headers['X-CSRF-Token']=csrf
    assert client.put('/api/settings',json=data,headers={'Origin':'https://evil.example'}).status_code==403
    client.headers.pop('X-Requested-With')
    assert client.post('/api/auth/logout').status_code==403
    assert client.post('/api/auth/login',json={'username':'tech@example.test','password':password}).status_code==403

def test_persistent_attempt_limit(setup):
    settings,client,password=setup
    for _ in range(5): assert client.post('/api/auth/login',json={'username':'tech@example.test','password':'bad'}).status_code==401
    other=TestClient(create_app(settings),headers=HEADERS)
    assert other.post('/api/auth/login',json={'username':'tech@example.test','password':password}).status_code==429
    with connect(settings) as conn: conn.execute("UPDATE web_login_throttle SET window_start=now()-interval '16 minutes'")
    sign_in(other,password)

def test_persistent_per_user_settings(setup):
    settings,client,password=setup
    sign_in(client,password)
    assert client.put('/api/settings',json={'warning_temp':80,'warning_battery':30}).status_code==200
    assert client.put('/api/settings',json={'warning_temp':900,'warning_battery':30}).status_code==422
    client.post('/api/auth/logout')
    sign_in(client,password)
    assert client.get('/api/settings').json()=={'warning_temp':80,'warning_battery':30}
    create_user(settings,'other','Other','TECHNICIAN',password)
    other=TestClient(create_app(settings),headers=HEADERS)
    other.post('/api/auth/login',json={'username':'other','password':password})
    assert other.get('/api/settings').json()=={'warning_temp':60,'warning_battery':20}

def test_simulation_sessions_and_five_diagnostics(setup):
    settings,client,password=setup
    seed_demo(settings);seed_demo(settings)
    sign_in(client,password)
    result=client.get('/api/live?t=30').json()
    assert result['mode']=='SIMULATION' and result['metrics']['battery']==87.6
    assert len(result['history'])==31
    assert client.get('/api/live?t=121').status_code==422
    sessions=client.get('/api/sessions').json()
    assert len(sessions)==4 and sessions[0]['sample_count']==121
    charts=client.get(f"/api/sessions/{sessions[0]['id']}/diagnostics").json()['charts']
    assert set(charts)=={'efficiency','power_temp','battery','power_rpm','temperature'} and all(charts.values())
    assert client.get('/api/sessions/999999/diagnostics').status_code==404

def test_database_mode_empty_current_stale_and_null(setup):
    settings,_,password=setup
    client=TestClient(create_app(replace(settings,mode='DATABASE')),headers=HEADERS)
    sign_in(client,password)
    assert client.get('/api/live').json()['metrics'] is None
    seed_demo(settings)
    assert client.get('/api/live').json()['metrics'] is None
    with connect(settings) as conn:
        sid=conn.execute("INSERT INTO vehicle_session(driver_identifier) VALUES ('Driver') RETURNING session_id").fetchone()['session_id']
        conn.execute('INSERT INTO telemetry_log(session_id,"timestamp",speed_mph,signal_status) VALUES (%s,now(),22,\'CAN ACTIVE\')',(sid,))
    r=client.get('/api/live').json()
    assert r['metrics']['speed']==22 and r['metrics']['temperature'] is None and r['stale'] is False
    assert r['source_type']=='CAN_BUS'
    with connect(settings) as conn: conn.execute("UPDATE vehicle_session SET source_type='SIMULATION' WHERE session_id=%s",(sid,))
    assert client.get('/api/live').json()['source_type']=='SIMULATION'
    with connect(settings) as conn: conn.execute('UPDATE telemetry_log SET "timestamp"=now()-interval \'1 minute\' WHERE session_id=%s',(sid,))
    assert client.get('/api/live').json()['stale'] is True

def test_backup_failure_is_logged(setup,monkeypatch):
    settings,client,password=setup
    sign_in(client,password)
    def fail(*args,**kwargs): raise FileNotFoundError('missing')
    monkeypatch.setattr(subprocess,'run',fail)
    assert client.post('/api/backups').status_code==503
    assert client.get('/api/backups').json()[0]['backup_status']=='FAILED'
    assert not list(settings.backup_dir.glob('*.dump'))

def test_backup_private_file_and_safe_arguments(setup,monkeypatch):
    settings,client,password=setup
    sign_in(client,password)
    def fake_dump(args,**kwargs):
        assert args[0]=='pg_dump' and settings.database_url not in args
        Path(args[-1]).write_bytes(b'test only')
    monkeypatch.setattr(subprocess,'run',fake_dump)
    assert client.post('/api/backups').status_code==201
    assert client.get('/api/backups').json()[0]['backup_status']=='SUCCESS'
    assert list(settings.backup_dir.glob('*.dump'))[0].stat().st_mode & 0o777==0o600

def test_real_pg_dump(setup):
    if not shutil.which('pg_dump'): pytest.skip('Requires PostgreSQL client tools.')
    _,client,password=setup
    sign_in(client,password)
    assert client.post('/api/backups').status_code==201

def test_deleted_account_blocks_existing_session(setup):
    settings,client,password=setup
    sign_in(client,password)
    with connect(settings) as conn: conn.execute("DELETE FROM technician_user WHERE username='tech@example.test'")
    assert client.get('/api/live').status_code==401
