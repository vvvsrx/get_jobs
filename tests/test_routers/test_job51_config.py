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


def test_job51_config_crud():
    resp = client.get("/api/job51/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    resp = client.put("/api/job51/config", json={"keywords": "Java", "job_area": "0200", "salary": "05"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = client.get("/api/job51/config")
    data = resp.json()
    assert data["keywords"] == "Java"
    assert data["job_area"] == "0200"
    assert data["salary"] == "05"
