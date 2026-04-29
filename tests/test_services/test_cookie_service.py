import pytest
import json
from app.database import async_session_maker, Base, engine
from app.services.cookie_service import CookieService


@pytest.fixture(autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_save_and_get_cookie():
    async with async_session_maker() as session:
        service = CookieService(session)
        cookies = [{"name": "test", "value": "123", "domain": ".zhipin.com"}]
        await service.save_cookie("boss", json.dumps(cookies), "test")
        result = await service.get_cookie("boss")
        assert result is not None
        data = json.loads(result.cookie_value)
        assert data[0]["name"] == "test"


@pytest.mark.asyncio
async def test_clear_cookie():
    async with async_session_maker() as session:
        service = CookieService(session)
        cookies = [{"name": "test", "value": "123", "domain": ".zhipin.com"}]
        await service.save_cookie("boss", json.dumps(cookies), "test")

        success = await service.clear_cookie("boss", "logout")
        assert success is True

        result = await service.get_cookie("boss")
        assert result.cookie_value == "[]"
        assert result.remark == "logout"

        # clear non-existent
        success = await service.clear_cookie("liepin", "logout")
        assert success is False


@pytest.mark.asyncio
async def test_save_cookie_updates_existing():
    async with async_session_maker() as session:
        service = CookieService(session)
        cookies1 = [{"name": "old", "value": "1"}]
        cookies2 = [{"name": "new", "value": "2"}]

        await service.save_cookie("boss", json.dumps(cookies1), "first")
        await service.save_cookie("boss", json.dumps(cookies2), "second")

        result = await service.get_cookie("boss")
        assert result is not None
        data = json.loads(result.cookie_value)
        assert data[0]["name"] == "new"
        assert result.remark == "second"


def test_filter_by_domain():
    cookies = [
        {"name": "a", "domain": ".zhipin.com"},
        {"name": "b", "domain": ".liepin.com"},
        {"name": "c", "domain": "zhipin.com"},
    ]
    result = CookieService.filter_by_domain(cookies, "zhipin.com")
    assert len(result) == 2
    assert result[0]["name"] == "a"
    assert result[1]["name"] == "c"

    # test case insensitivity
    result = CookieService.filter_by_domain(cookies, "ZHIPIN.COM")
    assert len(result) == 2
