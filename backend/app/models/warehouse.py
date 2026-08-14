from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)
    address: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )

    aisles: Mapped[list[Aisle]] = relationship("Aisle", back_populates="warehouse", lazy="select")


class Aisle(Base):
    __tablename__ = "aisles"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    aisle_label: Mapped[str] = mapped_column(sa.Text, nullable=False)    # "A", "B", …
    pos_x: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0")
    pos_y: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0")
    direction: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="N-S")
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )

    warehouse: Mapped[Warehouse] = relationship("Warehouse", back_populates="aisles")
    racks: Mapped[list[Rack]] = relationship("Rack", back_populates="aisle", lazy="select")

    __table_args__ = (sa.UniqueConstraint("warehouse_id", "aisle_label", name="uq_aisle_label_per_warehouse"),)


class Rack(Base):
    __tablename__ = "racks"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    aisle_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("aisles.id", ondelete="CASCADE"), nullable=False
    )
    rack_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    pos_x: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0")
    pos_y: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0")
    levels: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="4")
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )

    aisle: Mapped[Aisle] = relationship("Aisle", back_populates="racks")
    slots: Mapped[list[Slot]] = relationship("Slot", back_populates="rack", lazy="select")

    __table_args__ = (sa.UniqueConstraint("aisle_id", "rack_number", name="uq_rack_number_per_aisle"),)


class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    rack_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("racks.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    clearance_height: Mapped[float] = mapped_column(sa.Numeric, nullable=False)
    weight_capacity: Mapped[float] = mapped_column(sa.Numeric, nullable=False)
    pos_x: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0")
    pos_y: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0")
    pos_z: Mapped[float] = mapped_column(sa.Numeric, nullable=False, server_default="0")
    is_aisle_boundary: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.false())
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="empty")
    current_pallet_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("pallets.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    rack: Mapped[Rack] = relationship("Rack", back_populates="slots")

    __table_args__ = (sa.UniqueConstraint("rack_id", "level", name="uq_slots_rack_level"),)
