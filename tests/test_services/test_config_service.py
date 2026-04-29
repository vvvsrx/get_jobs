import pytest
from app.database import async_session_maker, Base, engine
from app.services.config_service import ConfigService


@pytest.fixture(autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_get_or_create_boss_config():
    async with async_session_maker() as session:
        service = ConfigService(session)
        config = await service.get_or_create_boss_config()
        assert config is not None
        assert config.id is not None


@pytest.mark.asyncio
async def test_update_boss_config():
    async with async_session_maker() as session:
        service = ConfigService(session)
        config = await service.update_boss_config(keywords="Java", city_code="101010100")
        assert config.keywords == "Java"
        assert config.city_code == "101010100"


@pytest.mark.asyncio
async def test_update_boss_config_rejects_invalid_fields():
    async with async_session_maker() as session:
        service = ConfigService(session)
        with pytest.raises(ValueError, match="Invalid config fields"):
            await service.update_boss_config(id=999, keywords="Java")


@pytest.mark.asyncio
async def test_blacklist_crud():
    async with async_session_maker() as session:
        service = ConfigService(session)

        # add
        item = await service.add_blacklist("company", "测试公司")
        assert item.id is not None
        assert item.type == "company"
        assert item.value == "测试公司"

        # get
        items = await service.get_blacklist()
        assert len(items) == 1

        # delete
        success = await service.delete_blacklist(item.id)
        assert success is True

        items = await service.get_blacklist()
        assert len(items) == 0

        # delete non-existent
        success = await service.delete_blacklist(99999)
        assert success is False


@pytest.mark.asyncio
async def test_get_options_by_type():
    async with async_session_maker() as session:
        service = ConfigService(session)
        # 由于 boss_option 表为空，返回空列表
        options = await service.get_options_by_type("city")
        assert options == []
