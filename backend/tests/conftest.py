"""
pytest configuration and shared fixtures.
"""
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import app.database


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session(monkeypatch):
    """In-memory SQLite session for fast tests."""
    # Import models to ensure all tables are registered on Base
    import app.models.db_models  # noqa
    from app.database import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Patch AsyncSessionLocal and engine in app.database so graph nodes and dependencies use test db
    monkeypatch.setattr(app.database, "AsyncSessionLocal", Session)
    monkeypatch.setattr(app.database, "engine", engine)

    async with Session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
