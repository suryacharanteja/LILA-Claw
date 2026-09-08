from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from lila.api.auth import create_app, COOKIE
from lila.security.sessions import AuthError


def test_bootstrap_atomic_expiry_and_no_plaintext_hash(auth):
    sessions, clock = auth
    secret = sessions.issue_bootstrap()
    def consume():
        try:
            return sessions.consume_bootstrap(secret)
        except AuthError:
            return None
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _:consume(), range(2)))
    assert sum(result is not None for result in results) == 1
    row = sessions.writer.call(lambda db:db.execute("SELECT token_hash FROM bootstrap").fetchone(), transaction=False)
    assert secret.encode() not in row[0]
    expired = sessions.issue_bootstrap()
    clock[0] += 60
    with pytest.raises(AuthError):
        sessions.consume_bootstrap(expired)


def test_renewal_overlap_csrf_revocation_epoch(auth):
    sessions, clock = auth
    initial = sessions.consume_bootstrap(sessions.issue_bootstrap())
    assert sessions.session(initial["secret"])["csrf_token"] == initial["csrf_token"]
    with pytest.raises(AuthError):
        sessions.renew(initial["secret"], "x"*43)
    rotated = sessions.renew(initial["secret"], initial["csrf_token"])
    sessions.authenticate(initial["secret"])
    with pytest.raises(AuthError):
        sessions.renew(initial["secret"], initial["csrf_token"])
    clock[0] += 30
    with pytest.raises(AuthError):
        sessions.authenticate(initial["secret"])
    sessions.revoke(rotated["principal_id"], 1)
    with pytest.raises(AuthError):
        sessions.authenticate(rotated["secret"])
    current = sessions.consume_bootstrap(sessions.issue_bootstrap())
    outstanding_bootstrap = sessions.issue_bootstrap()
    sessions.reset_epoch()
    with pytest.raises(AuthError):
        sessions.authenticate(current["secret"])
    with pytest.raises(AuthError):
        sessions.consume_bootstrap(outstanding_bootstrap)


def test_http_boundaries_and_cookie(auth):
    sessions, _ = auth
    url = "https://127.0.0.1:43127"
    with TestClient(create_app(sessions,43127), base_url=url) as client:
        token = sessions.issue_bootstrap()
        assert client.post("/api/v1/auth/bootstrap",json={"token":token}).status_code == 403
        assert client.post("/api/v1/auth/bootstrap",json={"token":token},headers={"Origin":"https://evil.invalid"}).status_code == 403
        result = client.post("/api/v1/auth/bootstrap",json={"token":token},headers={"Origin":url})
        assert result.status_code == 200
        cookie = result.headers["set-cookie"]
        for expected in [COOKIE,"HttpOnly","Secure","SameSite=strict","Path=/"]:
            assert expected in cookie
        assert "secret" not in result.json()
        assert result.headers["cache-control"] == "no-store"
        assert client.get("/api/v1/auth/session",headers={"Host":"localhost:43127"}).status_code == 403
        assert client.get("/api/v1/auth/session",headers={"Sec-Fetch-Site":"cross-site"}).status_code == 403
        assert client.post("/api/v1/auth/renew",json={"command_id":str(uuid4())},headers={"Origin":url}).status_code == 403
        assert client.post("/api/v1/auth/renew",json={"command_id":str(uuid4())},headers={"Origin":url,"X-Lila-CSRF":result.json()["csrf_token"]}).status_code == 200
        assert client.post("/api/v1/auth/bootstrap",content='{"token":"a","token":"b"}',headers={"Origin":url}).status_code == 400
        assert client.post("/api/v1/auth/bootstrap",content=b"x"*(1024*1024+1),headers={"Origin":url}).status_code == 413
