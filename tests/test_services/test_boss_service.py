import pytest
from app.database import async_session_maker, Base, engine
from app.services.boss_service import BossService


@pytest.fixture(autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_insert_job_and_check_exists():
    async with async_session_maker() as session:
        service = BossService(session)
        await service.insert_job(
            encrypt_id="test123",
            encrypt_user_id="user456",
            job_name="测试岗位",
            company_name="测试公司",
            salary="15-25K",
            delivery_status="未投递",
        )
        exists = await service.exists_job("test123", "user456")
        assert exists is True
        job = await service.get_job_by_encrypt_id("test123", "user456")
        assert job.job_name == "测试岗位"


@pytest.mark.asyncio
async def test_exists_job_not_found():
    async with async_session_maker() as session:
        service = BossService(session)
        exists = await service.exists_job("nonexistent", "user999")
        assert exists is False


@pytest.mark.asyncio
async def test_exists_job_without_user_id():
    async with async_session_maker() as session:
        service = BossService(session)
        await service.insert_job(
            encrypt_id="only_id",
            encrypt_user_id="",
            job_name="测试",
            company_name="公司",
            salary="10-20K",
            delivery_status="未投递",
        )
        exists = await service.exists_job("only_id", "")
        assert exists is True


@pytest.mark.asyncio
async def test_update_delivery_status():
    async with async_session_maker() as session:
        service = BossService(session)
        await service.insert_job(
            encrypt_id="job1",
            encrypt_user_id="user1",
            job_name="岗位1",
            company_name="公司1",
            salary="15-25K",
            delivery_status="未投递",
        )
        success = await service.update_delivery_status("job1", "user1", "已投递")
        assert success is True

        job = await service.get_job_by_encrypt_id("job1", "user1")
        assert job.delivery_status == "已投递"

        # update non-existent
        success = await service.update_delivery_status("nonexistent", "user", "已投递")
        assert success is False


@pytest.mark.asyncio
async def test_get_stats():
    async with async_session_maker() as session:
        service = BossService(session)
        # insert jobs with different statuses
        await service.insert_job(encrypt_id="a", encrypt_user_id="u1", job_name="j1", company_name="c1", salary="10K", delivery_status="已投递")
        await service.insert_job(encrypt_id="b", encrypt_user_id="u2", job_name="j2", company_name="c2", salary="15K", delivery_status="已过滤")
        await service.insert_job(encrypt_id="c", encrypt_user_id="u3", job_name="j3", company_name="c3", salary="20K", delivery_status="未投递")

        stats = await service.get_stats()
        assert stats["total"] == 3
        assert stats["delivered"] == 1
        assert stats["filtered"] == 1
        assert stats["pending"] == 1


@pytest.mark.asyncio
async def test_get_job_list():
    async with async_session_maker() as session:
        service = BossService(session)
        await service.insert_job(encrypt_id="a", encrypt_user_id="u1", job_name="j1", company_name="c1", salary="10K", delivery_status="已投递")
        await service.insert_job(encrypt_id="b", encrypt_user_id="u2", job_name="j2", company_name="c2", salary="15K", delivery_status="已过滤")

        # all
        jobs = await service.get_job_list()
        assert len(jobs) == 2

        # filter by status
        jobs = await service.get_job_list(status="已投递")
        assert len(jobs) == 1
        assert jobs[0].encrypt_id == "a"

        # pagination
        jobs = await service.get_job_list(limit=1, offset=0)
        assert len(jobs) == 1
