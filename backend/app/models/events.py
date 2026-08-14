from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PickEvent(Base):
    """Mirrors Odoo stock.move. Drives pick-frequency algorithms."""
    __tablename__ = "pick_events"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    odoo_move_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)


class OrderLine(Base):
    """Mirrors Odoo sale.order.line. Drives Apriori Affinity Clustering."""
    __tablename__ = "order_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    order_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    odoo_order_line_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
