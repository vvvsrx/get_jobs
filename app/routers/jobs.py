import asyncio
import json
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import ApiResponse
from app.worker.task_state import task_state
from app.worker.sse_manager import sse_manager
from app.worker.bot import BossBot
from app.worker.liepin_bot import LiepinBot
from app.worker.zhilian_bot import ZhilianBot
from app.worker.job51_bot import Job51Bot
from app.database import async_session_maker, get_db
from app.services.cookie_service import CookieService

router = APIRouter()
logger = logging.getLogger(__name__)


async def _check_login_status(cookie_service: CookieService, platform: str) -> bool:
    """Check if a platform has saved cookies (indicates logged in)."""
    cookie = await cookie_service.get_cookie(platform)
    if not cookie or not cookie.cookie_value:
        return False
    try:
        cookies = json.loads(cookie.cookie_value)
        return isinstance(cookies, list) and len(cookies) > 0
    except json.JSONDecodeError:
        return False


async def _run_boss_delivery():
    """后台执行 Boss 投递任务。"""
    bot = None
    try:
        bot = BossBot(config={}, db_session_factory=async_session_maker)
        await bot.init()

        def progress_cb(message: str, current: int, total: int):
            task_state.current_job = message
            sse_manager.publish({
                "type": "progress",
                "platform": "boss",
                "message": message,
                "current": current,
                "total": total,
            })

        bot.progress_callback = progress_cb
        await bot.run_delivery()
    except Exception as e:
        logger.error("Boss 投递任务异常：%s", e)
        sse_manager.publish({
            "type": "error",
            "platform": "boss",
            "message": f"投递异常：{e}",
        })
    finally:
        if bot:
            await bot.close()
        task_state.stop()
        sse_manager.publish({
            "type": "complete",
            "platform": "boss",
            "message": "投递任务已结束",
        })


@router.post("/boss/start", response_model=ApiResponse)
async def start_boss(db: AsyncSession = Depends(get_db)):
    cookie_service = CookieService(db)
    if not await _check_login_status(cookie_service, "boss"):
        return ApiResponse(success=False, message="请先登录Boss直聘", status="not_logged_in")
    if task_state.running:
        return ApiResponse(success=False, message="Boss任务已在运行中", status="running")

    task_state.start("boss")
    asyncio.create_task(_run_boss_delivery())
    return ApiResponse(success=True, message="Boss任务启动成功", status="started")


@router.post("/boss/stop", response_model=ApiResponse)
async def stop_boss():
    if not task_state.running:
        return ApiResponse(success=False, message="没有正在运行的Boss任务")
    task_state.stop()
    return ApiResponse(success=True, message="Boss任务停止请求已发送")


@router.post("/boss/logout", response_model=ApiResponse)
async def logout_boss(db: AsyncSession = Depends(get_db)):
    task_state.stop()
    cookie_service = CookieService(db)
    await cookie_service.clear_cookie("boss", "manual logout")
    return ApiResponse(success=True, message="Boss已退出登录，Cookie已清理")


@router.get("/boss/status", response_model=dict)
async def get_boss_status():
    return {
        "running": task_state.running,
        "current": task_state.current_job,
        "total": None,
        "platform": task_state.current_platform,
        "delivered_count": task_state.delivered_count,
        "filtered_count": task_state.filtered_count,
    }


@router.get("/boss/login-status", response_model=dict)
async def get_boss_login_status(db: AsyncSession = Depends(get_db)):
    cookie_service = CookieService(db)
    is_logged_in = await _check_login_status(cookie_service, "boss")
    return {
        "success": True,
        "isLoggedIn": is_logged_in,
        "message": "已登录" if is_logged_in else "未登录",
    }


async def _run_liepin_delivery():
    """后台执行 Liepin 投递任务。"""
    bot = None
    try:
        bot = LiepinBot(config={}, db_session_factory=async_session_maker)
        await bot.init()

        def progress_cb(message: str, current: int, total: int):
            task_state.current_job = message
            sse_manager.publish({
                "type": "progress",
                "platform": "liepin",
                "message": message,
                "current": current,
                "total": total,
            })

        bot.progress_callback = progress_cb
        await bot.run_delivery()
    except Exception as e:
        logger.error("Liepin 投递任务异常：%s", e)
        sse_manager.publish({
            "type": "error",
            "platform": "liepin",
            "message": f"投递异常：{e}",
        })
    finally:
        if bot:
            await bot.close()
        task_state.stop()
        sse_manager.publish({
            "type": "complete",
            "platform": "liepin",
            "message": "投递任务已结束",
        })


@router.post("/liepin/start", response_model=ApiResponse)
async def start_liepin(db: AsyncSession = Depends(get_db)):
    cookie_service = CookieService(db)
    if not await _check_login_status(cookie_service, "liepin"):
        return ApiResponse(success=False, message="请先登录猎聘", status="not_logged_in")
    if task_state.running:
        return ApiResponse(success=False, message="任务已在运行中", status="running")

    task_state.start("liepin")
    asyncio.create_task(_run_liepin_delivery())
    return ApiResponse(success=True, message="Liepin任务启动成功", status="started")


