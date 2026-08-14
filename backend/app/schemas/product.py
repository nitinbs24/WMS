"""Product and pallet response schemas."""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel


class ProductOut(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    description: str | None
    length: float
    width: float
    height: float
    weight: float
    category: str | None
    abc_class: str        # A | B | C

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    sku: str
    name: str
    description: str | None = None
    length: float
    width: float
    height: float
    weight: float
    category: str | None = None
    abc_class: str = "C"


class PalletItemOut(BaseModel):
    product_id: uuid.UUID
    quantity: int
    pos_x: float | None
    pos_y: float | None
    pos_z: float | None

    model_config = {"from_attributes": True}


class PalletOut(BaseModel):
    id: uuid.UUID
    computed_height: float
    computed_weight: float
    computed_volume: float
    stability_status: str
    items: list[PalletItemOut] = []

    model_config = {"from_attributes": True}
