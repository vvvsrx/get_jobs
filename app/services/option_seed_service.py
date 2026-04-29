import json
import os
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BossOption, LiepinOption, ZhilianOption, Job51Option

logger = logging.getLogger(__name__)

_OPTION_MODELS = {
    "boss": BossOption,
    "liepin": LiepinOption,
    "zhilian": ZhilianOption,
    "job51": Job51Option,
}

_SEED_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "options",
)


class OptionSeedService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_table_empty(self, platform: str) -> bool:
        """Check if the option table for a platform has zero rows."""
        model = _OPTION_MODELS[platform]
        result = await self.session.execute(select(func.count()).select_from(model))
        return result.scalar() == 0

    async def import_platform(self, platform: str, force: bool = False) -> dict:
        """Import option data for a single platform using hybrid strategy.

        Priority:
        1. JSON seed file (if user manually placed data)
        2. Web scraping (optional, may fail silently)
        3. Built-in fallback data

        Returns {"imported": int, "skipped": bool, "error": str|None}
        """
        if not force and not await self.is_table_empty(platform):
            return {"imported": 0, "skipped": True, "error": None}

        # 1. Try JSON file first
        json_path = os.path.join(_SEED_DIR, f"{platform}.json")
        if os.path.exists(json_path):
            return await self._import_from_json(platform, json_path, force)

        # 2. Try web scraping (best effort, silent fallback)
        scraped = await self._scrape_from_web(platform)
        if scraped:
            return await self._insert_data(platform, scraped, force)

        # 3. Fallback to built-in data
        fallback = self._get_fallback_data(platform)
        if fallback:
            return await self._insert_data(platform, fallback, force)

        return {"imported": 0, "skipped": False, "error": "No data source available"}

    async def _import_from_json(self, platform: str, json_path: str, force: bool) -> dict:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return {"imported": 0, "skipped": False, "error": f"Failed to read seed file: {e}"}

        return await self._insert_data(platform, data, force)

    async def _insert_data(self, platform: str, data: list, force: bool) -> dict:
        model = _OPTION_MODELS[platform]

        if force:
            await self.session.execute(model.__table__.delete())

        for item in data:
            option = model(
                type=item["type"],
                name=item["name"],
                code=item["code"],
                sort_order=item.get("sort_order"),
            )
            self.session.add(option)

        await self.session.commit()
        logger.info("Imported %d %s options", len(data), platform)
        return {"imported": len(data), "skipped": False, "error": None}

    async def _scrape_from_web(self, platform: str) -> list | None:
        """Attempt to scrape option data from the platform's website.

        This is a best-effort approach that may fail due to site changes.
        Returns None on any error to allow fallback.
        """
        try:
            if platform == "boss":
                return await self._scrape_boss()
            elif platform == "liepin":
                return await self._scrape_liepin()
            elif platform == "zhilian":
                return await self._scrape_zhilian()
            elif platform == "job51":
                return await self._scrape_job51()
        except Exception as e:
            logger.debug("Web scraping failed for %s: %s", platform, e)
        return None

    async def _scrape_boss(self) -> list | None:
        # TODO: Implement boss scraping if needed
        return None

    async def _scrape_liepin(self) -> list | None:
        # TODO: Implement liepin scraping if needed
        return None

    async def _scrape_zhilian(self) -> list | None:
        # TODO: Implement zhilian scraping if needed
        return None

    async def _scrape_job51(self) -> list | None:
        # TODO: Implement job51 scraping if needed
        return None

    def _get_fallback_data(self, platform: str) -> list | None:
        """Return built-in fallback data for the platform."""
        from app.services.option_seed_fallback import (
            BOSS_FALLBACK,
            LIEPIN_FALLBACK,
            ZHILIAN_FALLBACK,
            JOB51_FALLBACK,
        )

        return {
            "boss": BOSS_FALLBACK,
            "liepin": LIEPIN_FALLBACK,
            "zhilian": ZHILIAN_FALLBACK,
            "job51": JOB51_FALLBACK,
        }.get(platform)

    async def import_all(self, force: bool = False) -> dict:
        """Import option data for all platforms."""
        results = {}
        for platform in _OPTION_MODELS:
            results[platform] = await self.import_platform(platform, force=force)
        return results
