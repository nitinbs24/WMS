from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    goal: Mapped[str] = mapped_column(sa.Text, nullable=False)       # space_efficiency | picking_efficiency
    algorithm: Mapped[str] = mapped_column(sa.Text, nullable=False)  # see domain enums in TRD §3
    scope: Mapped[str] = mapped_column(sa.Text, nullable=False)      # full | incremental
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # NULL = scheduled run
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="queued")
    # queued | running | completed | completed_with_exceptions | failed
    started_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    thresholds_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )


class SlotAssignment(Base):
    __tablename__ = "slot_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False
    )
    pallet_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("pallets.id", ondelete="SET NULL"), nullable=True
    )  # NULL for picking-efficiency runs (SKU-level, no pallet)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )  # populated for picking-efficiency runs
    slot_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("slots.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float | None] = mapped_column(sa.Numeric, nullable=True)
    is_override: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.false())
    overridden_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    overridden_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )


class RunException(Base):
    """Unplaced-item queue — items an algorithm could not safely place."""
    __tablename__ = "exceptions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False
    )
    pallet_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("pallets.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    reason_code: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # NO_CLEARANCE_MATCH | NO_WEIGHT_CAPACITY | COM_VIOLATION | AISLE_DENSITY_CAP
    reason_detail: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="open")
    # open | resolved
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )
