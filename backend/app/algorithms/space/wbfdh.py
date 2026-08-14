"""
Weight-Based Best-Fit Decreasing Height (W-BFDH)
-------------------------------------------------
Pallet → Slot assignment layer for ALL Space Efficiency runs.

This always runs after whichever Item→Pallet builder ran (FFDH or BLF).

Algorithm (TRD §7, Algorithm Report §3.3):
1. Sort pallets descending by computed_weight (heaviest first).
2. For each pallet, find the "best fit" slot:
   - Slot must be EMPTY
   - Slot clearance_height ≥ pallet.computed_height
   - Slot weight_capacity ≥ pallet.computed_weight
   - Weight class rule: heavy pallets only on level 1,
                        medium on levels 1-2,
                        light on any level.
   - Aisle A density cap: no more than aisle_a_density_cap fraction
     of aisle-A slots may be occupied by A-class pallets.
   - Best fit = slot with the smallest (clearance_height - pallet_height)
     slack (minimise wasted vertical space).
3. If no slot fits, record as AlgorithmException with reason_code.

Score = 1.0 - (clearance_slack / max_clearance) — higher is tighter fit.
"""
from __future__ import annotations

import uuid

from app.algorithms.safety import SafetyViolation, validate_placement
from app.algorithms.types import (
    AlgorithmException,
    Assignment,
    Pallet,
    Slot,
    SlotAssignmentResult,
    Thresholds,
)


def assign(
    pallets: list[Pallet],
    slots: list[Slot],
    thresholds: Thresholds = None,
) -> SlotAssignmentResult:
    """
    Assign pallets to slots using W-BFDH.
    Returns SlotAssignmentResult with assignments and exceptions.
    """
    if thresholds is None:
        thresholds = Thresholds()

    # Sort heaviest first
    sorted_pallets = sorted(pallets, key=lambda p: p.computed_weight, reverse=True)

    available_slots: list[Slot] = [s for s in slots if s.status == "empty"]
    assignments: list[Assignment] = []
    exceptions: list[AlgorithmException] = []

    # Track aisle-A occupancy for density cap
    # A slot is "aisle-A" if its rack's aisle is A; we approximate via is_aisle_boundary
    aisle_a_total = sum(1 for s in available_slots if s.is_aisle_boundary)
    aisle_a_used = 0

    occupied: set[uuid.UUID] = set()

    max_clearance = max((s.clearance_height for s in available_slots), default=1.0)

    for pallet in sorted_pallets:
        best_slot: Slot | None = None
        best_slack = float("inf")
        best_violation: str | None = None

        for slot in available_slots:
            if slot.id in occupied:
                continue

            # Run hard safety checks
            try:
                validate_placement(pallet, slot, thresholds)
            except SafetyViolation as exc:
                best_violation = exc.reason_code
                continue

            # Aisle-A density cap
            if slot.is_aisle_boundary and aisle_a_total > 0:
                if (aisle_a_used + 1) / aisle_a_total > thresholds.aisle_a_density_cap:
                    best_violation = best_violation or "AISLE_DENSITY_CAP"
                    continue

            # Best-fit: smallest height slack
            slack = slot.clearance_height - pallet.computed_height
            if slack < best_slack:
                best_slack = slack
                best_slot = slot

        if best_slot is None:
            reason = best_violation or "NO_CLEARANCE_MATCH"
            exceptions.append(
                AlgorithmException(
                    pallet_id=pallet.id,
                    product_id=None,
                    reason_code=reason,
                    reason_detail=f"No eligible slot for pallet {pallet.id} (weight={pallet.computed_weight:.1f}kg, height={pallet.computed_height:.2f}m)",
                )
            )
            continue

        score = 1.0 - (best_slack / max_clearance) if max_clearance > 0 else 1.0
        assignments.append(
            Assignment(
                pallet_id=pallet.id,
                product_id=None,
                slot_id=best_slot.id,
                score=round(score, 4),
            )
        )
        occupied.add(best_slot.id)
        if best_slot.is_aisle_boundary:
            aisle_a_used += 1

    return SlotAssignmentResult(assignments=assignments, exceptions=exceptions)
