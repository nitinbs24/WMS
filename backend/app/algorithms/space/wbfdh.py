"""
Weighted Best-Fit Decreasing Height (W-BFDH)
(Space Efficiency — Pallet → Slot stage, ALWAYS runs for space efficiency runs)

Algorithm: Sort pallets by height descending. For each pallet, find the slot
that gives the best fit (minimum wasted height) while satisfying all safety
constraints (clearance, weight capacity, weight-class level restrictions).

Full implementation in Phase 4 — pseudocode from Algorithm Implementation Report §X.
"""
from __future__ import annotations

from app.algorithms.types import Pallet, Slot, SlotAssignmentResult, Thresholds


def assign(
    pallets: list[Pallet],
    slots: list[Slot],
    thresholds: Thresholds,
) -> SlotAssignmentResult:
    """
    Assign pallets to warehouse slots using W-BFDH.

    Args:
        pallets:    Built pallets (output of FFDH or BLF stage).
        slots:      All currently empty warehouse slots.
        thresholds: Active safety thresholds.

    Returns:
        SlotAssignmentResult with assignments list and exceptions list.
        Every pallet that cannot be placed appears in exceptions with reason.
    """
    raise NotImplementedError("Phase 4 — implement from Algorithm Implementation Report")
