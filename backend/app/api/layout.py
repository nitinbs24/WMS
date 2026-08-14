"""
Layout import router.
Admin uploads JSON/CSV → validation runs → apply commits to DB.
GET /layout returns the full warehouse structure for 3D scene seeding.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User

router = APIRouter(prefix="/layout", tags=["layout"])


@router.post("/import")
async def upload_layout(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Upload a JSON or CSV warehouse layout file. Returns import_id for polling."""
    # Phase 3 — layout_service.py will process file and persist LayoutImport row
    raise HTTPException(status_code=501, detail="Implemented in Phase 3")


@router.get("/imports/{import_id}")
async def get_import_status(
    import_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Check validation status of a layout import."""
    raise HTTPException(status_code=501, detail="Implemented in Phase 3")


@router.post("/imports/{import_id}/apply")
async def apply_import(
    import_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Commit a validated import. Upserts racks/aisles/slots preserving matched slot IDs."""
    raise HTTPException(status_code=501, detail="Implemented in Phase 3")


@router.get("")
async def get_layout(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return full warehouse structure — racks, aisles, slots. Seeds the 3D scene."""
    raise HTTPException(status_code=501, detail="Implemented in Phase 3")
