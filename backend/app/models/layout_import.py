from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LayoutImport(Base):
    __tablename__ = "layout_imports"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str] = mapped_column(sa.Text, nullable=False)
    raw_content: Mapped[str | None] = mapped_column(sa.Text, nullable=True)   # stored for apply step
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="pending")
    # pending | valid | invalid | applied
    error_detail: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    row_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )
