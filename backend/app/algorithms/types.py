"""
Shared data types for all algorithm modules.

All algorithm modules are pure functions — no DB sessions, no HTTP context.
They take these types as input and return SlotAssignmentResult as output.
Units: meters / kilograms throughout (TRD §15.3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict
import uuid


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Dims:
    """Physical dimensions in meters."""
    length: float
    width: float
    height: float

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass
class Item:
    """A single product unit to be placed."""
    id: uuid.UUID
    sku: str
    dims: Dims
    weight: float          # kg
    abc_class: str         # A | B | C
    category: str = ""
    quantity: int = 1


@dataclass
class Pallet:
    """A built pallet (output of Item→Pallet stage, input to Pallet→Slot stage)."""
    id: uuid.UUID
    items: list[tuple[Item, int]]   # (item, quantity)
    computed_height: float          # metres
    computed_weight: float          # kg
    computed_volume: float          # m³
    stability_status: str = "stable"  # stable | unstable
    item_positions: list[tuple[uuid.UUID, float, float, float]] = field(default_factory=list)
    # (product_id, x_pos, y_pos, z_pos) — for CoM audit


@dataclass(frozen=True)
class Slot:
    """A warehouse slot, as loaded from the DB for algorithm consumption."""
    id: uuid.UUID
    rack_id: uuid.UUID
    level: int              # 1 = ground level
    clearance_height: float # metres
    weight_capacity: float  # kg
    pos_x: float
    pos_y: float
    pos_z: float
    is_aisle_boundary: bool = False
    status: str = "empty"   # empty | occupied | reserved


@dataclass(frozen=True)
class SKU:
    """Simplified product view for picking-efficiency algorithms."""
    id: uuid.UUID
    sku: str
    abc_class: str
    pick_frequency: float  # picks per lookback window
    dims: Dims
    weight: float


@dataclass
class Thresholds:
    """Active threshold settings passed explicitly to every algorithm run."""
    heavy_weight_kg: float = 600.0
    medium_weight_kg: float = 300.0
    com_threshold: float = 0.55
    blf_com_threshold: float = 0.60
    aisle_a_density_cap: float = 0.35
    ergonomic_factors: dict[str, float] = field(
        default_factory=lambda: {"L1": 0.90, "L2": 1.00, "L3": 0.70, "L4": 0.50}
    )
    pick_lookback_days: int = 90


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

class Assignment(TypedDict):
    """A successful slot assignment produced by an algorithm."""
    pallet_id: uuid.UUID | None      # None for picking-efficiency (SKU-level)
    product_id: uuid.UUID | None     # Populated for picking-efficiency
    slot_id: uuid.UUID
    score: float


class AlgorithmException(TypedDict):
    """An item/pallet the algorithm could not safely place."""
    pallet_id: uuid.UUID | None
    product_id: uuid.UUID | None
    reason_code: str   # NO_CLEARANCE_MATCH | NO_WEIGHT_CAPACITY | COM_VIOLATION | AISLE_DENSITY_CAP
    reason_detail: str


class SlotAssignmentResult(TypedDict):
    """The contract every algorithm module must return."""
    assignments: list[Assignment]
    exceptions: list[AlgorithmException]


# ---------------------------------------------------------------------------
# Pick history types (input to picking-efficiency algorithms)
# ---------------------------------------------------------------------------

@dataclass
class PickHistory:
    """Aggregated pick events per SKU within the lookback window."""
    frequencies: dict[uuid.UUID, float]   # product_id → picks per window


@dataclass
class OrderLines:
    """Order co-occurrence data for Apriori Affinity Clustering."""
    # List of orders, each order is a list of product_ids
    orders: list[list[uuid.UUID]]


@dataclass
class RackGrid:
    """Spatial layout of racks and slots for S-Shape routing."""
    racks: list[tuple[uuid.UUID, float, float]]  # (rack_id, aisle_pos, rack_pos)
    slots_by_rack: dict[uuid.UUID, list[Slot]]   # rack_id → slots
