"""Optimization runs router — trigger, list, status, assignments, rollback."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.optimization import OptimizationRun
from app.models.user import User

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    goal: str       # space_efficiency | picking_efficiency
    algorithm: str  # see domain enums in TRD §3
    scope: str      # full | incremental


@router.post("")
async def create_run(
    body: CreateRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    """Enqueue an optimization run. Returns immediately with run_id and status=queued."""
    raise HTTPException(status_code=501, detail="Implemented in Phase 5")


@router.get("")
async def list_runs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(OptimizationRun).order_by(OptimizationRun.created_at.desc()))
    runs = result.scalars().all()
    return [{"id": str(r.id), "goal": r.goal, "algorithm": r.algorithm, "status": r.status, "created_at": r.created_at.isoformat()} for r in runs]


@router.get("/{run_id}")
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(OptimizationRun).where(OptimizationRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"id": str(run.id), "goal": run.goal, "algorithm": run.algorithm, "status": run.status, "summary_metrics": run.summary_metrics}


@router.get("/{run_id}/assignments")
async def get_run_assignments(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full slot_assignments for this run — consumed by the 3D view."""
    raise HTTPException(status_code=501, detail="Implemented in Phase 5")


@router.post("/{run_id}/rollback")
async def rollback_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    """Revert slot state to the prior run's assignments."""
    raise HTTPException(status_code=501, detail="Implemented in Phase 5")


@router.get("/{run_id}/exceptions")
async def get_run_exceptions(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Implemented in Phase 5")


@router.get("/{run_id}/export.csv")
async def export_run_csv(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Implemented in Phase 5")


@router.get("/{run_id}/report")
async def get_run_report(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Implemented in Phase 5")
