from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BossConfig, BossBlacklist, BossOption, LiepinConfig, LiepinOption, ZhilianConfig, ZhilianOption, Job51Config, Job51Option

# BossConfig 允许更新的字段白名单
BOSS_CONFIG_FIELDS = {
    "debugger", "wait_time", "keywords", "city_code", "industry",
    "job_type", "experience", "degree", "salary", "scale", "stage",
    "say_hi", "expected_salary_min", "expected_salary_max",
    "enable_ai", "send_img_resume", "filter_dead_hr", "dead_status",
}

LIEPIN_CONFIG_FIELDS = {"keywords", "city_code", "salary_code"}

ZHILIAN_CONFIG_FIELDS = {"keywords", "city_code", "salary"}

JOB51_CONFIG_FIELDS = {"keywords", "job_area", "salary"}


class ConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ========== Boss ==========
    async def get_or_create_boss_config(self) -> BossConfig:
        result = await self.session.execute(select(BossConfig).order_by(BossConfig.id.desc()).limit(1))
        config = result.scalar_one_or_none()
        if not config:
            config = BossConfig()
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)
        return config

    async def update_boss_config(self, **kwargs) -> BossConfig:
        config = await self.get_or_create_boss_config()
        invalid_keys = [k for k in kwargs if k not in BOSS_CONFIG_FIELDS]
        if invalid_keys:
            raise ValueError(f"Invalid config fields: {invalid_keys}")
        for key, value in kwargs.items():
            setattr(config, key, value)
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def get_blacklist(self) -> list[BossBlacklist]:
        result = await self.session.execute(select(BossBlacklist))
        return result.scalars().all()

    async def add_blacklist(self, type_: str, value: str) -> BossBlacklist:
        item = BossBlacklist(type=type_, value=value)
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete_blacklist(self, id_: int) -> bool:
        result = await self.session.execute(select(BossBlacklist).where(BossBlacklist.id == id_))
        item = result.scalar_one_or_none()
        if item:
            await self.session.delete(item)
            await self.session.commit()
            return True
        return False

    async def get_options_by_type(self, type_: str) -> list[BossOption]:
        result = await self.session.execute(
            select(BossOption).where(BossOption.type == type_).order_by(BossOption.sort_order)
        )
        return result.scalars().all()

    # ========== Liepin ==========
    async def get_or_create_liepin_config(self) -> LiepinConfig:
        result = await self.session.execute(select(LiepinConfig).order_by(LiepinConfig.id.desc()).limit(1))
        config = result.scalar_one_or_none()
        if not config:
            config = LiepinConfig()
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)
        return config

    async def update_liepin_config(self, **kwargs) -> LiepinConfig:
        config = await self.get_or_create_liepin_config()
        invalid = [k for k in kwargs if k not in LIEPIN_CONFIG_FIELDS]
        if invalid:
            raise ValueError(f"Invalid fields: {invalid}")
        for k, v in kwargs.items():
            setattr(config, k, v)
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def get_liepin_options_by_type(self, type_: str) -> list[LiepinOption]:
        result = await self.session.execute(
            select(LiepinOption).where(LiepinOption.type == type_).order_by(LiepinOption.sort_order)
        )
        return result.scalars().all()

    # ========== Zhilian ==========
    async def get_or_create_zhilian_config(self) -> ZhilianConfig:
        result = await self.session.execute(select(ZhilianConfig).order_by(ZhilianConfig.id.desc()).limit(1))
        config = result.scalar_one_or_none()
        if not config:
            config = ZhilianConfig()
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)
        return config

    async def update_zhilian_config(self, **kwargs) -> ZhilianConfig:
        config = await self.get_or_create_zhilian_config()
        invalid = [k for k in kwargs if k not in ZHILIAN_CONFIG_FIELDS]
        if invalid:
            raise ValueError(f"Invalid fields: {invalid}")
        for k, v in kwargs.items():
            setattr(config, k, v)
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def get_zhilian_options_by_type(self, type_: str) -> list[ZhilianOption]:
        result = await self.session.execute(
            select(ZhilianOption).where(ZhilianOption.type == type_).order_by(ZhilianOption.sort_order)
        )
        return result.scalars().all()

    # ========== Job51 ==========
    async def get_or_create_job51_config(self) -> Job51Config:
        result = await self.session.execute(select(Job51Config).order_by(Job51Config.id.desc()).limit(1))
        config = result.scalar_one_or_none()
        if not config:
            config = Job51Config()
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)
        return config

    async def update_job51_config(self, **kwargs) -> Job51Config:
        config = await self.get_or_create_job51_config()
        invalid = [k for k in kwargs if k not in JOB51_CONFIG_FIELDS]
        if invalid:
            raise ValueError(f"Invalid fields: {invalid}")
        for k, v in kwargs.items():
            setattr(config, k, v)
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def get_job51_options_by_type(self, type_: str) -> list[Job51Option]:
        result = await self.session.execute(
            select(Job51Option).where(Job51Option.type == type_).order_by(Job51Option.sort_order)
        )
        return result.scalars().all()
