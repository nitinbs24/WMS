"""Admin settings router — versioned threshold configuration."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role
from app.models.settings import ThresholdSettings
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])


def _threshold_to_dict(t: ThresholdSettings) -> dict:
    return {
        "id": str(t.id),
        "version": t.version,
        "heavy_weight_kg": float(t.heavy_weight_kg),
        "medium_weight_kg": float(t.medium_weight_kg),
        "com_threshold": float(t.com_threshold),
        "blf_com_threshold": float(t.blf_com_threshold),
        "aisle_a_density_cap": float(t.aisle_a_density_cap),
        "ergonomic_factors": t.ergonomic_factors,
        "pick_lookback_days": t.pick_lookback_days,
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat(),
    }


@router.get("/thresholds")
async def get_active_thresholds(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the currently active ThresholdSettings version."""
    result = await db.execute(
        select(ThresholdSettings).where(ThresholdSettings.is_active == True).order_by(ThresholdSettings.version.desc())
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="No threshold settings found — seed the database first")
    return _threshold_to_dict(settings)


@router.put("/thresholds")
async def update_thresholds(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    Create a new threshold version. Does NOT mutate the existing row.
    Past runs remain auditable against the thresholds active at their time.
    """
    raise HTTPException(status_code=501, detail="Implemented in Phase 5")
