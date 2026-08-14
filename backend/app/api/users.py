"""
Users router.
- GET  /api/v1/users         — list all users (admin only)
- POST /api/v1/users         — create user (admin only)
- GET  /api/v1/users/{id}   — get user (admin or self)
- PUT  /api/v1/users/{id}   — update user (admin only)
- DELETE /api/v1/users/{id} — delete user (admin only)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.schemas.user import UserOut, UserCreate, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return await user_service.list_users(db)


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    user = await user_service.create_user(db, body)
    await db.commit()
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admins can fetch any user; others can only fetch themselves
    if current_user.role != "admin" and current_user.id != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorised")
    return await user_service.get_user(db, user_id)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    user = await user_service.update_user(db, user_id, body)
    await db.commit()
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    if str(current_user.id) == str(user_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    await user_service.delete_user(db, user_id)
    await db.commit()
