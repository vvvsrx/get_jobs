from fastapi.testclient import TestClient
from app.main import app
from app.worker.task_state import task_state

client = TestClient(app)


async def _mock_check_login(_s, _p):
    return True


def test_job51_start_stop(monkeypatch):
    async def _mock_sleep_forever():
        import asyncio
        while True:
            await asyncio.sleep(3600)

    monkeypatch.setattr("app.routers.jobs._run_job51_delivery", _mock_sleep_forever)
    monkeypatch.setattr("app.routers.jobs._check_login_status", _mock_check_login)
    task_state.stop()

    resp = client.post("/api/job51/start")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    resp = client.post("/api/job51/start")
    assert resp.json()["success"] is False

    resp = client.post("/api/job51/stop")
    assert resp.json()["success"] is True

    resp = client.get("/api/job51/status")
    assert resp.status_code == 200
    assert "running" in resp.json()


def test_job51_logout():
    task_state.stop()
    resp = client.post("/api/job51/logout")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
