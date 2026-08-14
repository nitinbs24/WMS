"""
Optimization Runs router.

POST   /api/v1/runs                      — trigger a run (manager+)
GET    /api/v1/runs                      — list runs (any auth)
GET    /api/v1/runs/{id}                 — get run status + metrics (any auth)
GET    /api/v1/runs/{id}/assignments     — full assignment set (any auth)
GET    /api/v1/runs/{id}/exceptions      — exception list (any auth)
POST   /api/v1/runs/{id}/rollback        — revert slot states (manager+)
GET    /api/v1/runs/{id}/export.csv      — CSV export (any auth)
GET    /api/v1/runs/{id}/report          — summary report (any auth)
"""
from __future__ import annotations

import csv
import io
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role
from app.core.config import get_settings
from app.models.optimization import OptimizationRun, RunException, SlotAssignment
from app.models.settings import ThresholdSettings
from app.models.user import User
from app.models.warehouse import Slot
from app.schemas.optimization import RunCreate, RunOut, AssignmentOut, ExceptionOut, RunReport

router = APIRouter(prefix="/runs", tags=["runs"])
settings = get_settings()

_VALID_SPACE_ALGOS = {"ffdh_com", "blf_stratified"}
_VALID_PICK_ALGOS = {"golden_zone", "affinity_clustering", "s_shape_routing"}


@router.post("", response_model=RunOut, status_code=201)
async def create_run(
    body: RunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    """Validate, create a queued run row, and enqueue an arq job."""
    # Validate algorithm matches goal
    if body.goal == "space_efficiency" and body.algorithm not in _VALID_SPACE_ALGOS:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"Algorithm '{body.algorithm}' is not valid for space_efficiency. Use: {_VALID_SPACE_ALGOS}")
    if body.goal == "picking_efficiency" and body.algorithm not in _VALID_PICK_ALGOS:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"Algorithm '{body.algorithm}' is not valid for picking_efficiency. Use: {_VALID_PICK_ALGOS}")

    # Get active thresholds snapshot
    ts_result = await db.execute(
        select(ThresholdSettings)
        .where(ThresholdSettings.is_active == True)  # noqa: E712
        .order_by(ThresholdSettings.version.desc())
        .limit(1)
    )
    ts = ts_result.scalar_one_or_none()
    threshold_snapshot = _threshold_snapshot(ts) if ts else _default_snapshot()

    # Create queued run
    run = OptimizationRun(
        goal=body.goal,
        algorithm=body.algorithm,
        scope=body.scope,
        triggered_by=current_user.id,
        status="queued",
        thresholds_snapshot=threshold_snapshot,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Enqueue arq job (non-blocking; worker picks it up)
    try:
        from arq import create_pool
        redis = await create_pool(settings.REDIS_URL)
        await redis.enqueue_job("run_optimization", str(run.id))
        await redis.close()
    except Exception:
        # Redis unavailable (e.g. in tests without Redis) — job stays "queued"
        pass

    return run


@router.get("", response_model=list[RunOut])
async def list_runs(
    goal: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(OptimizationRun).order_by(OptimizationRun.created_at.desc()).limit(limit)
    if goal:
        stmt = stmt.where(OptimizationRun.goal == goal)
    if status:
        stmt = stmt.where(OptimizationRun.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await _get_run_or_404(db, run_id)


@router.get("/{run_id}/assignments", response_model=list[AssignmentOut])
async def get_assignments(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_run_or_404(db, run_id)
    result = await db.execute(
        select(SlotAssignment).where(SlotAssignment.run_id == run_id)
    )
    return list(result.scalars().all())


@router.get("/{run_id}/exceptions", response_model=list[ExceptionOut])
async def get_exceptions(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_run_or_404(db, run_id)
    result = await db.execute(
        select(RunException).where(RunException.run_id == run_id)
    )
    return list(result.scalars().all())


@router.post("/{run_id}/rollback", status_code=200)
async def rollback_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("manager", "admin")),
):
    """
    Revert all slot statuses modified by this run back to 'empty'.
    Deletes the run's SlotAssignment rows.
    """
    run = await _get_run_or_404(db, run_id)
    if run.status not in ("completed", "completed_with_exceptions"):
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=f"Cannot rollback run with status '{run.status}'")

    # Get assigned slot ids
    result = await db.execute(select(SlotAssignment.slot_id).where(SlotAssignment.run_id == run_id))
    slot_ids = [r[0] for r in result.all()]

    # Reset slot statuses
    if slot_ids:
        from sqlalchemy import update
        await db.execute(update(Slot).where(Slot.id.in_(slot_ids)).values(status="empty"))

    # Delete assignments
    from sqlalchemy import delete
    await db.execute(delete(SlotAssignment).where(SlotAssignment.run_id == run_id))
    run.status = "queued"   # mark as rolled back / re-queueable
    await db.commit()
    return {"rolled_back_slots": len(slot_ids)}


@router.get("/{run_id}/report", response_model=RunReport)
async def get_run_report(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    run = await _get_run_or_404(db, run_id)
    asgn_result = await db.execute(select(SlotAssignment).where(SlotAssignment.run_id == run_id))
    assignments = list(asgn_result.scalars().all())
    exc_result = await db.execute(select(RunException).where(RunException.run_id == run_id))
    exceptions = list(exc_result.scalars().all())

    metrics = run.summary_metrics or {}
    return RunReport(
        run=run,
        assignments_count=len(assignments),
        exceptions_count=len(exceptions),
        fill_rate_pct=metrics.get("fill_rate_pct"),
        avg_pick_distance_m=metrics.get("avg_pick_distance_m"),
        summary_metrics=metrics,
    )


@router.get("/{run_id}/export.csv")
async def export_run_csv(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_run_or_404(db, run_id)
    result = await db.execute(select(SlotAssignment).where(SlotAssignment.run_id == run_id))
    assignments = list(result.scalars().all())

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["id", "run_id", "pallet_id", "product_id", "slot_id", "score", "is_override"])
    writer.writeheader()
    for a in assignments:
        writer.writerow({
            "id": a.id, "run_id": a.run_id, "pallet_id": a.pallet_id,
            "product_id": a.product_id, "slot_id": a.slot_id,
            "score": a.score, "is_override": a.is_override,
        })
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=run_{run_id}.csv"},
    )


# ─── helpers ───

async def _get_run_or_404(db: AsyncSession, run_id: uuid.UUID) -> OptimizationRun:
    from fastapi import HTTPException
    result = await db.execute(select(OptimizationRun).where(OptimizationRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def _threshold_snapshot(ts: ThresholdSettings) -> dict:
    return {
        "version": ts.version,
        "heavy_weight_kg": float(ts.heavy_weight_kg),
        "medium_weight_kg": float(ts.medium_weight_kg),
        "com_threshold": float(ts.com_threshold),
        "blf_com_threshold": float(ts.blf_com_threshold),
        "aisle_a_density_cap": float(ts.aisle_a_density_cap),
        "ergonomic_factors": ts.ergonomic_factors,
        "pick_lookback_days": ts.pick_lookback_days,
    }


def _default_snapshot() -> dict:
    return {
        "heavy_weight_kg": 600.0, "medium_weight_kg": 300.0,
        "com_threshold": 0.55, "blf_com_threshold": 0.60,
        "aisle_a_density_cap": 0.35,
        "ergonomic_factors": {"L1": 0.90, "L2": 1.00, "L3": 0.70, "L4": 0.50},
        "pick_lookback_days": 90,
    }
