"""Assignments router — manual override for slot assignments."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User

router = APIRouter(prefix="/assignments", tags=["assignments"])


class OverrideRequest(BaseModel):
    slot_id: uuid.UUID


@router.patch("/{assignment_id}")
async def override_assignment(
    assignment_id: uuid.UUID,
    body: OverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    """
    Move a pallet/SKU to a different slot.
    Validates against active ThresholdSettings before accepting.
    Returns 409 with reason_code if unsafe.
    """
    raise HTTPException(status_code=501, detail="Implemented in Phase 5")
