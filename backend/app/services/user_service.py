"""
User service — all user CRUD lives here, routers stay thin.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def create_user(db: AsyncSession, body: UserCreate) -> User:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")
    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.flush()
    return user


async def update_user(db: AsyncSession, user_id: uuid.UUID, body: UserUpdate) -> User:
    user = await get_user(db, user_id)
    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        user.email = body.email
    if body.role is not None:
        user.role = body.role
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    await db.flush()
    return user


async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    user = await get_user(db, user_id)
    await db.delete(user)
    await db.flush()