@router.post("/liepin/stop", response_model=ApiResponse)
async def stop_liepin():
    if not task_state.running:
        return ApiResponse(success=False, message="没有正在运行的任务")
    task_state.stop()
    return ApiResponse(success=True, message="Liepin任务停止请求已发送")


@router.post("/liepin/logout", response_model=ApiResponse)
async def logout_liepin(db: AsyncSession = Depends(get_db)):
    task_state.stop()
    cookie_service = CookieService(db)
    await cookie_service.clear_cookie("liepin", "manual logout")
    return ApiResponse(success=True, message="Liepin已退出登录，Cookie已清理")


@router.get("/liepin/status", response_model=dict)
async def get_liepin_status():
    return {
        "running": task_state.running,
        "current": task_state.current_job,
        "total": None,
        "platform": task_state.current_platform,
        "delivered_count": task_state.delivered_count,
        "filtered_count": task_state.filtered_count,
    }


@router.get("/liepin/login-status", response_model=dict)
async def get_liepin_login_status(db: AsyncSession = Depends(get_db)):
    cookie_service = CookieService(db)
    is_logged_in = await _check_login_status(cookie_service, "liepin")
    return {
        "success": True,
        "isLoggedIn": is_logged_in,
        "message": "已登录" if is_logged_in else "未登录",
    }


async def _run_zhilian_delivery():
    """后台执行 Zhilian 投递任务。"""
    bot = None
    try:
        bot = ZhilianBot(config={}, db_session_factory=async_session_maker)
        await bot.init()

        def progress_cb(message: str, current: int, total: int):
            task_state.current_job = message
            sse_manager.publish({
                "type": "progress",
                "platform": "zhilian",
                "message": message,
                "current": current,
                "total": total,
            })

        bot.progress_callback = progress_cb
        await bot.run_delivery()
    except Exception as e:
        logger.error("Zhilian 投递任务异常：%s", e)
        sse_manager.publish({
            "type": "error",
            "platform": "zhilian",
            "message": f"投递异常：{e}",
        })
    finally:
        if bot:
            await bot.close()
        task_state.stop()
        sse_manager.publish({
            "type": "complete",
            "platform": "zhilian",
            "message": "投递任务已结束",
        })


@router.post("/zhilian/start", response_model=ApiResponse)
async def start_zhilian(db: AsyncSession = Depends(get_db)):
    cookie_service = CookieService(db)
    if not await _check_login_status(cookie_service, "zhilian"):
        return ApiResponse(success=False, message="请先登录智联招聘", status="not_logged_in")
    if task_state.running:
        return ApiResponse(success=False, message="任务已在运行中", status="running")

    task_state.start("zhilian")
    asyncio.create_task(_run_zhilian_delivery())
    return ApiResponse(success=True, message="Zhilian任务启动成功", status="started")


@router.post("/zhilian/stop", response_model=ApiResponse)
async def stop_zhilian():
    if not task_state.running:
        return ApiResponse(success=False, message="没有正在运行的任务")
    task_state.stop()
    return ApiResponse(success=True, message="Zhilian任务停止请求已发送")


@router.post("/zhilian/logout", response_model=ApiResponse)
async def logout_zhilian(db: AsyncSession = Depends(get_db)):
    task_state.stop()
    cookie_service = CookieService(db)
    await cookie_service.clear_cookie("zhilian", "manual logout")
    return ApiResponse(success=True, message="Zhilian已退出登录，Cookie已清理")


@router.get("/zhilian/status", response_model=dict)
async def get_zhilian_status():
    return {
        "running": task_state.running,
        "current": task_state.current_job,
        "total": None,
        "platform": task_state.current_platform,
        "delivered_count": task_state.delivered_count,
        "filtered_count": task_state.filtered_count,
    }


@router.get("/zhilian/login-status", response_model=dict)
async def get_zhilian_login_status(db: AsyncSession = Depends(get_db)):
    cookie_service = CookieService(db)
    is_logged_in = await _check_login_status(cookie_service, "zhilian")
    return {
        "success": True,
        "isLoggedIn": is_logged_in,
        "message": "已登录" if is_logged_in else "未登录",
    }


async def _run_job51_delivery():
    """后台执行 Job51 投递任务。"""
    bot = None
    try:
        bot = Job51Bot(config={}, db_session_factory=async_session_maker)
        await bot.init()

        def progress_cb(message: str, current: int, total: int):
            task_state.current_job = message
            sse_manager.publish({
                "type": "progress",
                "platform": "job51",
                "message": message,
                "current": current,
                "total": total,
            })

        bot.progress_callback = progress_cb
        await bot.run_delivery()
    except Exception as e:
        logger.error("Job51 投递任务异常：%s", e)
        sse_manager.publish({
            "type": "error",
            "platform": "job51",
            "message": f"投递异常：{e}",
        })
    finally:
        if bot:
            await bot.close()
        task_state.stop()
        sse_manager.publish({
            "type": "complete",
            "platform": "job51",
            "message": "投递任务已结束",
        })


