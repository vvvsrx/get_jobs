from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import config, ai, cookie, jobs, analytics, sse
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed options
    from app.database import init_db, async_session_maker
    from app.services.option_seed_service import OptionSeedService
    await init_db()
    async with async_session_maker() as session:
        seed_service = OptionSeedService(session)
        await seed_service.import_all()
    yield
    # Shutdown


app = FastAPI(
    title="get_jobs",
    description="求职自动投递工具 - Python 重构版",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(cookie.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(sse.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
