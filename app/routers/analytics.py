from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models import BossData, LiepinData, ZhilianData, Job51Data
from app.schemas import BossStatsResponse, BossDataResponse, ApiResponse, LiepinDataResponse, ZhilianDataResponse, Job51DataResponse
from app.services.boss_service import BossService
from app.services.liepin_service import LiepinService
from app.services.zhilian_service import ZhilianService
from app.services.job51_service import Job51Service

router = APIRouter()


@router.get("/boss/stats", response_model=dict)
async def get_boss_stats(db: AsyncSession = Depends(get_db)):
    service = BossService(db)
    stats = await service.get_stats()
    return {"success": True, **stats}


@router.get("/boss/list", response_model=dict)
async def get_boss_list(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = BossService(db)
    jobs = await service.get_job_list(limit=limit, offset=offset, status=status)

    # 查询总记录数
    count_query = select(func.count()).select_from(BossData)
    if status:
        count_query = count_query.where(BossData.delivery_status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {
        "success": True,
        "data": [BossDataResponse.model_validate(j).model_dump() for j in jobs],
        "total": total,
    }


@router.post("/boss/reload", response_model=ApiResponse)
async def reload_boss():
    return ApiResponse(success=True, message="数据重新加载完成")


@router.get("/liepin/stats", response_model=dict)
async def get_liepin_stats(db: AsyncSession = Depends(get_db)):
    service = LiepinService(db)
    stats = await service.get_stats()
    return {"success": True, **stats}


@router.get("/liepin/list", response_model=dict)
async def get_liepin_list(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = LiepinService(db)
    jobs = await service.get_job_list(limit=limit, offset=offset, status=status)

    count_query = select(func.count()).select_from(LiepinData)
    if status == "delivered":
        count_query = count_query.where(LiepinData.delivered == 1)
    elif status == "pending":
        count_query = count_query.where(LiepinData.delivered == 0)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {
        "success": True,
        "data": [LiepinDataResponse.model_validate(j).model_dump() for j in jobs],
        "total": total,
    }


@router.post("/liepin/reload", response_model=ApiResponse)
async def reload_liepin():
    return ApiResponse(success=True, message="数据重新加载完成")


@router.get("/zhilian/stats", response_model=dict)
async def get_zhilian_stats(db: AsyncSession = Depends(get_db)):
    service = ZhilianService(db)
    stats = await service.get_stats()
    return {"success": True, **stats}


@router.get("/zhilian/list", response_model=dict)
async def get_zhilian_list(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = ZhilianService(db)
    jobs = await service.get_job_list(limit=limit, offset=offset, status=status)

    count_query = select(func.count()).select_from(ZhilianData)
    if status == "delivered":
        count_query = count_query.where(ZhilianData.delivered == 1)
    elif status == "pending":
        count_query = count_query.where(ZhilianData.delivered == 0)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {
        "success": True,
        "data": [ZhilianDataResponse.model_validate(j).model_dump() for j in jobs],
        "total": total,
    }


@router.post("/zhilian/reload", response_model=ApiResponse)
async def reload_zhilian():
    return ApiResponse(success=True, message="数据重新加载完成")


@router.get("/job51/stats", response_model=dict)
async def get_job51_stats(db: AsyncSession = Depends(get_db)):
    service = Job51Service(db)
    stats = await service.get_stats()
    return {"success": True, **stats}


@router.get("/job51/list", response_model=dict)
async def get_job51_list(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = Job51Service(db)
    jobs = await service.get_job_list(limit=limit, offset=offset, status=status)

    count_query = select(func.count()).select_from(Job51Data)
    if status == "delivered":
        count_query = count_query.where(Job51Data.delivered == 1)
    elif status == "pending":
        count_query = count_query.where(Job51Data.delivered == 0)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {
        "success": True,
        "data": [Job51DataResponse.model_validate(j).model_dump() for j in jobs],
        "total": total,
    }


@router.post("/job51/reload", response_model=ApiResponse)
async def reload_job51():
    return ApiResponse(success=True, message="数据重新加载完成")
