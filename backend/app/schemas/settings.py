"""Threshold settings schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ThresholdSettingsOut(BaseModel):
    id: uuid.UUID
    version: int
    heavy_weight_kg: float
    medium_weight_kg: float
    com_threshold: float
    blf_com_threshold: float
    aisle_a_density_cap: float
    ergonomic_factors: dict[str, Any]
    pick_lookback_days: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ThresholdSettingsUpdate(BaseModel):
    heavy_weight_kg: float = Field(default=600.0, gt=0)
    medium_weight_kg: float = Field(default=300.0, gt=0)
    com_threshold: float = Field(default=0.55, gt=0, le=1)
    blf_com_threshold: float = Field(default=0.60, gt=0, le=1)
    aisle_a_density_cap: float = Field(default=0.35, gt=0, le=1)
    ergonomic_factors: dict[str, float] = Field(
        default={"L1": 0.90, "L2": 1.00, "L3": 0.70, "L4": 0.50}
    )
    pick_lookback_days: int = Field(default=90, gt=0)
