"""Integration test for the require_trusted_client gate (needs fastapi+httpx only).

Run: .venv-sec/bin/python backend/tests/test_trust_gate.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.core.security import require_trusted_client

app = FastAPI()


@app.post("/guarded", dependencies=[Depends(require_trusted_client)])
def guarded():
    return {"ok": True}


def client_for(host: str) -> TestClient:
    return TestClient(app, client=(host, 54321))


def test_remote_without_token_blocked():
    os.environ.pop("REPOVERSE_ADMIN_TOKEN", None)
    os.environ.pop("REPOVERSE_TRUST_PROXY", None)
    r = client_for("203.0.113.7").post("/guarded")
    assert r.status_code == 403, r.status_code


def test_localhost_allowed():
    # Behind no proxy, the raw socket peer is what counts.
    r = client_for("127.0.0.1").post("/guarded")
    assert r.status_code == 200, r.status_code


def test_remote_with_valid_token_allowed():
    os.environ["REPOVERSE_ADMIN_TOKEN"] = "s3cret-token"
    try:
        c = client_for("203.0.113.7")
        r = c.post("/guarded", headers={"X-RepoVerse-Admin": "s3cret-token"})
        assert r.status_code == 200, r.status_code
        r_bad = c.post("/guarded", headers={"X-RepoVerse-Admin": "wrong"})
        assert r_bad.status_code == 403
    finally:
        os.environ.pop("REPOVERSE_ADMIN_TOKEN", None)


def test_proxy_forwarded_remote_blocked():
    # With REPOVERSE_TRUST_PROXY=1 the gate reads X-Forwarded-For: a remote
    # user behind Render's proxy must NOT inherit loopback trust.
    os.environ["REPOVERSE_TRUST_PROXY"] = "1"
    os.environ.pop("REPOVERSE_ADMIN_TOKEN", None)
    try:
        c = client_for("127.0.0.1")  # raw peer is the proxy itself
        r = c.post("/guarded", headers={"X-Forwarded-For": "198.51.100.4, 127.0.0.1"})
        assert r.status_code == 403, r.status_code
        r_local = c.post("/guarded", headers={"X-Forwarded-For": "127.0.0.1"})
        assert r_local.status_code == 200, r_local.status_code
    finally:
        os.environ.pop("REPOVERSE_TRUST_PROXY", None)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
