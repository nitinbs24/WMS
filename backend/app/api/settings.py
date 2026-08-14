"""
Settings router.
- GET  /api/v1/settings/thresholds  — get active thresholds (any authenticated user)
- POST /api/v1/settings/thresholds  — create new threshold version (admin only)
- GET  /api/v1/settings/thresholds/history — list all versions (admin only)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.settings import ThresholdSettings
from app.schemas.settings import ThresholdSettingsOut, ThresholdSettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/thresholds", response_model=ThresholdSettingsOut)
async def get_thresholds(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await settings_service.get_active_thresholds(db)


@router.post("/thresholds", response_model=ThresholdSettingsOut, status_code=201)
async def update_thresholds(
    body: ThresholdSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    ts = await settings_service.create_threshold_version(db, body)
    await db.commit()
    return ts


@router.get("/thresholds/history", response_model=list[ThresholdSettingsOut])
async def threshold_history(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    result = await db.execute(
        select(ThresholdSettings).order_by(ThresholdSettings.version.desc())
    )
    return list(result.scalars().all())
