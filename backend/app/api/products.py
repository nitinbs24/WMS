"""Products router — product catalog and seed endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
async def list_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Product))
    products = result.scalars().all()
    return [
        {
            "id": str(p.id), "sku": p.sku, "name": p.name,
            "length": float(p.length), "width": float(p.width), "height": float(p.height),
            "weight": float(p.weight), "category": p.category, "abc_class": p.abc_class,
        }
        for p in products
    ]


@router.get("/{sku}")
async def get_product(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.sku == sku))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": str(product.id), "sku": product.sku, "name": product.name}


@router.post("/seed")
async def seed_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Dev-only: load the mock dataset from seed files into the database."""
    raise HTTPException(status_code=501, detail="Implemented in Phase 3")
