import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.routers import config, ai, cookie, jobs, analytics, sse
from app.config import settings

_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
_INDEX_HTML = os.path.join(_STATIC_DIR, "index.html")


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
    return {"status": "UP"}


# SPA fallback: Next.js static export writes pages as {route}.html.
# We need to map /boss -> boss.html, /51job -> 51job.html, etc.
# StaticFiles(html=True) only handles / -> index.html, so we use a
# catch-all route instead.
if os.path.isdir(_STATIC_DIR) and os.path.isfile(_INDEX_HTML):
    @app.get("/{full_path:path}")
    async def serve_static(full_path: str):
        # Let FastAPI return proper 404 JSON for missing API endpoints
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        # Prevent directory traversal
        file_path = os.path.normpath(os.path.join(_STATIC_DIR, full_path))
        if not file_path.startswith(os.path.normpath(_STATIC_DIR)):
            raise HTTPException(status_code=404, detail="Not Found")

        # Direct file (assets, favicon, etc.)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # No extension: try .html (Next.js static-export pages)
        if "." not in os.path.basename(full_path):
            html_path = file_path + ".html"
            if os.path.isfile(html_path):
                return FileResponse(html_path)

        # SPA fallback
        return FileResponse(_INDEX_HTML)
