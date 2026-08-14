"""Users router — Admin-only CRUD for user management."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.core.security import hash_password
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_role("admin")


class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # admin | manager | staff


class UpdateUserRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    password: str | None = None


@router.get("")
async def list_users(db: AsyncSession = Depends(get_db), _=Depends(admin_only)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": str(u.id), "name": u.name, "email": u.email, "role": u.role} for u in users]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: CreateUserRequest, db: AsyncSession = Depends(get_db), _=Depends(admin_only)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")
    user = User(name=body.name, email=body.email, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    await db.flush()
    return {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role}


@router.patch("/{user_id}")
async def update_user(user_id: uuid.UUID, body: UpdateUserRequest, db: AsyncSession = Depends(get_db), _=Depends(admin_only)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        user.email = body.email
    if body.role is not None:
        user.role = body.role
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    return {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(admin_only)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
