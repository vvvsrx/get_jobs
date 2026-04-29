import pytest
from unittest.mock import AsyncMock, patch, Mock
from app.database import async_session_maker, Base, engine
from app.services.ai_service import AiService


@pytest.fixture(autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_get_ai_config():
    async with async_session_maker() as session:
        service = AiService(session)
        config = await service.get_ai_config()
        assert config is None  # 空表时返回 None


@pytest.mark.asyncio
async def test_update_ai_config():
    async with async_session_maker() as session:
        service = AiService(session)
        config = await service.update_ai_config(introduce="5年后端", prompt="自定义prompt")
        assert config.introduce == "5年后端"
        assert config.prompt == "自定义prompt"

        # 再次更新
        config = await service.update_ai_config(introduce="3年前端")
        assert config.introduce == "3年前端"
        assert config.prompt == "自定义prompt"  # prompt 不变


@pytest.mark.asyncio
async def test_generate_message_with_custom_prompt():
    async with async_session_maker() as session:
        service = AiService(session)
        # 先创建自定义 prompt
        await service.update_ai_config(prompt="基于{say_hi}生成")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = Mock(return_value=None)
            mock_post.return_value.json = Mock(return_value={
                "choices": [{"message": {"content": "自定义结果"}}]
            })
            result = await service.generate_message(
                introduce="",
                keyword="",
                job_name="",
                jd="",
                say_hi="你好",
            )
            assert result == "自定义结果"
            # 验证请求中使用了自定义 prompt
            call_args = mock_post.call_args
            request_content = call_args.kwargs["json"]["messages"][0]["content"]
            assert "基于你好生成" in request_content


@pytest.mark.asyncio
async def test_generate_message_mocked():
    async with async_session_maker() as session:
        service = AiService(session)
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json = Mock(return_value={
                "choices": [{"message": {"content": "您好，我对这个岗位很感兴趣"}}]
            })
            mock_post.return_value.raise_for_status = Mock(return_value=None)
            result = await service.generate_message(
                introduce="5年后端经验",
                keyword="Java",
                job_name="Java后端开发",
                jd="负责后端系统开发",
                say_hi="您好"
            )
            assert result == "您好，我对这个岗位很感兴趣"
