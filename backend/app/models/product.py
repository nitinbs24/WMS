from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Product(Base):
    """Mirrors Odoo product.template. odoo_product_id nullable until Phase 2."""
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    sku: Mapped[str] = mapped_column(sa.Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    length: Mapped[float] = mapped_column(sa.Numeric, nullable=False)
    width: Mapped[float] = mapped_column(sa.Numeric, nullable=False)
    height: Mapped[float] = mapped_column(sa.Numeric, nullable=False)
    weight: Mapped[float] = mapped_column(sa.Numeric, nullable=False)
    category: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    abc_class: Mapped[str | None] = mapped_column(sa.Text, nullable=True)  # A | B | C
    odoo_product_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    pallet_items: Mapped[list[PalletItem]] = relationship("PalletItem", back_populates="product")


class Pallet(Base):
    __tablename__ = "pallets"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    computed_height: Mapped[float | None] = mapped_column(sa.Numeric, nullable=True)
    computed_weight: Mapped[float | None] = mapped_column(sa.Numeric, nullable=True)
    computed_volume: Mapped[float | None] = mapped_column(sa.Numeric, nullable=True)
    stability_status: Mapped[str | None] = mapped_column(sa.Text, nullable=True)  # stable | unstable
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )

    items: Mapped[list[PalletItem]] = relationship("PalletItem", back_populates="pallet")


class PalletItem(Base):
    """Individual product placement within a pallet (drives CoM calculation)."""
    __tablename__ = "pallet_items"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    pallet_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("pallets.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    x_pos: Mapped[float | None] = mapped_column(sa.Numeric, nullable=True)
    y_pos: Mapped[float | None] = mapped_column(sa.Numeric, nullable=True)
    z_pos: Mapped[float | None] = mapped_column(sa.Numeric, nullable=True)

    pallet: Mapped[Pallet] = relationship("Pallet", back_populates="items")
    product: Mapped[Product] = relationship("Product", back_populates="pallet_items")
