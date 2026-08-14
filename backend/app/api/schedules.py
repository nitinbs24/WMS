"""Schedules router — Admin CRUD for recurring optimization runs."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.schedule import Schedule
from app.models.user import User

router = APIRouter(prefix="/schedules", tags=["schedules"])


class CreateScheduleRequest(BaseModel):
    goal: str
    algorithm: str
    scope: str
    cron_expression: str


@router.get("")
async def list_schedules(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    result = await db.execute(select(Schedule))
    schedules = result.scalars().all()
    return [{"id": str(s.id), "goal": s.goal, "algorithm": s.algorithm, "scope": s.scope, "cron_expression": s.cron_expression, "is_active": s.is_active} for s in schedules]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_schedule(body: CreateScheduleRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    schedule = Schedule(
        goal=body.goal, algorithm=body.algorithm,
        scope=body.scope, cron_expression=body.cron_expression,
        created_by=current_user.id,
    )
    db.add(schedule)
    await db.flush()
    return {"id": str(schedule.id)}


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.delete(schedule)
