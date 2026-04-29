import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.worker.task_state import task_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_task_state():
    """每个测试前重置 task_state 状态，避免测试间相互影响"""
    task_state.stop()
    task_state.current_platform = None
    task_state.current_job = None
    yield
    task_state.stop()
    task_state.current_platform = None
    task_state.current_job = None


async def _mock_sleep_forever():
    import asyncio
    while True:
        await asyncio.sleep(3600)


async def _mock_check_login(_s, _p):
    return True


def test_start_and_stop_boss(monkeypatch):
    monkeypatch.setattr("app.routers.jobs._run_boss_delivery", _mock_sleep_forever)
    monkeypatch.setattr("app.routers.jobs._check_login_status", _mock_check_login)

    # start
    response = client.post("/api/boss/start")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # status
    response = client.get("/api/boss/status")
    assert response.json()["running"] is True

    # stop
    response = client.post("/api/boss/stop")
    assert response.json()["success"] is True

    response = client.get("/api/boss/status")
    assert response.json()["running"] is False


def test_start_boss_when_already_running(monkeypatch):
    monkeypatch.setattr("app.routers.jobs._run_boss_delivery", _mock_sleep_forever)
    monkeypatch.setattr("app.routers.jobs._check_login_status", _mock_check_login)

    # 先启动
    response = client.post("/api/boss/start")
    assert response.json()["success"] is True

    # 再次启动应返回失败
    response = client.post("/api/boss/start")
    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["message"] == "Boss任务已在运行中"


def test_stop_boss_when_not_running():
    response = client.post("/api/boss/stop")
    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["message"] == "没有正在运行的Boss任务"


def test_logout_boss(monkeypatch):
    monkeypatch.setattr("app.routers.jobs._run_boss_delivery", _mock_sleep_forever)
    monkeypatch.setattr("app.routers.jobs._check_login_status", _mock_check_login)

    # 先启动
    response = client.post("/api/boss/start")
    assert response.json()["success"] is True

    # logout
    response = client.post("/api/boss/logout")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # 确认已停止
    response = client.get("/api/boss/status")
    assert response.json()["running"] is False


def test_get_boss_status_initial():
    response = client.get("/api/boss/status")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False
    assert data["current"] is None
    assert data["total"] is None
    assert data["platform"] is None
    assert data["delivered_count"] == 0
    assert data["filtered_count"] == 0


def test_start_boss_triggers_background_task(monkeypatch):
    import asyncio
    called = False

    async def mock_run():
        nonlocal called
        called = True

    monkeypatch.setattr("app.routers.jobs._run_boss_delivery", mock_run)
    monkeypatch.setattr("app.routers.jobs._check_login_status", _mock_check_login)
    response = client.post("/api/boss/start")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "started"
