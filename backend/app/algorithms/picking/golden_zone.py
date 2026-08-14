"""
Ergonomic Golden Zone SKU→Slot Assignment
------------------------------------------
Picking Efficiency algorithm #1 (TRD §7, Algorithm Report §4.1).

Golden Zone principle: slots at waist-to-shoulder height (ergonomic
optimum) should host the highest-frequency SKUs. This minimises picker
fatigue and reduces pick time for fast-moving items.

Algorithm:
1. Rank SKUs by pick_frequency descending (most-picked first).
2. Rank slots by ergonomic_score descending.
   ergonomic_score = thresholds.ergonomic_factors[f"L{slot.level}"]
   (L2 = 1.00 is the golden zone; L1/L3/L4 decrease progressively)
3. Assign the Nth-ranked SKU to the Nth-ranked slot (greedy 1:1 match).
   Apply hard safety checks (weight_capacity on the slot).
4. Unassigned SKUs (no more eligible slots) → AlgorithmException.

Score = ergonomic_factor × normalised_frequency.
"""
from __future__ import annotations

import uuid

from app.algorithms.types import (
    AlgorithmException,
    Assignment,
    Pallet,
    PickHistory,
    SKU,
    Slot,
    SlotAssignmentResult,
    Thresholds,
)


def assign(
    skus: list[SKU],
    slots: list[Slot],
    pick_history: PickHistory,
    thresholds: Thresholds = None,
) -> SlotAssignmentResult:
    """
    Assign SKUs to slots using the Ergonomic Golden Zone strategy.
    """
    if thresholds is None:
        thresholds = Thresholds()

    if not skus:
        return SlotAssignmentResult(assignments=[], exceptions=[])

    # 1. Rank SKUs by frequency
    def sku_freq(sku: SKU) -> float:
        return pick_history.frequencies.get(sku.id, 0.0)

    ranked_skus = sorted(skus, key=sku_freq, reverse=True)
    max_freq = sku_freq(ranked_skus[0]) if ranked_skus else 1.0

    # 2. Rank slots by ergonomic score
    def ergo_score(slot: Slot) -> float:
        key = f"L{slot.level}"
        return thresholds.ergonomic_factors.get(key, 0.5)

    available = [s for s in slots if s.status == "empty"]
    ranked_slots = sorted(available, key=ergo_score, reverse=True)

    assignments: list[Assignment] = []
    exceptions: list[AlgorithmException] = []
    used_slots: set[uuid.UUID] = set()

    slot_iter = iter(ranked_slots)
    current_slot: Slot | None = next(slot_iter, None)

    for sku in ranked_skus:
        # Find next slot with sufficient weight capacity
        placed = False
        while current_slot is not None:
            if current_slot.id not in used_slots and current_slot.weight_capacity >= sku.weight:
                freq = sku_freq(sku)
                norm_freq = freq / max_freq if max_freq > 0 else 0.0
                score = round(ergo_score(current_slot) * norm_freq, 4)
                assignments.append(
                    Assignment(
                        pallet_id=None,
                        product_id=sku.id,
                        slot_id=current_slot.id,
                        score=score,
                    )
                )
                used_slots.add(current_slot.id)
                current_slot = next(slot_iter, None)
                placed = True
                break
            current_slot = next(slot_iter, None)

        if not placed:
            exceptions.append(
                AlgorithmException(
                    pallet_id=None,
                    product_id=sku.id,
                    reason_code="NO_CLEARANCE_MATCH",
                    reason_detail=f"No eligible ergonomic slot for SKU {sku.sku} (freq={sku_freq(sku):.1f})",
                )
            )

    return SlotAssignmentResult(assignments=assignments, exceptions=exceptions)
