"""Safety constraint unit tests — must pass before any algorithm implementation."""
from __future__ import annotations

import uuid
import pytest

from app.algorithms.types import Dims, Item, Pallet, Slot, Thresholds
from app.algorithms.safety import (
    SafetyViolation,
    check_clearance_height,
    check_weight_capacity,
    check_weight_class_level,
    validate_placement,
)


def make_pallet(height: float, weight: float) -> Pallet:
    return Pallet(
        id=uuid.uuid4(),
        items=[],
        computed_height=height,
        computed_weight=weight,
        computed_volume=1.0,
    )


def make_slot(clearance: float, capacity: float, level: int = 1) -> Slot:
    return Slot(
        id=uuid.uuid4(), rack_id=uuid.uuid4(), level=level,
        clearance_height=clearance, weight_capacity=capacity,
        pos_x=0, pos_y=0, pos_z=0,
    )


THRESHOLDS = Thresholds()


class TestClearanceHeight:
    def test_pallet_fits(self):
        check_clearance_height(make_pallet(1.0, 100), make_slot(1.2, 1000))

    def test_exact_fit(self):
        check_clearance_height(make_pallet(1.2, 100), make_slot(1.2, 1000))

    def test_too_tall_raises(self):
        with pytest.raises(SafetyViolation) as exc_info:
            check_clearance_height(make_pallet(1.3, 100), make_slot(1.2, 1000))
        assert exc_info.value.reason_code == "NO_CLEARANCE_MATCH"


class TestWeightCapacity:
    def test_within_capacity(self):
        check_weight_capacity(make_pallet(1.0, 500), make_slot(1.5, 600))

    def test_exact_capacity(self):
        check_weight_capacity(make_pallet(1.0, 600), make_slot(1.5, 600))

    def test_over_capacity_raises(self):
        with pytest.raises(SafetyViolation) as exc_info:
            check_weight_capacity(make_pallet(1.0, 601), make_slot(1.5, 600))
        assert exc_info.value.reason_code == "NO_WEIGHT_CAPACITY"


class TestWeightClassLevel:
    def test_heavy_pallet_on_level_1_ok(self):
        check_weight_class_level(make_pallet(1.0, 700), make_slot(2.0, 1000, level=1), THRESHOLDS)

    def test_heavy_pallet_on_level_2_raises(self):
        with pytest.raises(SafetyViolation):
            check_weight_class_level(make_pallet(1.0, 700), make_slot(2.0, 1000, level=2), THRESHOLDS)

    def test_medium_pallet_on_level_2_ok(self):
        check_weight_class_level(make_pallet(1.0, 400), make_slot(2.0, 600, level=2), THRESHOLDS)

    def test_medium_pallet_on_level_3_raises(self):
        with pytest.raises(SafetyViolation):
            check_weight_class_level(make_pallet(1.0, 400), make_slot(2.0, 600, level=3), THRESHOLDS)

    def test_light_pallet_on_any_level_ok(self):
        for level in [1, 2, 3, 4]:
            check_weight_class_level(make_pallet(1.0, 100), make_slot(2.0, 200, level=level), THRESHOLDS)


class TestValidatePlacement:
    def test_valid_placement_passes(self):
        validate_placement(make_pallet(1.0, 200), make_slot(1.2, 500), THRESHOLDS)

    def test_invalid_clears_first_violation(self):
        """validate_placement raises on the first violation encountered."""
        with pytest.raises(SafetyViolation):
            validate_placement(make_pallet(1.5, 200), make_slot(1.2, 500), THRESHOLDS)
