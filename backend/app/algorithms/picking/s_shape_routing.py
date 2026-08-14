"""
S-Shape Pick-Path Routing SKU→Slot Assignment
----------------------------------------------
Picking Efficiency algorithm #3 (TRD §7, Algorithm Report §4.3).

S-Shape principle: a picker traversing aisles in an alternating
(serpentine) pattern travels the minimum total distance when
high-frequency SKUs are placed at the entry/exit of each aisle.
SKUs placed at the far end of an aisle that are rarely picked waste
travel.

Algorithm:
1. Build an S-Shape traversal order over all slots:
   - Sort aisles by pos_y.
   - Within even-numbered aisles (0-indexed): traverse slots left-to-right
     (ascending pos_x), then ascending level.
   - Within odd-numbered aisles: traverse right-to-left (descending pos_x).
   - This produces a single ordered list representing the picker's path.
2. Rank SKUs descending by pick_frequency.
3. Assign the Nth-ranked SKU to the Nth slot in traversal order that:
   - Is empty.
   - Has sufficient weight_capacity.
4. Unassigned SKUs → AlgorithmException.

Score = 1.0 - (traversal_position / total_slots)
  (slots earlier on the path score higher, as the picker reaches them faster).
"""
from __future__ import annotations

import uuid

from app.algorithms.types import (
    AlgorithmException,
    Assignment,
    PickHistory,
    RackGrid,
    SKU,
    Slot,
    SlotAssignmentResult,
    Thresholds,
)


def assign(
    skus: list[SKU],
    rack_grid: RackGrid,
    thresholds: Thresholds = None,
) -> SlotAssignmentResult:
    """
    Assign SKUs to slots using S-Shape (serpentine) pick-path routing.
    """
    if thresholds is None:
        thresholds = Thresholds()
    if not skus:
        return SlotAssignmentResult(assignments=[], exceptions=[])

    # 1. Build S-Shape traversal order
    traversal = _build_s_shape_traversal(rack_grid)
    available = [s for s in traversal if s.status == "empty"]

    total = len(traversal)

    # 2. Rank SKUs by frequency
    ranked_skus = sorted(skus, key=lambda s: s.pick_frequency, reverse=True)

    assignments: list[Assignment] = []
    exceptions: list[AlgorithmException] = []
    used: set[uuid.UUID] = set()

    slot_iter = iter(enumerate(available))  # (traversal_pos, slot)

    for sku in ranked_skus:
        placed = False
        for pos, slot in slot_iter:
            if slot.id in used:
                continue
            if slot.weight_capacity >= sku.weight:
                score = round(1.0 - (pos / max(total, 1)), 4)
                assignments.append(
                    Assignment(
                        pallet_id=None,
                        product_id=sku.id,
                        slot_id=slot.id,
                        score=score,
                    )
                )
                used.add(slot.id)
                placed = True
                break

        if not placed:
            exceptions.append(
                AlgorithmException(
                    pallet_id=None,
                    product_id=sku.id,
                    reason_code="NO_CLEARANCE_MATCH",
                    reason_detail=f"S-Shape path exhausted — no eligible slot for SKU {sku.sku}",
                )
            )

    return SlotAssignmentResult(assignments=assignments, exceptions=exceptions)


def _build_s_shape_traversal(rack_grid: RackGrid) -> list[Slot]:
    """
    Build the S-Shape (serpentine) slot traversal order.
    Racks are sorted by aisle_pos; even-index racks go L→R, odd go R→L.
    Within a rack position, slots sorted by level ascending (bottom first).
    """
    # Sort racks by aisle position
    sorted_racks = sorted(rack_grid.racks, key=lambda r: (r[1], r[2]))  # (rack_id, aisle_pos, rack_pos)

    traversal: list[Slot] = []
    for rack_idx, (rack_id, aisle_pos, rack_pos) in enumerate(sorted_racks):
        slots = rack_grid.slots_by_rack.get(rack_id, [])
        # Sort by level ascending (bottom shelf first within a rack position)
        slots_sorted = sorted(slots, key=lambda s: (s.pos_x, s.pos_y, s.level))
        if rack_idx % 2 == 1:
            # Odd rack: traverse in reverse (right-to-left)
            slots_sorted = list(reversed(slots_sorted))
        traversal.extend(slots_sorted)

    return traversal
