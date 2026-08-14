"""
User CRUD API tests.
Tests: list users (admin), create, get self, update, delete, RBAC.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_users_as_admin(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(u["role"] == "admin" for u in data)


@pytest.mark.asyncio
async def test_list_users_forbidden_for_staff(client: AsyncClient, db_session):
    from app.models.user import User
    from app.core.security import hash_password
    staff = User(name="Staff", email="staff2@example.com", password_hash=hash_password("pass"), role="staff")
    db_session.add(staff)
    await db_session.commit()
    login = await client.post("/api/v1/auth/login", json={"email": "staff2@example.com", "password": "pass"})
    token = login.json()["access_token"]
    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/v1/users",
        json={"name": "New Manager", "email": "manager@example.com", "password": "pass123", "role": "manager"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "manager@example.com"
    assert data["role"] == "manager"


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient, admin_token: str, admin_user):
    resp = await client.post(
        "/api/v1/users",
        json={"name": "Dup", "email": "testadmin@example.com", "password": "x", "role": "staff"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_self(client: AsyncClient, admin_user, admin_token: str):
    resp = await client.get(
        f"/api/v1/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(admin_user.id)


@pytest.mark.asyncio
async def test_delete_self_forbidden(client: AsyncClient, admin_user, admin_token: str):
    resp = await client.delete(
        f"/api/v1/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
