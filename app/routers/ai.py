from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import AiConfigSchema, ApiResponse
from app.services.ai_service import AiService

router = APIRouter()


@router.get("/ai/config", response_model=dict)
async def get_ai_config(db: AsyncSession = Depends(get_db)):
    service = AiService(db)
    config = await service.get_ai_config()
    if not config:
        return {"success": True, "introduce": "", "prompt": ""}
    return {
        "success": True,
        **AiConfigSchema.model_validate(config).model_dump(),
    }


@router.post("/ai/config", response_model=ApiResponse)
async def update_ai_config(
    data: AiConfigSchema,
    db: AsyncSession = Depends(get_db),
):
    service = AiService(db)
    await service.update_ai_config(
        introduce=data.introduce,
        prompt=data.prompt,
    )
    return ApiResponse(success=True, message="AI配置已保存")
