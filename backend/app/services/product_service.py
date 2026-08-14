"""
Product service — list, get by SKU, seed from mock data.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

SEED_FILE = Path(__file__).parent.parent.parent / "seed" / "products.json"


async def list_products(db: AsyncSession) -> list[Product]:
    result = await db.execute(select(Product).order_by(Product.sku))
    return list(result.scalars().all())


async def get_product_by_sku(db: AsyncSession, sku: str) -> Product:
    result = await db.execute(select(Product).where(Product.sku == sku))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{sku}' not found")
    return product


async def seed_products(db: AsyncSession) -> int:
    """
    Load products.json and upsert into the database.
    Returns the number of rows upserted.
    """
    if not SEED_FILE.exists():
        raise HTTPException(status_code=500, detail="Seed file not found — run seed generator first")

    with SEED_FILE.open() as f:
        records = json.load(f)

    if not records:
        return 0

    stmt = (
        insert(Product)
        .values(records)
        .on_conflict_do_update(
            index_elements=["sku"],
            set_={
                "name": insert(Product).excluded.name,
                "length": insert(Product).excluded.length,
                "width": insert(Product).excluded.width,
                "height": insert(Product).excluded.height,
                "weight": insert(Product).excluded.weight,
                "abc_class": insert(Product).excluded.abc_class,
                "category": insert(Product).excluded.category,
            },
        )
    )
    await db.execute(stmt)
    await db.flush()
    return len(records)
