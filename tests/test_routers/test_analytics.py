import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)


@pytest.fixture(autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def test_get_stats():
    response = client.get("/api/boss/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "total" in data


def test_get_boss_list():
    response = client.get("/api/boss/list")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "total" in data
    assert data["total"] >= len(data["data"])


def test_get_boss_list_with_status():
    response = client.get("/api/boss/list?status=已投递")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "total" in data
    assert data["total"] >= len(data["data"])


def test_reload_boss():
    response = client.post("/api/boss/reload")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "重新加载" in data["message"]
