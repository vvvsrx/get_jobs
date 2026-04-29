from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ApiResponse
from app.services.cookie_service import CookieService

router = APIRouter()


@router.post("/cookie/save", response_model=ApiResponse)
async def save_cookie(
    platform: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    service = CookieService(db)
    # 实际保存由 worker 在登录成功后触发，此处为兼容前端接口
    await service.save_cookie(platform, "[]", "api save")
    return ApiResponse(success=True, message="Cookie保存成功")
