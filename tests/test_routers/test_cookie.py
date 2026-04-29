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


def test_save_cookie():
    response = client.post("/api/cookie/save?platform=boss")
    assert response.status_code == 200
    assert response.json()["success"] is True
