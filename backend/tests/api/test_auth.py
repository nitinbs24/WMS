"""Auth API integration tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "testadmin@warehaven.local",
        "password": "testpassword",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "testadmin@warehaven.local",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    assert data["email"] == "testadmin@warehaven.local"


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_staff_cannot_access_users(client: AsyncClient, db_session):
    from app.models.user import User
    from app.core.security import hash_password
    staff = User(name="Staff", email="staff@test.local", password_hash=hash_password("pass"), role="staff")
    db_session.add(staff)
    await db_session.flush()
    login = await client.post("/api/v1/auth/login", json={"email": "staff@test.local", "password": "pass"})
    token = login.json()["access_token"]
    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
