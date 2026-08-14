"""
Layout router.
- POST /api/v1/layout/import            — upload JSON layout file (admin only)
- GET  /api/v1/layout/import/{id}       — poll import status
- POST /api/v1/layout/import/{id}/apply — apply import to DB (admin only)
- GET  /api/v1/layout                   — get full warehouse tree (all roles)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.schemas.warehouse import LayoutImportOut, LayoutImportApplyResult, WarehouseOut
from app.services import layout_service

router = APIRouter(prefix="/layout", tags=["layout"])


@router.post("/import", response_model=LayoutImportOut, status_code=201)
async def upload_layout(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    layout_import = await layout_service.upload_layout(db, file, current_user.id)
    await db.commit()
    return layout_import


@router.get("/import/{import_id}", response_model=LayoutImportOut)
async def get_import_status(
    import_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await layout_service.get_import(db, import_id)


@router.post("/import/{import_id}/apply", response_model=LayoutImportApplyResult)
async def apply_import(
    import_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    result = await layout_service.apply_import(db, import_id)
    await db.commit()
    return result


@router.get("", response_model=list[WarehouseOut])
async def get_layout(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await layout_service.get_full_layout(db)
