import pytest
from app.database import async_session_maker, Base, engine
from app.services.job51_service import Job51Service


@pytest.fixture(autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_job51_service_crud():
    async with async_session_maker() as session:
        service = Job51Service(session)
        job = await service.insert_job({
            "job_id": "12345",
            "job_title": "测试岗位",
            "comp_name": "测试公司",
            "job_salary_text": "20-30K",
            "delivered": 0,
        })
        assert job.job_id == "12345"
        assert await service.exists_job("12345") is True
        assert await service.exists_job("99999") is False

        assert await service.mark_delivered("12345") is True
        assert await service.mark_delivered("99999") is False

        stats = await service.get_stats()
        assert stats["total"] == 1
        assert stats["delivered"] == 1
        assert stats["pending"] == 0


@pytest.mark.asyncio
async def test_job51_get_job_list():
    async with async_session_maker() as session:
        service = Job51Service(session)
        await service.insert_job({"job_id": "1", "job_title": "A", "comp_name": "C1", "delivered": 1})
        await service.insert_job({"job_id": "2", "job_title": "B", "comp_name": "C2", "delivered": 0})

        all_jobs = await service.get_job_list(limit=10, offset=0)
        assert len(all_jobs) == 2

        delivered = await service.get_job_list(limit=10, offset=0, status="delivered")
        assert len(delivered) == 1
        assert delivered[0].job_id == "1"

        pending = await service.get_job_list(limit=10, offset=0, status="pending")
        assert len(pending) == 1
        assert pending[0].job_id == "2"
