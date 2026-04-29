from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import LiepinData


class LiepinService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exists_job(self, job_id: str) -> bool:
        result = await self.session.execute(select(LiepinData).where(LiepinData.job_id == job_id))
        return result.scalar_one_or_none() is not None

    async def insert_job(self, data: dict) -> LiepinData:
        job = LiepinData(**data)
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def mark_delivered(self, job_id: str) -> bool:
        result = await self.session.execute(select(LiepinData).where(LiepinData.job_id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.delivered = 1
            await self.session.commit()
            return True
        return False

    async def get_stats(self) -> dict:
        total = await self.session.execute(select(func.count()).select_from(LiepinData))
        delivered = await self.session.execute(
            select(func.count()).select_from(LiepinData).where(LiepinData.delivered == 1)
        )
        total_val = total.scalar()
        delivered_val = delivered.scalar()
        return {
            "total": total_val,
            "delivered": delivered_val,
            "pending": total_val - delivered_val,
        }

    async def get_job_list(self, limit: int = 100, offset: int = 0, status: str = None):
        query = (
            select(LiepinData)
            .order_by(LiepinData.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status == "delivered":
            query = query.where(LiepinData.delivered == 1)
        elif status == "pending":
            query = query.where(LiepinData.delivered == 0)
        result = await self.session.execute(query)
        return result.scalars().all()
