"""
Shared safety constraint validators used by all algorithm modules.

Every hard safety rule from the algorithm report is enforced here,
regardless of algorithm choice. These validators are called by each
algorithm before accepting any placement.
"""
from __future__ import annotations

from app.algorithms.types import Pallet, Slot, Thresholds


class SafetyViolation(Exception):
    """Raised when a hard safety constraint would be violated."""
    def __init__(self, reason_code: str, detail: str):
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def check_clearance_height(pallet: Pallet, slot: Slot) -> None:
    """Pallet height must not exceed slot clearance."""
    if pallet.computed_height > slot.clearance_height:
        raise SafetyViolation(
            "NO_CLEARANCE_MATCH",
            f"Pallet height {pallet.computed_height:.3f}m exceeds slot clearance {slot.clearance_height:.3f}m",
        )


def check_weight_capacity(pallet: Pallet, slot: Slot) -> None:
    """Pallet weight must not exceed slot weight capacity."""
    if pallet.computed_weight > slot.weight_capacity:
        raise SafetyViolation(
            "NO_WEIGHT_CAPACITY",
            f"Pallet weight {pallet.computed_weight:.1f}kg exceeds slot capacity {slot.weight_capacity:.1f}kg",
        )


def check_weight_class_level(pallet: Pallet, slot: Slot, thresholds: Thresholds) -> None:
    """
    Heavy items must be on lower levels.
    Weight classification per TRD §4 (threshold_settings defaults):
      heavy  > heavy_weight_kg  → level 1 only
      medium > medium_weight_kg → levels 1–2
      light  ≤ medium_weight_kg → any level
    """
    w = pallet.computed_weight
    if w > thresholds.heavy_weight_kg and slot.level > 1:
        raise SafetyViolation(
            "NO_WEIGHT_CAPACITY",
            f"Heavy pallet ({w:.0f}kg > {thresholds.heavy_weight_kg:.0f}kg) must be on level 1, "
            f"but target slot is level {slot.level}",
        )
    if w > thresholds.medium_weight_kg and slot.level > 2:
        raise SafetyViolation(
            "NO_WEIGHT_CAPACITY",
            f"Medium pallet ({w:.0f}kg > {thresholds.medium_weight_kg:.0f}kg) must be on level ≤2, "
            f"but target slot is level {slot.level}",
        )


def check_com_stability(pallet: Pallet, thresholds: Thresholds, use_blf: bool = False) -> None:
    """
    Centre-of-Mass stability check.
    Computes horizontal CoM displacement ratio; must be within threshold.
    Uses blf_com_threshold when use_blf=True (BLF+Stratification algorithm).
    """
    if not pallet.item_positions:
        return  # no position data → skip (pallet not yet built)

    threshold = thresholds.blf_com_threshold if use_blf else thresholds.com_threshold

    total_weight = pallet.computed_weight
    if total_weight == 0:
        return

    # Simple CoM: weighted average of item x/z positions
    # Full pallet base assumed to be 1.2m × 1.0m centred at (0.6, 0.5)
    base_cx, base_cz = 0.6, 0.5
    cx = sum(x * 1.0 for _, x, _, _ in pallet.item_positions) / len(pallet.item_positions)
    cz = sum(z * 1.0 for _, _, _, z in pallet.item_positions) / len(pallet.item_positions)

    displacement = ((cx - base_cx) ** 2 + (cz - base_cz) ** 2) ** 0.5
    max_disp = min(base_cx, base_cz)
    ratio = displacement / max_disp if max_disp > 0 else 0

    if ratio > threshold:
        raise SafetyViolation(
            "COM_VIOLATION",
            f"CoM displacement ratio {ratio:.3f} exceeds threshold {threshold:.2f}",
        )


def check_aisle_a_density(
    slot: Slot,
    aisle_a_count: int,
    total_aisle_slots: int,
    thresholds: Thresholds,
) -> None:
    """
    Prevent over-concentration of A-class items in one aisle (congestion risk).
    After placing this item, A-class density must not exceed aisle_a_density_cap.
    """
    new_density = (aisle_a_count + 1) / max(total_aisle_slots, 1)
    if new_density > thresholds.aisle_a_density_cap:
        raise SafetyViolation(
            "AISLE_DENSITY_CAP",
            f"Placing A-class item would push aisle density to {new_density:.2%}, "
            f"exceeding cap {thresholds.aisle_a_density_cap:.2%}",
        )


def validate_placement(
    pallet: Pallet,
    slot: Slot,
    thresholds: Thresholds,
    aisle_a_count: int = 0,
    total_aisle_slots: int = 1,
    use_blf_com: bool = False,
) -> None:
    """
    Run all hard safety checks in order. Raises SafetyViolation on the first failure.
    Call this before accepting any placement — algorithm-produced or manual override.
    """
    check_clearance_height(pallet, slot)
    check_weight_capacity(pallet, slot)
    check_weight_class_level(pallet, slot, thresholds)
    check_com_stability(pallet, thresholds, use_blf=use_blf_com)
