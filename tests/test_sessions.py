from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get('/healthz')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_login_session_cookie():
    r = client.post('/api/v1/auth/login', data={'username': 'admin', 'password': 'admin'})
    assert r.status_code == 200
    # check cookie set
    assert 'ah_session' in r.cookies
    # use cookie to access health endpoint (middleware attaches session but health doesn't require auth)
    cookies = {'ah_session': r.cookies.get('ah_session')}
    r2 = client.get('/healthz', cookies=cookies)
    assert r2.status_code == 200


def test_logout_removes_cookie():
    r = client.post('/api/v1/auth/login', data={'username': 'admin', 'password': 'admin'})
    assert 'ah_session' in r.cookies
    cookies = {'ah_session': r.cookies.get('ah_session')}
    r2 = client.post('/api/v1/auth/logout', cookies=cookies)
    assert r2.status_code == 200
    # after logout, cookie should be deleted in response
    assert r2.headers.get('set-cookie') is not None
