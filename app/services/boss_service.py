from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BossData
from typing import Optional


class BossService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exists_job(self, encrypt_id: str, encrypt_user_id: str) -> bool:
        if not encrypt_user_id:
            result = await self.session.execute(
                select(BossData).where(BossData.encrypt_id == encrypt_id)
            )
        else:
            result = await self.session.execute(
                select(BossData).where(
                    BossData.encrypt_id == encrypt_id,
                    BossData.encrypt_user_id == encrypt_user_id,
                )
            )
        return result.scalar_one_or_none() is not None

    async def get_job_by_encrypt_id(self, encrypt_id: str, encrypt_user_id: str) -> Optional[BossData]:
        result = await self.session.execute(
            select(BossData).where(
                BossData.encrypt_id == encrypt_id,
                BossData.encrypt_user_id == encrypt_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def insert_job(self, **kwargs) -> BossData:
        job = BossData(**kwargs)
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def update_delivery_status(self, encrypt_id: str, encrypt_user_id: str, status: str) -> bool:
        result = await self.session.execute(
            update(BossData)
            .where(
                BossData.encrypt_id == encrypt_id,
                BossData.encrypt_user_id == encrypt_user_id,
            )
            .values(delivery_status=status)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def get_stats(self) -> dict:
        total_result = await self.session.execute(select(func.count()).select_from(BossData))
        total = total_result.scalar()

        delivered_result = await self.session.execute(
            select(func.count()).select_from(BossData).where(BossData.delivery_status == "已投递")
        )
        delivered = delivered_result.scalar()

        filtered_result = await self.session.execute(
            select(func.count()).select_from(BossData).where(BossData.delivery_status == "已过滤")
        )
        filtered = filtered_result.scalar()

        return {
            "total": total,
            "delivered": delivered,
            "filtered": filtered,
            "pending": total - delivered - filtered,
        }

    async def get_job_list(self, limit: int = 100, offset: int = 0, status: Optional[str] = None) -> list[BossData]:
        query = select(BossData)
        if status:
            query = query.where(BossData.delivery_status == status)
        query = query.order_by(BossData.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()
