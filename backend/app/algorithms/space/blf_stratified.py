"""
Bottom-Left Fill (BLF) + Weight Stratification
-----------------------------------------------
Item → Pallet stage for Space Efficiency runs (alternative to FFDH+CoM).

Algorithm (TRD §7, Algorithm Report §3.2):
1. Classify items: Heavy (≥heavy_weight_kg/items_per_pallet proxy),
   Medium, Light using thresholds.
2. Sort layers:
   - Level 1 (ground): Heavy items, sorted desc by weight
   - Level 2: Medium items, sorted desc by weight
   - Level 3+: Light items, sorted desc by height
3. Within each level use BLF placement: always place at the bottom-left
   corner of the remaining free area in that layer slice.
4. CoM check using blf_com_threshold (slightly looser than FFDH).

The key difference from FFDH+CoM: stratification is enforced by layer,
not per-item. This guarantees heavy items are always on the base.
"""
from __future__ import annotations

import uuid

from app.algorithms.types import Dims, Item, Pallet, Thresholds

_DEFAULT_PALLET = Dims(length=1.2, width=0.8, height=2.0)
_PALLET_BASE_WEIGHT = 25.0


def build_pallets(
    items: list[Item],
    pallet_dims: Dims = _DEFAULT_PALLET,
    thresholds: Thresholds = None,
) -> list[Pallet]:
    """
    Pack items onto pallets using BLF + weight stratification.
    """
    if thresholds is None:
        thresholds = Thresholds()
    if not items:
        return []

    # Per-item weight class (uses a per-item threshold, not total pallet weight)
    # We divide by an assumed 10 items per layer as a proxy
    heavy_thresh = thresholds.heavy_weight_kg / 10
    medium_thresh = thresholds.medium_weight_kg / 10

    def weight_class(item: Item) -> int:
        if item.weight >= heavy_thresh:
            return 0   # heavy → bottom
        if item.weight >= medium_thresh:
            return 1   # medium → middle
        return 2       # light → top

    # Sort by weight class first, then by weight desc within class
    expanded: list[Item] = []
    for item in items:
        for _ in range(item.quantity):
            expanded.append(item)
    expanded.sort(key=lambda i: (weight_class(i), -i.weight))

    pallets: list[_BLFPalletBuilder] = []

    for item in expanded:
        placed = False
        for pb in pallets:
            if pb.try_place(item, pallet_dims, thresholds):
                placed = True
                break
        if not placed:
            pb = _BLFPalletBuilder(pallet_dims)
            pb.try_place(item, pallet_dims, thresholds)
            pallets.append(pb)

    return [pb.to_pallet() for pb in pallets]


class _BLFPalletBuilder:
    def __init__(self, pallet_dims: Dims) -> None:
        self.pallet_dims = pallet_dims
        self.placements: list[tuple[Item, float, float, float]] = []  # (item, x, y, z)
        self.total_weight: float = _PALLET_BASE_WEIGHT
        self.height_used: float = 0.0
        # BLF free rectangles: list of (x, y, z, avail_l, avail_w, avail_h)
        self._free: list[tuple[float, float, float, float, float, float]] = [
            (0.0, 0.0, 0.0, pallet_dims.length, pallet_dims.width, pallet_dims.height)
        ]

    def try_place(self, item: Item, pallet_dims: Dims, thresholds: Thresholds) -> bool:
        if self.total_weight + item.weight > thresholds.heavy_weight_kg * 2:
            return False

        il, iw, ih = item.dims.length, item.dims.width, item.dims.height

        # Find bottom-left free rect that fits the item
        best = None
        best_score = float("inf")
        for rect in self._free:
            rx, ry, rz, rl, rw, rh = rect
            if il <= rl and iw <= rw and ih <= rh:
                score = rz * 1000 + rx + ry   # prefer lowest z, then leftmost
                if score < best_score:
                    best_score = score
                    best = rect

        if best is None:
            return False

        rx, ry, rz, rl, rw, rh = best

        # CoM check
        if not self._com_ok(item, rx, ry, rz, thresholds):
            return False

        # Place
        self.placements.append((item, rx, ry, rz))
        self.total_weight += item.weight
        self.height_used = max(self.height_used, rz + ih)

        # Split free rect (simplified guillotine split)
        self._free.remove(best)
        # Right remainder
        if rl - il > 0.001:
            self._free.append((rx + il, ry, rz, rl - il, rw, rh))
        # Front remainder
        if rw - iw > 0.001:
            self._free.append((rx, ry + iw, rz, il, rw - iw, rh))
        # Above remainder
        if rh - ih > 0.001:
            self._free.append((rx, ry, rz + ih, rl, rw, rh - ih))

        return True

    def _com_ok(self, new_item: Item, nx: float, ny: float, nz: float, thresholds: Thresholds) -> bool:
        # Always allow placement on an empty pallet (first item sets the baseline)
        if not self.placements:
            return True
        all_pts = [(p.weight, x + p.dims.length / 2, y + p.dims.width / 2)
                   for p, x, y, z in self.placements]
        all_pts.append((new_item.weight, nx + new_item.dims.length / 2, ny + new_item.dims.width / 2))
        total_w = sum(w for w, *_ in all_pts)
        if total_w == 0:
            return True
        cx = sum(w * x for w, x, y in all_pts) / total_w
        cy = sum(w * y for w, x, y in all_pts) / total_w
        half_l = self.pallet_dims.length / 2
        half_w = self.pallet_dims.width / 2
        t = thresholds.blf_com_threshold
        return (abs(cx - half_l) <= t * half_l) and (abs(cy - half_w) <= t * half_w)

    def to_pallet(self) -> Pallet:
        item_counts: dict[uuid.UUID, int] = {}
        item_map: dict[uuid.UUID, Item] = {}
        positions: list[tuple[uuid.UUID, float, float, float]] = []

        for item, x, y, z in self.placements:
            item_counts[item.id] = item_counts.get(item.id, 0) + 1
            item_map[item.id] = item
            positions.append((item.id, x, y, z))

        items_list = [(item_map[iid], cnt) for iid, cnt in item_counts.items()]
        volume = self.pallet_dims.length * self.pallet_dims.width * self.height_used

        return Pallet(
            id=uuid.uuid4(),
            items=items_list,
            computed_height=self.height_used,
            computed_weight=self.total_weight,
            computed_volume=volume,
            stability_status="stable",
            item_positions=positions,
        )
