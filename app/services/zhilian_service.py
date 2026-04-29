from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ZhilianData


class ZhilianService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exists_job(self, job_id: str) -> bool:
        result = await self.session.execute(select(ZhilianData).where(ZhilianData.job_id == job_id))
        return result.scalar_one_or_none() is not None

    async def insert_job(self, data: dict) -> ZhilianData:
        job = ZhilianData(**data)
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def mark_delivered(self, job_id: str) -> bool:
        result = await self.session.execute(select(ZhilianData).where(ZhilianData.job_id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.delivered = 1
            await self.session.commit()
            return True
        return False

    async def get_stats(self) -> dict:
        total_result = await self.session.execute(select(func.count()).select_from(ZhilianData))
        delivered_result = await self.session.execute(select(func.count()).select_from(ZhilianData).where(ZhilianData.delivered == 1))
        total = total_result.scalar()
        delivered = delivered_result.scalar()
        return {
            "total": total,
            "delivered": delivered,
            "pending": total - delivered,
        }

    async def get_job_list(self, limit: int = 100, offset: int = 0, status: str = None):
        query = select(ZhilianData).order_by(ZhilianData.created_at.desc()).limit(limit).offset(offset)
        if status == "delivered":
            query = query.where(ZhilianData.delivered == 1)
        elif status == "pending":
            query = query.where(ZhilianData.delivered == 0)
        result = await self.session.execute(query)
        return result.scalars().all()
