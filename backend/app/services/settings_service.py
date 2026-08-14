"""
Settings service — versioned threshold management.
Each update creates a new row; the previous active version is deactivated.
Past runs always reference their own snapshot via threshold_version FK.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import ThresholdSettings
from app.schemas.settings import ThresholdSettingsUpdate


async def get_active_thresholds(db: AsyncSession) -> ThresholdSettings:
    result = await db.execute(
        select(ThresholdSettings)
        .where(ThresholdSettings.is_active == True)  # noqa: E712
        .order_by(ThresholdSettings.version.desc())
        .limit(1)
    )
    ts = result.scalar_one_or_none()
    if not ts:
        raise HTTPException(
            status_code=404,
            detail="No threshold settings found — run the seed script first.",
        )
    return ts


async def create_threshold_version(
    db: AsyncSession, body: ThresholdSettingsUpdate
) -> ThresholdSettings:
    # Deactivate all current active rows
    await db.execute(
        update(ThresholdSettings)
        .where(ThresholdSettings.is_active == True)  # noqa: E712
        .values(is_active=False)
    )
    # Get next version number
    result = await db.execute(select(ThresholdSettings.version).order_by(ThresholdSettings.version.desc()).limit(1))
    latest = result.scalar_one_or_none() or 0

    new_ts = ThresholdSettings(
        version=latest + 1,
        heavy_weight_kg=body.heavy_weight_kg,
        medium_weight_kg=body.medium_weight_kg,
        com_threshold=body.com_threshold,
        blf_com_threshold=body.blf_com_threshold,
        aisle_a_density_cap=body.aisle_a_density_cap,
        ergonomic_factors=body.ergonomic_factors,
        pick_lookback_days=body.pick_lookback_days,
        is_active=True,
    )
    db.add(new_ts)
    await db.flush()
    return new_ts
