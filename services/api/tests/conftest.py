import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RAW_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RAW_DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    monkeypatch.setenv("RAW_RATE_LIMIT_PER_MIN", "100000")
    from app import config, jobs
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MIN", 100000)
    from app.main import app
    jobs.reset_pool()
    with TestClient(app) as c:
        yield c
    jobs.reset_pool()


def signup(client, email="a@example.com"):
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    pid = client.post("/projects", json={"name": "P"}, headers=h).json()["id"]
    return h, pid


def wait(client, h, job_id, timeout=20):
    import time
    t = time.time()
    while time.time() - t < timeout:
        j = client.get(f"/jobs/{job_id}", headers=h).json()
        if j["state"] in ("COMPLETED", "FAILED", "CANCELLED", "WAITING_FOR_APPROVAL"):
            return j
        time.sleep(0.05)
    raise AssertionError("job did not finish")
