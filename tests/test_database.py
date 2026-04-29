import pytest
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from app.database import async_session_maker, engine, init_db, get_db
from app.models import BossConfig, BossBlacklist, BossData, Cookie, AiConfig, BossOption, Config


@pytest.mark.asyncio
async def test_engine_created():
    assert engine is not None
    assert isinstance(engine, AsyncEngine)


@pytest.mark.asyncio
async def test_session_maker_returns_async_session():
    async with async_session_maker() as session:
        assert isinstance(session, AsyncSession)


@pytest.mark.asyncio
async def test_init_db_runs_without_error():
    await init_db()


@pytest.mark.asyncio
async def test_get_db_yields_session():
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break  # 只取第一个，确保正常退出


def test_models_importable():
    assert BossConfig.__tablename__ == "boss_config"
    assert BossBlacklist.__tablename__ == "boss_blacklist"
    assert BossData.__tablename__ == "boss_data"
    assert Cookie.__tablename__ == "cookie"
    assert AiConfig.__tablename__ == "ai"
    assert BossOption.__tablename__ == "boss_option"
    assert Config.__tablename__ == "config"
