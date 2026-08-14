"""
Modified First-Fit Decreasing Height (FFDH) + Centre-of-Mass Validation
-----------------------------------------------------------------------
Item → Pallet stage for Space Efficiency runs.

Algorithm (TRD §7, Algorithm Report §3.1):
1. Sort items descending by height.
2. For each item, try fitting it into the current open layer of an existing
   pallet. A layer is a horizontal slice at a given z-height.
3. If the item fits dimensionally, simulate adding it and run the CoM check.
   If CoM is within threshold, accept. Otherwise try the next pallet.
4. If no existing pallet/layer can accept the item, open a new pallet.
5. When a pallet's total weight or pallet_dims are exceeded, close it and
   open a new one.

CoM check: the geometric centre of mass must remain within
  [threshold * half_length, threshold * half_width] of the pallet centre.
  threshold = thresholds.com_threshold (default 0.55).

Units: metres / kilograms throughout.
"""
from __future__ import annotations

import uuid
from copy import deepcopy

from app.algorithms.safety import SafetyViolation
from app.algorithms.types import Dims, Item, Pallet, Thresholds

# Standard EU pallet footprint (can be overridden via pallet_dims)
_DEFAULT_PALLET = Dims(length=1.2, width=0.8, height=2.0)
_PALLET_BASE_WEIGHT = 25.0   # kg tare weight of the pallet itself


def build_pallets(
    items: list[Item],
    pallet_dims: Dims = _DEFAULT_PALLET,
    thresholds: Thresholds = None,
) -> list[Pallet]:
    """
    Pack items onto pallets using FFDH + CoM validation.
    Returns a list of Pallet objects (may be empty if items is empty).
    """
    if thresholds is None:
        thresholds = Thresholds()
    if not items:
        return []

    # Expand items by quantity, sort descending by height (FFDH)
    expanded: list[Item] = []
    for item in items:
        for _ in range(item.quantity):
            expanded.append(item)
    expanded.sort(key=lambda i: i.dims.height, reverse=True)

    pallets: list[_PalletBuilder] = []

    for item in expanded:
        placed = False
        for pb in pallets:
            if pb.try_place(item, pallet_dims, thresholds):
                placed = True
                break
        if not placed:
            pb = _PalletBuilder(pallet_dims)
            pb.try_place(item, pallet_dims, thresholds)  # always fits on fresh pallet
            pallets.append(pb)

    return [pb.to_pallet() for pb in pallets]


class _Layer:
    """A horizontal packing layer within a pallet at a given z-offset."""

    def __init__(self, z_offset: float, layer_height: float, pallet_length: float, pallet_width: float) -> None:
        self.z_offset = z_offset
        self.layer_height = layer_height
        self.cursor_x: float = 0.0
        self.items: list[tuple[Item, float, float, float]] = []  # (item, x, y, z)
        self.pallet_length = pallet_length
        self.pallet_width = pallet_width

    def fits(self, item: Item) -> tuple[float, float] | None:
        """Return (x, y) placement position if item fits in this layer, else None."""
        if item.dims.height > self.layer_height:
            return None
        if self.cursor_x + item.dims.length > self.pallet_length:
            return None
        if item.dims.width > self.pallet_width:
            return None
        # Centre the item in the y-axis so the CoM stays balanced
        y_pos = (self.pallet_width - item.dims.width) / 2
        return (self.cursor_x, y_pos)

    def place(self, item: Item, x: float, y: float) -> None:
        self.items.append((item, x, y, self.z_offset))
        self.cursor_x += item.dims.length


class _PalletBuilder:
    """Accumulates items into a pallet, managing layers."""

    def __init__(self, pallet_dims: Dims) -> None:
        self.pallet_dims = pallet_dims
        self.layers: list[_Layer] = []
        self.total_weight: float = _PALLET_BASE_WEIGHT
        self.current_z: float = 0.0

    def try_place(self, item: Item, pallet_dims: Dims, thresholds: Thresholds) -> bool:
        """Try to place item. Returns True if placed, False if this pallet is full."""
        max_payload = pallet_dims.height * 1000  # rough upper bound in kg (no cap in this alg)
        if self.total_weight + item.weight > thresholds.heavy_weight_kg * 2:
            return False
        if self.current_z + item.dims.height > pallet_dims.height:
            return False

        # Try existing layers first (FFDH)
        for layer in reversed(self.layers):
            pos = layer.fits(item)
            if pos is not None:
                # CoM check before committing
                if self._com_ok(item, pos[0], pos[1], layer.z_offset, thresholds):
                    layer.place(item, pos[0], pos[1])
                    self.total_weight += item.weight
                    return True

        # Open a new layer
        if self.current_z + item.dims.height > pallet_dims.height:
            return False

        new_layer = _Layer(
            z_offset=self.current_z,
            layer_height=item.dims.height,
            pallet_length=pallet_dims.length,
            pallet_width=pallet_dims.width,
        )
        pos = new_layer.fits(item)
        if pos is None:
            return False  # item wider than pallet — can't place

        if self._com_ok(item, pos[0], pos[1], self.current_z, thresholds):
            new_layer.place(item, pos[0], pos[1])
            self.layers.append(new_layer)
            self.current_z += item.dims.height
            self.total_weight += item.weight
            return True

        return False

    def _com_ok(self, new_item: Item, nx: float, ny: float, nz: float, thresholds: Thresholds) -> bool:
        """Check that CoM stays within threshold fraction of pallet centre."""
        all_existing = []
        for layer in self.layers:
            for (item, x, y, z) in layer.items:
                all_existing.append((item.weight, x + item.dims.length / 2, y + item.dims.width / 2))

        # Always allow placement on an empty pallet (first item sets the baseline)
        if not all_existing:
            return True

        all_items = all_existing + [
            (new_item.weight, nx + new_item.dims.length / 2, ny + new_item.dims.width / 2)
        ]
        total_w = sum(w for w, *_ in all_items)
        if total_w == 0:
            return True
        cx = sum(w * x for w, x, y in all_items) / total_w
        cy = sum(w * y for w, x, y in all_items) / total_w

        half_l = self.pallet_dims.length / 2
        half_w = self.pallet_dims.width / 2
        t = thresholds.com_threshold
        return (abs(cx - half_l) <= t * half_l) and (abs(cy - half_w) <= t * half_w)

    def to_pallet(self) -> Pallet:
        items_list: list[tuple[Item, int]] = []
        positions: list[tuple[uuid.UUID, float, float, float]] = []
        item_counts: dict[uuid.UUID, int] = {}
        item_map: dict[uuid.UUID, Item] = {}

        for layer in self.layers:
            for (item, x, y, z) in layer.items:
                item_counts[item.id] = item_counts.get(item.id, 0) + 1
                item_map[item.id] = item
                positions.append((item.id, x, y, z))

        items_list = [(item_map[iid], cnt) for iid, cnt in item_counts.items()]
        height = self.current_z
        volume = self.pallet_dims.length * self.pallet_dims.width * height

        return Pallet(
            id=uuid.uuid4(),
            items=items_list,
            computed_height=height,
            computed_weight=self.total_weight,
            computed_volume=volume,
            stability_status="stable",
            item_positions=positions,
        )
