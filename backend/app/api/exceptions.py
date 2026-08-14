"""Exceptions router — view and resolve unplaced-item queue."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User

router = APIRouter(prefix="/exceptions", tags=["exceptions"])


@router.patch("/{exception_id}")
async def resolve_exception(
    exception_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    """Mark an exception as resolved, optionally with a manual slot assignment."""
    raise HTTPException(status_code=501, detail="Implemented in Phase 5")
