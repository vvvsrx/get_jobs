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


def test_liepin_config_crud():
    resp = client.get("/api/liepin/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    resp = client.put("/api/liepin/config", json={"keywords": "Python", "city_code": "410"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = client.get("/api/liepin/config")
    data = resp.json()
    assert data["keywords"] == "Python"
    assert data["city_code"] == "410"
