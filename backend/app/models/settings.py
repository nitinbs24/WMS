from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ThresholdSettings(Base):
    """Versioned threshold configuration. Each PUT creates a new row (immutable history)."""
    __tablename__ = "threshold_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    heavy_weight_kg: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="600")
    medium_weight_kg: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="300")
    com_threshold: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0.55")
    blf_com_threshold: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0.60")
    aisle_a_density_cap: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0.35")
    ergonomic_factors: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default='{"L1": 0.90, "L2": 1.00, "L3": 0.70, "L4": 0.50}',
    )
    pick_lookback_days: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="90")
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )
