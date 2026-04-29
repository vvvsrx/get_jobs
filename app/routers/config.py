from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas import (
    BossConfigSchema, BossBlacklistCreate, BossBlacklistResponse,
    ApiResponse, BossOptionSchema, LiepinConfigSchema, ZhilianConfigSchema,
    Job51ConfigSchema,
)
from app.services.config_service import ConfigService

router = APIRouter()


async def get_config_service(db: AsyncSession = Depends(get_db)):
    return ConfigService(db)


@router.get("/boss/config", response_model=dict)
async def get_boss_config(service: ConfigService = Depends(get_config_service)):
    config = await service.get_or_create_boss_config()
    blacklist = await service.get_blacklist()
    return {
        "success": True,
        **BossConfigSchema.model_validate(config).model_dump(),
        "blacklist": [BossBlacklistResponse.model_validate(b).model_dump() for b in blacklist],
    }


@router.put("/boss/config", response_model=ApiResponse)
async def update_boss_config(
    data: BossConfigSchema,
    service: ConfigService = Depends(get_config_service),
):
    update_data = data.model_dump(exclude={"id", "created_at", "updated_at"}, exclude_unset=True)
    await service.update_boss_config(**update_data)
    return ApiResponse(success=True, message="配置已保存")


@router.get("/boss/config/blacklist", response_model=list)
async def get_blacklist(service: ConfigService = Depends(get_config_service)):
    items = await service.get_blacklist()
    return [BossBlacklistResponse.model_validate(i).model_dump() for i in items]


@router.post("/boss/config/blacklist", response_model=ApiResponse)
async def add_blacklist(
    data: BossBlacklistCreate,
    service: ConfigService = Depends(get_config_service),
):
    await service.add_blacklist(data.type, data.value)
    return ApiResponse(success=True, message="黑名单添加成功")


@router.delete("/boss/config/blacklist/{id}", response_model=ApiResponse)
async def delete_blacklist(
    id: int,
    service: ConfigService = Depends(get_config_service),
):
    success = await service.delete_blacklist(id)
    if not success:
        raise HTTPException(status_code=404, detail="黑名单项不存在")
    return ApiResponse(success=True, message="黑名单删除成功")


@router.get("/boss/config/options/{type}", response_model=list)
async def get_options(type: str, service: ConfigService = Depends(get_config_service)):
    options = await service.get_options_by_type(type)
    return [BossOptionSchema.model_validate(o).model_dump() for o in options]


@router.get("/liepin/config", response_model=dict)
async def get_liepin_config(service: ConfigService = Depends(get_config_service)):
    config = await service.get_or_create_liepin_config()
    return {
        "success": True,
        **LiepinConfigSchema.model_validate(config).model_dump(),
    }


@router.put("/liepin/config", response_model=ApiResponse)
async def update_liepin_config(
    data: LiepinConfigSchema,
    service: ConfigService = Depends(get_config_service),
):
    update_data = data.model_dump(exclude={"id", "created_at", "updated_at"}, exclude_unset=True)
    await service.update_liepin_config(**update_data)
    return ApiResponse(success=True, message="配置已保存")


@router.get("/liepin/config/options/{type}", response_model=list)
async def get_liepin_options(type: str, service: ConfigService = Depends(get_config_service)):
    options = await service.get_liepin_options_by_type(type)
    return [{"type": o.type, "name": o.name, "code": o.code} for o in options]


@router.get("/zhilian/config", response_model=dict)
async def get_zhilian_config(service: ConfigService = Depends(get_config_service)):
    config = await service.get_or_create_zhilian_config()
    return {
        "success": True,
        **ZhilianConfigSchema.model_validate(config).model_dump(),
    }


@router.put("/zhilian/config", response_model=ApiResponse)
async def update_zhilian_config(
    data: ZhilianConfigSchema,
    service: ConfigService = Depends(get_config_service),
):
    update_data = data.model_dump(exclude={"id", "created_at", "updated_at"}, exclude_unset=True)
    await service.update_zhilian_config(**update_data)
    return ApiResponse(success=True, message="配置已保存")


@router.get("/zhilian/config/options/{type}", response_model=list)
async def get_zhilian_options(type: str, service: ConfigService = Depends(get_config_service)):
    options = await service.get_zhilian_options_by_type(type)
    return [{"type": o.type, "name": o.name, "code": o.code} for o in options]


@router.get("/job51/config", response_model=dict)
async def get_job51_config(service: ConfigService = Depends(get_config_service)):
    config = await service.get_or_create_job51_config()
    return {
        "success": True,
        **Job51ConfigSchema.model_validate(config).model_dump(),
    }


@router.put("/job51/config", response_model=ApiResponse)
async def update_job51_config(
    data: Job51ConfigSchema,
    service: ConfigService = Depends(get_config_service),
):
    update_data = data.model_dump(exclude={"id", "created_at", "updated_at"}, exclude_unset=True)
    await service.update_job51_config(**update_data)
    return ApiResponse(success=True, message="配置已保存")


@router.get("/job51/config/options/{type}", response_model=list)
async def get_job51_options(type: str, service: ConfigService = Depends(get_config_service)):
    options = await service.get_job51_options_by_type(type)
    return [{"type": o.type, "name": o.name, "code": o.code} for o in options]
