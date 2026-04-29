from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas import (
    BossConfigSchema, BossBlacklistCreate, BossBlacklistResponse,
    ApiResponse, BossOptionSchema, LiepinConfigSchema, LiepinOptionSchema,
    ZhilianConfigSchema, ZhilianOptionSchema,
    Job51ConfigSchema, Job51OptionSchema,
)
from app.services.config_service import ConfigService

router = APIRouter()


async def get_config_service(db: AsyncSession = Depends(get_db)):
    return ConfigService(db)


# ========== Boss ==========
@router.get("/boss/config", response_model=dict)
async def get_boss_config(service: ConfigService = Depends(get_config_service)):
    config = await service.get_or_create_boss_config()
    blacklist = await service.get_blacklist()
    options = {
        "city": [BossOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_options_by_type("city")],
        "industry": [BossOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_options_by_type("industry")],
        "experience": [BossOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_options_by_type("experience")],
        "jobType": [BossOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_options_by_type("jobType")],
        "salary": [BossOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_options_by_type("salary")],
        "degree": [BossOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_options_by_type("degree")],
        "scale": [BossOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_options_by_type("scale")],
        "stage": [BossOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_options_by_type("stage")],
    }
    return {
        "success": True,
        "config": BossConfigSchema.model_validate(config).model_dump(by_alias=True),
        "options": options,
        "blacklist": [BossBlacklistResponse.model_validate(b).model_dump(by_alias=True) for b in blacklist],
    }


@router.put("/boss/config", response_model=ApiResponse)
async def update_boss_config(
    data: BossConfigSchema,
    service: ConfigService = Depends(get_config_service),
):
    update_data = data.model_dump(exclude={"id", "created_at", "updated_at"}, exclude_unset=True, by_alias=False)
    await service.update_boss_config(**update_data)
    return ApiResponse(success=True, message="配置已保存")


@router.get("/boss/config/blacklist", response_model=list)
async def get_blacklist(service: ConfigService = Depends(get_config_service)):
    items = await service.get_blacklist()
    return [BossBlacklistResponse.model_validate(i).model_dump(by_alias=True) for i in items]


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
    return [BossOptionSchema.model_validate(o).model_dump(by_alias=True) for o in options]


# ========== Liepin ==========
@router.get("/liepin/config", response_model=dict)
async def get_liepin_config(service: ConfigService = Depends(get_config_service)):
    config = await service.get_or_create_liepin_config()
    options = {
        "city": [LiepinOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_liepin_options_by_type("city")],
    }
    return {
        "success": True,
        "config": LiepinConfigSchema.model_validate(config).model_dump(by_alias=True),
        "options": options,
    }


@router.put("/liepin/config", response_model=ApiResponse)
async def update_liepin_config(
    data: LiepinConfigSchema,
    service: ConfigService = Depends(get_config_service),
):
    update_data = data.model_dump(exclude={"id", "created_at", "updated_at"}, exclude_unset=True, by_alias=False)
    await service.update_liepin_config(**update_data)
    return ApiResponse(success=True, message="配置已保存")


@router.get("/liepin/config/options/{type}", response_model=list)
async def get_liepin_options(type: str, service: ConfigService = Depends(get_config_service)):
    options = await service.get_liepin_options_by_type(type)
    return [LiepinOptionSchema.model_validate(o).model_dump(by_alias=True) for o in options]


# ========== Zhilian ==========
@router.get("/zhilian/config", response_model=dict)
async def get_zhilian_config(service: ConfigService = Depends(get_config_service)):
    config = await service.get_or_create_zhilian_config()
    options = {
        "city": [ZhilianOptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_zhilian_options_by_type("city")],
    }
    return {
        "success": True,
        "config": ZhilianConfigSchema.model_validate(config).model_dump(by_alias=True),
        "options": options,
    }


@router.put("/zhilian/config", response_model=ApiResponse)
async def update_zhilian_config(
    data: ZhilianConfigSchema,
    service: ConfigService = Depends(get_config_service),
):
    update_data = data.model_dump(exclude={"id", "created_at", "updated_at"}, exclude_unset=True, by_alias=False)
    await service.update_zhilian_config(**update_data)
    return ApiResponse(success=True, message="配置已保存")


@router.get("/zhilian/config/options/{type}", response_model=list)
async def get_zhilian_options(type: str, service: ConfigService = Depends(get_config_service)):
    options = await service.get_zhilian_options_by_type(type)
    return [ZhilianOptionSchema.model_validate(o).model_dump(by_alias=True) for o in options]


# ========== Job51 ==========
@router.get("/job51/config", response_model=dict)
async def get_job51_config(service: ConfigService = Depends(get_config_service)):
    config = await service.get_or_create_job51_config()
    options = {
        "jobArea": [Job51OptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_job51_options_by_type("jobArea")],
        "salary": [Job51OptionSchema.model_validate(o).model_dump(by_alias=True) for o in await service.get_job51_options_by_type("salary")],
    }
    return {
        "success": True,
        "config": Job51ConfigSchema.model_validate(config).model_dump(by_alias=True),
        "options": options,
    }


@router.put("/job51/config", response_model=ApiResponse)
async def update_job51_config(
    data: Job51ConfigSchema,
    service: ConfigService = Depends(get_config_service),
):
    update_data = data.model_dump(exclude={"id", "created_at", "updated_at"}, exclude_unset=True, by_alias=False)
    await service.update_job51_config(**update_data)
    return ApiResponse(success=True, message="配置已保存")


@router.get("/job51/config/options/{type}", response_model=list)
async def get_job51_options(type: str, service: ConfigService = Depends(get_config_service)):
    options = await service.get_job51_options_by_type(type)
    return [Job51OptionSchema.model_validate(o).model_dump(by_alias=True) for o in options]


# ========== Env Config (key-value store) ==========
from sqlalchemy import select
from app.models import Config as ConfigModel

_ENV_KEYS = ["HOOK_URL", "BASE_URL", "API_KEY", "MODEL", "BOT_IS_SEND"]


@router.get("/config", response_model=dict)
async def get_env_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ConfigModel).where(ConfigModel.config_key.in_(_ENV_KEYS)))
    rows = result.scalars().all()
    data = {row.config_key: row.config_value or "" for row in rows}
    # Ensure all keys exist with defaults
    for key in _ENV_KEYS:
        if key not in data:
            data[key] = ""
    return {"success": True, "data": data}


@router.post("/config", response_model=ApiResponse)
async def save_env_config(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    for key in _ENV_KEYS:
        value = payload.get(key, "")
        result = await db.execute(select(ConfigModel).where(ConfigModel.config_key == key))
        row = result.scalar_one_or_none()
        if row:
            row.config_value = value
        else:
            db.add(ConfigModel(config_key=key, config_value=value, config_type="string", category="env"))
    await db.commit()
    return ApiResponse(success=True, message="配置已保存")


@router.post("/config/options/import", response_model=ApiResponse)
async def import_options(db: AsyncSession = Depends(get_db)):
    from app.services.option_seed_service import OptionSeedService
    service = OptionSeedService(db)
    results = await service.import_all()
    total = sum(len(v) for v in results.values() if isinstance(v, list))
    return ApiResponse(success=True, message=f"基础数据更新完成，共导入 {total} 条记录")
