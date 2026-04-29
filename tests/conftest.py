import pytest
from app.database import Base, engine


@pytest.fixture(autouse=True)
async def ensure_tables():
    """Ensure all database tables exist before each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
