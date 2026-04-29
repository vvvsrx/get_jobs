import logging
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AiConfig
from app.config import settings
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = """请基于以下信息生成简洁友好的中文打招呼语，不超过60字：
个人介绍：{introduce}
关键词：{keyword}
职位名称：{job_name}
职位描述：{jd}
参考语：{say_hi}"""


class AiService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_ai_config(self) -> Optional[AiConfig]:
        result = await self.session.execute(select(AiConfig).order_by(AiConfig.id.desc()).limit(1))
        return result.scalar_one_or_none()

    async def update_ai_config(self, introduce: Optional[str] = None, prompt: Optional[str] = None) -> AiConfig:
        config = await self.get_ai_config()
        if not config:
            config = AiConfig()
            self.session.add(config)
        if introduce is not None:
            config.introduce = introduce
        if prompt is not None:
            config.prompt = prompt
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def generate_message(
        self,
        introduce: str,
        keyword: str,
        job_name: str,
        jd: str,
        say_hi: str,
    ) -> Optional[str]:
        config = await self.get_ai_config()
        prompt_template = config.prompt if config and config.prompt else DEFAULT_PROMPT
        try:
            request_message = prompt_template.format(
                introduce=introduce or "",
                keyword=keyword,
                job_name=job_name,
                jd=jd or "",
                say_hi=say_hi,
            )
        except KeyError as e:
            logger.warning("Prompt template has invalid placeholder: %s", e)
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.model,
                        "messages": [{"role": "user", "content": request_message}],
                        "max_tokens": 120,
                    },
                )
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    return None
                content = choices[0].get("message", {}).get("content", "").strip()
                if content.lower() == "false" or not content:
                    return None
                return content
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning("AI API request failed: %s", e)
            return None
        except (KeyError, IndexError, TypeError) as e:
            logger.warning("AI API response parsing failed: %s", e)
            return None
