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


def test_get_boss_config():
    response = client.get("/api/boss/config")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_update_boss_config():
    payload = {
        "keywords": "Java,后端",
        "city_code": "101010100",
        "say_hi": "您好",
        "enable_ai": 1,
    }
    response = client.put("/api/boss/config", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "配置已保存" in data["message"]


def test_blacklist_crud():
    # add
    response = client.post("/api/boss/config/blacklist", json={"type": "company", "value": "测试公司"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # get
    response = client.get("/api/boss/config/blacklist")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1

    # delete
    item_id = items[0]["id"]
    response = client.delete(f"/api/boss/config/blacklist/{item_id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # delete non-existent
    response = client.delete("/api/boss/config/blacklist/99999")
    assert response.status_code == 404


def test_get_options_by_type():
    response = client.get("/api/boss/config/options/city")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
