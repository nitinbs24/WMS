"""Optimization run / assignment / exception schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


OptimizationGoal = Literal["space_efficiency", "picking_efficiency"]
SpaceAlgorithm = Literal["ffdh_com", "blf_stratified"]
PickingAlgorithm = Literal["golden_zone", "affinity_clustering", "s_shape_routing"]
RunScope = Literal["full", "incremental"]
RunStatus = Literal["queued", "running", "completed", "completed_with_exceptions", "failed"]


class RunCreate(BaseModel):
    goal: OptimizationGoal
    algorithm: str   # validated against goal in service layer
    scope: RunScope


class RunOut(BaseModel):
    id: uuid.UUID
    goal: str
    algorithm: str
    scope: str
    status: RunStatus
    summary_metrics: dict[str, Any] | None
    thresholds_snapshot: dict[str, Any]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    triggered_by: uuid.UUID | None

    model_config = {"from_attributes": True}


class AssignmentOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    pallet_id: uuid.UUID | None
    product_id: uuid.UUID | None
    slot_id: uuid.UUID
    score: float | None
    is_override: bool

    model_config = {"from_attributes": True}


class ExceptionOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    pallet_id: uuid.UUID | None
    product_id: uuid.UUID | None
    reason_code: str
    reason_detail: str | None
    status: str
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class RunReport(BaseModel):
    run: RunOut
    assignments_count: int
    exceptions_count: int
    fill_rate_pct: float | None
    avg_pick_distance_m: float | None
    summary_metrics: dict[str, Any] | None
