"""
Products router.
- GET  /api/v1/products         — list all products (any authenticated user)
- GET  /api/v1/products/{sku}   — get product by SKU
- POST /api/v1/products/seed    — seed from mock JSON (admin only)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.schemas.product import ProductOut
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await product_service.list_products(db)


@router.get("/{sku}", response_model=ProductOut)
async def get_product(
    sku: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await product_service.get_product_by_sku(db, sku)


@router.post("/seed", status_code=200)
async def seed_products(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    count = await product_service.seed_products(db)
    await db.commit()
    return {"seeded": count}
