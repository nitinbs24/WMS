"""
pytest conftest — shared fixtures for the Warehaven test suite.
"""
from __future__ import annotations

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User
from app.models.settings import ThresholdSettings

TEST_DATABASE_URL = "postgresql+asyncpg://warehaven:warehaven@localhost:5432/warehaven_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """HTTP test client with DB session override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        name="Test Admin",
        email="testadmin@warehaven.local",
        password_hash=hash_password("testpassword"),
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_token(client, admin_user) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": "testadmin@warehaven.local", "password": "testpassword"})
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def default_thresholds(db_session: AsyncSession) -> ThresholdSettings:
    ts = ThresholdSettings(version=1)
    db_session.add(ts)
    await db_session.flush()
    return ts
