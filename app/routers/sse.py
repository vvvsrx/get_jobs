import asyncio
import json
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.sse_manager import sse_manager
from app.database import get_db
from app.services.cookie_service import CookieService

router = APIRouter()


async def _platform_sse_event_generator(
    connected_message: str,
    platform: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE events, optionally filtering by platform."""
    yield f"data: {json.dumps({'type': 'connected', 'message': connected_message})}\n\n"
    async for event in sse_manager.subscribe():
        if platform is not None:
            try:
                data = json.loads(event.removeprefix("data: "))
                if data.get("platform") != platform:
                    continue
            except (json.JSONDecodeError, AttributeError):
                pass
        yield event


@router.get("/boss/stream")
async def boss_stream():
    return StreamingResponse(
        _platform_sse_event_generator("已连接到Boss投递进度推送", platform="boss"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/liepin/stream")
async def liepin_stream():
    return StreamingResponse(
        _platform_sse_event_generator("已连接到猎聘投递进度推送", platform="liepin"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/zhilian/stream")
async def zhilian_stream():
    return StreamingResponse(
        _platform_sse_event_generator("已连接到智联投递进度推送", platform="zhilian"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/job51/stream")
async def job51_stream():
    return StreamingResponse(
        _platform_sse_event_generator("已连接到51job投递进度推送", platform="job51"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


async def _check_platform_login_status(cookie_service: CookieService, platform: str) -> bool:
    """Check if a platform has saved cookies (indicates logged in)."""
    cookie = await cookie_service.get_cookie(platform)
    if not cookie or not cookie.cookie_value:
        return False
    try:
        cookies = json.loads(cookie.cookie_value)
        return isinstance(cookies, list) and len(cookies) > 0
    except json.JSONDecodeError:
        return False


async def _login_status_event_generator(
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Generate login status SSE events with periodic heartbeat and status checks."""
    cookie_service = CookieService(db)
    platforms = ["boss", "liepin", "zhilian", "job51"]

    # Send initial connection message with all platform statuses
    initial_status = {}
    for platform in platforms:
        initial_status[f"{platform}LoggedIn"] = await _check_platform_login_status(
            cookie_service, platform
        )

    yield f"data: {json.dumps({'type': 'connected', 'message': '已连接到登录状态推送', **initial_status})}\n\n"

    # Subscribe to SSE manager for login-related events
    async for event in sse_manager.subscribe():
        yield event


@router.get("/jobs/login-status/stream")
async def login_status_stream(db: AsyncSession = Depends(get_db)):
    return StreamingResponse(
        _login_status_event_generator(db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
