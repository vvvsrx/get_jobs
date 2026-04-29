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


def test_get_ai_config():
    response = client.get("/api/ai/config")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_update_ai_config():
    payload = {
        "introduce": "我是5年经验的Java后端工程师",
        "prompt": "请基于以下信息生成简洁友好的中文打招呼语：{introduce}",
    }
    response = client.post("/api/ai/config", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "AI配置已保存" in data["message"]

    # verify get returns saved config
    response = client.get("/api/ai/config")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["introduce"] == payload["introduce"]
    assert data["prompt"] == payload["prompt"]
