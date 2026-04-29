from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Cookie
from typing import Optional


class CookieService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_cookie(self, platform: str) -> Optional[Cookie]:
        result = await self.session.execute(select(Cookie).where(Cookie.platform == platform))
        return result.scalar_one_or_none()

    async def save_cookie(self, platform: str, cookie_value: str, remark: str = "") -> Cookie:
        existing = await self.get_cookie(platform)
        if existing:
            existing.cookie_value = cookie_value
            existing.remark = remark
        else:
            existing = Cookie(platform=platform, cookie_value=cookie_value, remark=remark)
            self.session.add(existing)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def clear_cookie(self, platform: str, remark: str) -> bool:
        item = await self.get_cookie(platform)
        if item:
            item.cookie_value = "[]"
            item.remark = remark
            await self.session.commit()
            return True
        return False

    @staticmethod
    def filter_by_domain(cookies: list[dict], domain_suffix: str) -> list[dict]:
        domain_suffix = domain_suffix.lower()
        filtered = []
        for c in cookies:
            domain = c.get("domain", "").lower()
            if domain == domain_suffix or domain.endswith("." + domain_suffix):
                filtered.append(c)
        return filtered