@router.post("/job51/start", response_model=ApiResponse)
async def start_job51(db: AsyncSession = Depends(get_db)):
    cookie_service = CookieService(db)
    if not await _check_login_status(cookie_service, "job51"):
        return ApiResponse(success=False, message="请先登录51job", status="not_logged_in")
    if task_state.running:
        return ApiResponse(success=False, message="任务已在运行中", status="running")

    task_state.start("job51")
    asyncio.create_task(_run_job51_delivery())
    return ApiResponse(success=True, message="Job51任务启动成功", status="started")


@router.post("/job51/stop", response_model=ApiResponse)
async def stop_job51():
    if not task_state.running:
        return ApiResponse(success=False, message="没有正在运行的任务")
    task_state.stop()
    return ApiResponse(success=True, message="Job51任务停止请求已发送")


@router.post("/job51/logout", response_model=ApiResponse)
async def logout_job51(db: AsyncSession = Depends(get_db)):
    task_state.stop()
    cookie_service = CookieService(db)
    await cookie_service.clear_cookie("job51", "manual logout")
    return ApiResponse(success=True, message="Job51已退出登录，Cookie已清理")


@router.get("/job51/status", response_model=dict)
async def get_job51_status():
    return {
        "running": task_state.running,
        "current": task_state.current_job,
        "total": None,
        "platform": task_state.current_platform,
        "delivered_count": task_state.delivered_count,
        "filtered_count": task_state.filtered_count,
    }


@router.get("/job51/login-status", response_model=dict)
async def get_job51_login_status(db: AsyncSession = Depends(get_db)):
    cookie_service = CookieService(db)
    is_logged_in = await _check_login_status(cookie_service, "job51")
    return {
        "success": True,
        "isLoggedIn": is_logged_in,
        "message": "已登录" if is_logged_in else "未登录",
    }


# ========== Login helpers ==========
_LOGIN_URLS = {
    "boss": "https://www.zhipin.com/web/geek/jobs",
    "liepin": "https://www.liepin.com/zhaopin/",
    "zhilian": "https://www.zhaopin.com/sou/",
    "job51": "https://we.51job.com/pc/search",
}

_LOGIN_BOT_CLASSES = {
    "boss": BossBot,
    "liepin": LiepinBot,
    "zhilian": ZhilianBot,
    "job51": Job51Bot,
}


async def _run_platform_login(platform: str):
    """Open browser, wait for user login, save cookies."""
    bot_class = _LOGIN_BOT_CLASSES[platform]
    url = _LOGIN_URLS[platform]
    bot = None
    try:
        bot = bot_class(config={}, db_session_factory=async_session_maker)
        await bot.init()
        await bot.navigate(url)

        sse_manager.publish({
            "type": "login-status",
            "platform": platform,
            "isLoggedIn": False,
            "message": f"请在新打开的浏览器中登录{platform}",
        })

        # Wait up to 5 minutes for login
        for _ in range(60):  # 60 * 5s = 300s
            await asyncio.sleep(5)

            try:
                if await bot.is_logged_in():
                    cookies = await bot.context.cookies()
                    cookie_json = json.dumps(cookies)

                    async with async_session_maker() as db:
                        cookie_service = CookieService(db)
                        await cookie_service.save_cookie(platform, cookie_json, remark="login")

                    sse_manager.publish({
                        "type": "login-status",
                        "platform": platform,
                        "isLoggedIn": True,
                        "message": f"{platform} 登录成功",
                    })
                    return
            except Exception:
                pass

        sse_manager.publish({
            "type": "login-status",
            "platform": platform,
            "isLoggedIn": False,
            "message": f"{platform} 登录超时",
        })
    except Exception as e:
        logger.error("%s login error: %s", platform, e)
        sse_manager.publish({
            "type": "login-status",
            "platform": platform,
            "isLoggedIn": False,
            "message": f"{platform} 登录异常: {e}",
        })
    finally:
        if bot:
            try:
                await bot.close()
            except Exception:
                pass


@router.post("/boss/login", response_model=ApiResponse)
async def login_boss():
    asyncio.create_task(_run_platform_login("boss"))
    return ApiResponse(success=True, message="请在打开的浏览器中登录Boss直聘")


@router.post("/liepin/login", response_model=ApiResponse)
async def login_liepin():
    asyncio.create_task(_run_platform_login("liepin"))
    return ApiResponse(success=True, message="请在打开的浏览器中登录猎聘")


@router.post("/zhilian/login", response_model=ApiResponse)
async def login_zhilian():
    asyncio.create_task(_run_platform_login("zhilian"))
    return ApiResponse(success=True, message="请在打开的浏览器中登录智联招聘")


@router.post("/job51/login", response_model=ApiResponse)
async def login_job51():
    asyncio.create_task(_run_platform_login("job51"))
    return ApiResponse(success=True, message="请在打开的浏览器中登录51job")
