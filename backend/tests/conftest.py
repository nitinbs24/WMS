"""
pytest conftest — shared fixtures for the Warehaven test suite.
"""
from __future__ import annotations

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


@pytest_asyncio.fixture
async def test_engine():
    """Fresh schema per test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Session for fixtures — uses commit() so API routes can see the data."""
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine):
    """HTTP test client — each request gets its own session from the SAME test engine as db_session."""
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# Force client and db_session to share the same test_engine fixture instance
# by making both depend on it. pytest caches fixtures within the same test's
# fixture graph, so test_engine is only instantiated once per test.


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        name="Test Admin",
        email="testadmin@example.com",
        password_hash=hash_password("testpassword"),
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()   # commit so the API route can see the user
    return user


@pytest_asyncio.fixture
async def admin_token(client, admin_user) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testadmin@example.com", "password": "testpassword"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def default_thresholds(db_session: AsyncSession) -> ThresholdSettings:
    ts = ThresholdSettings(version=1)
    db_session.add(ts)
    await db_session.commit()
    return ts
