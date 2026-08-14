"""
Layout import service.

Handles the 3-step import lifecycle:
  1. upload()    → validate JSON/CSV, write LayoutImport row (status=pending→valid/invalid)
  2. get_import() → poll status
  3. apply()     → upsert Warehouse/Aisle/Rack/Slot rows, update status=applied

JSON schema expected (matches seed/warehouse_layout.json):
{
  "warehouses": [
    {
      "name": "Main Warehouse",
      "address": "...",
      "aisles": [
        {
          "aisle_label": "A",
          "pos_x": 0.0,
          "pos_y": 0.0,
          "direction": "N-S",
          "racks": [
            {
              "rack_number": 1,
              "pos_x": 0.0,
              "pos_y": 0.0,
              "levels": 4,
              "slots": [
                {
                  "level": 1,
                  "clearance_height": 2.0,
                  "weight_capacity": 1500.0,
                  "pos_x": 0.0,
                  "pos_y": 0.0,
                  "pos_z": 0.0,
                  "is_aisle_boundary": true
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.layout_import import LayoutImport
from app.models.warehouse import Aisle, Rack, Slot, Warehouse
from app.schemas.warehouse import LayoutImportApplyResult

STORAGE_DIR = Path("/data/layout-imports")


async def upload_layout(
    db: AsyncSession,
    file: UploadFile,
    uploaded_by: uuid.UUID,
) -> LayoutImport:
    """Read, validate structure, and persist LayoutImport row."""
    content = await file.read()

    # Parse
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        layout_import = LayoutImport(
            filename=file.filename or "upload",
            raw_content=content.decode(errors="replace"),
            status="invalid",
            error_detail=f"JSON parse error: {exc}",
            uploaded_by=uploaded_by,
        )
        db.add(layout_import)
        await db.flush()
        return layout_import

    # Basic structure validation
    error = _validate_structure(data)
    layout_import = LayoutImport(
        filename=file.filename or "upload",
        raw_content=content.decode(errors="replace"),
        status="invalid" if error else "valid",
        error_detail=error,
        row_count=_count_slots(data) if not error else None,
        uploaded_by=uploaded_by,
    )
    db.add(layout_import)
    await db.flush()
    return layout_import


def _validate_structure(data: Any) -> str | None:
    if not isinstance(data, dict):
        return "Root must be a JSON object"
    if "warehouses" not in data or not isinstance(data["warehouses"], list):
        return "Missing 'warehouses' array"
    for w in data["warehouses"]:
        if "name" not in w:
            return "Each warehouse must have a 'name'"
        for a in w.get("aisles", []):
            if "aisle_label" not in a:
                return "Each aisle must have an 'aisle_label'"
            for r in a.get("racks", []):
                if "rack_number" not in r:
                    return "Each rack must have a 'rack_number'"
    return None


def _count_slots(data: dict) -> int:
    count = 0
    for w in data.get("warehouses", []):
        for a in w.get("aisles", []):
            for r in a.get("racks", []):
                count += len(r.get("slots", []))
    return count


async def get_import(db: AsyncSession, import_id: uuid.UUID) -> LayoutImport:
    result = await db.execute(select(LayoutImport).where(LayoutImport.id == import_id))
    layout_import = result.scalar_one_or_none()
    if not layout_import:
        raise HTTPException(status_code=404, detail="Layout import not found")
    return layout_import


async def apply_import(
    db: AsyncSession,
    import_id: uuid.UUID,
) -> LayoutImportApplyResult:
    """Upsert all warehouse/aisle/rack/slot rows. Idempotent — safe to re-apply."""
    layout_import = await get_import(db, import_id)
    if layout_import.status == "invalid":
        raise HTTPException(status_code=422, detail="Cannot apply an invalid import")
    if layout_import.status == "applied":
        raise HTTPException(status_code=409, detail="Import already applied")

    data = json.loads(layout_import.raw_content)
    counters = {"warehouses": 0, "aisles": 0, "racks": 0, "slots": 0}

    for w_data in data.get("warehouses", []):
        warehouse = await _upsert_warehouse(db, w_data)
        counters["warehouses"] += 1

        for a_data in w_data.get("aisles", []):
            aisle = await _upsert_aisle(db, a_data, warehouse.id)
            counters["aisles"] += 1

            for r_data in a_data.get("racks", []):
                rack = await _upsert_rack(db, r_data, aisle.id)
                counters["racks"] += 1

                for s_data in r_data.get("slots", []):
                    await _upsert_slot(db, s_data, rack.id)
                    counters["slots"] += 1

    layout_import.status = "applied"
    await db.flush()

    return LayoutImportApplyResult(
        warehouses_upserted=counters["warehouses"],
        aisles_upserted=counters["aisles"],
        racks_upserted=counters["racks"],
        slots_upserted=counters["slots"],
    )


async def _upsert_warehouse(db: AsyncSession, data: dict) -> Warehouse:
    result = await db.execute(select(Warehouse).where(Warehouse.name == data["name"]))
    existing = result.scalar_one_or_none()
    if existing:
        existing.address = data.get("address")
        return existing
    w = Warehouse(name=data["name"], address=data.get("address"))
    db.add(w)
    await db.flush()
    return w


async def _upsert_aisle(db: AsyncSession, data: dict, warehouse_id: uuid.UUID) -> Aisle:
    result = await db.execute(
        select(Aisle).where(Aisle.warehouse_id == warehouse_id, Aisle.aisle_label == data["aisle_label"])
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.pos_x = data.get("pos_x", 0.0)
        existing.pos_y = data.get("pos_y", 0.0)
        existing.direction = data.get("direction", "N-S")
        return existing
    a = Aisle(
        warehouse_id=warehouse_id,
        aisle_label=data["aisle_label"],
        pos_x=data.get("pos_x", 0.0),
        pos_y=data.get("pos_y", 0.0),
        direction=data.get("direction", "N-S"),
    )
    db.add(a)
    await db.flush()
    return a


async def _upsert_rack(db: AsyncSession, data: dict, aisle_id: uuid.UUID) -> Rack:
    result = await db.execute(
        select(Rack).where(Rack.aisle_id == aisle_id, Rack.rack_number == data["rack_number"])
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.levels = data.get("levels", 4)
        existing.pos_x = data.get("pos_x", 0.0)
        existing.pos_y = data.get("pos_y", 0.0)
        return existing
    r = Rack(
        aisle_id=aisle_id,
        rack_number=data["rack_number"],
        pos_x=data.get("pos_x", 0.0),
        pos_y=data.get("pos_y", 0.0),
        levels=data.get("levels", 4),
    )
    db.add(r)
    await db.flush()
    return r


async def _upsert_slot(db: AsyncSession, data: dict, rack_id: uuid.UUID) -> Slot:
    result = await db.execute(
        select(Slot).where(Slot.rack_id == rack_id, Slot.level == data["level"])
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.clearance_height = data.get("clearance_height", 2.0)
        existing.weight_capacity = data.get("weight_capacity", 1500.0)
        existing.pos_x = data.get("pos_x", 0.0)
        existing.pos_y = data.get("pos_y", 0.0)
        existing.pos_z = data.get("pos_z", 0.0)
        existing.is_aisle_boundary = data.get("is_aisle_boundary", False)
        return existing
    s = Slot(
        rack_id=rack_id,
        level=data["level"],
        clearance_height=data.get("clearance_height", 2.0),
        weight_capacity=data.get("weight_capacity", 1500.0),
        pos_x=data.get("pos_x", 0.0),
        pos_y=data.get("pos_y", 0.0),
        pos_z=data.get("pos_z", 0.0),
        is_aisle_boundary=data.get("is_aisle_boundary", False),
    )
    db.add(s)
    await db.flush()
    return s


async def get_full_layout(db: AsyncSession) -> list[Warehouse]:
    """Return all warehouses with eagerly loaded aisles→racks→slots."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Warehouse).options(
            selectinload(Warehouse.aisles).selectinload(Aisle.racks).selectinload(Rack.slots)
        )
    )
    return list(result.scalars().unique().all())
