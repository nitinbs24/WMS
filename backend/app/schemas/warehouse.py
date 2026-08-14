"""Warehouse / layout response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class SlotOut(BaseModel):
    id: uuid.UUID
    rack_id: uuid.UUID
    level: int
    clearance_height: float
    weight_capacity: float
    pos_x: float
    pos_y: float
    pos_z: float
    is_aisle_boundary: bool
    status: str

    model_config = {"from_attributes": True}


class RackOut(BaseModel):
    id: uuid.UUID
    aisle_id: uuid.UUID
    rack_number: int
    pos_x: float
    pos_y: float
    levels: int
    slots: list[SlotOut] = []

    model_config = {"from_attributes": True}


class AisleOut(BaseModel):
    id: uuid.UUID
    warehouse_id: uuid.UUID
    aisle_label: str
    pos_x: float
    pos_y: float
    direction: str
    racks: list[RackOut] = []

    model_config = {"from_attributes": True}


class WarehouseOut(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    aisles: list[AisleOut] = []

    model_config = {"from_attributes": True}


class LayoutImportOut(BaseModel):
    id: uuid.UUID
    filename: str
    status: str          # pending | valid | invalid | applied
    error_detail: str | None
    row_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LayoutImportApplyResult(BaseModel):
    warehouses_upserted: int
    aisles_upserted: int
    racks_upserted: int
    slots_upserted: int
