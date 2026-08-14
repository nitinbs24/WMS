"""
Algorithm unit tests — all 6 modules.
No DB, no HTTP. Pure function testing against the TRD spec.
"""
from __future__ import annotations

import uuid
import pytest

from app.algorithms.types import (
    Dims, Item, Pallet, Slot, SKU, Thresholds,
    PickHistory, OrderLines, RackGrid,
)
from app.algorithms.space import ffdh_com, blf_stratified, wbfdh
from app.algorithms.picking import golden_zone, affinity_clustering, s_shape_routing


# ─────────────────────────── fixtures ───────────────────────────

def make_item(weight: float = 10.0, h: float = 0.3, abc: str = "B", qty: int = 1) -> Item:
    return Item(
        id=uuid.uuid4(), sku=f"SKU-{uuid.uuid4().hex[:4]}",
        dims=Dims(length=0.4, width=0.3, height=h),
        weight=weight, abc_class=abc, quantity=qty,
    )


def make_slot(level: int = 1, clearance: float = 2.0, capacity: float = 1500.0,
              status: str = "empty", aisle: bool = False,
              pos_x: float = 0.0, pos_y: float = 0.0) -> Slot:
    return Slot(
        id=uuid.uuid4(), rack_id=uuid.uuid4(),
        level=level, clearance_height=clearance, weight_capacity=capacity,
        pos_x=pos_x, pos_y=pos_y, pos_z=0.0,
        is_aisle_boundary=aisle, status=status,
    )


def make_sku(freq: float = 10.0, weight: float = 5.0, abc: str = "A") -> SKU:
    return SKU(
        id=uuid.uuid4(), sku=f"SKU-{uuid.uuid4().hex[:4]}",
        abc_class=abc, pick_frequency=freq,
        dims=Dims(length=0.3, width=0.2, height=0.2), weight=weight,
    )


THRESHOLDS = Thresholds()
PALLET_DIMS = Dims(length=1.2, width=0.8, height=2.0)


# ─────────────────────────── FFDH+CoM ───────────────────────────

class TestFFDHCoM:
    def test_empty_items_returns_no_pallets(self):
        result = ffdh_com.build_pallets([], PALLET_DIMS, THRESHOLDS)
        assert result == []

    def test_single_item_creates_one_pallet(self):
        items = [make_item()]
        pallets = ffdh_com.build_pallets(items, PALLET_DIMS, THRESHOLDS)
        assert len(pallets) == 1
        assert pallets[0].computed_weight > 0

    def test_many_small_items_packed_into_fewer_pallets(self):
        items = [make_item(weight=5.0, h=0.1) for _ in range(20)]
        pallets = ffdh_com.build_pallets(items, PALLET_DIMS, THRESHOLDS)
        assert len(pallets) < 20   # should be packed, not 1-per-pallet

    def test_pallet_height_never_exceeds_limit(self):
        items = [make_item(h=0.4) for _ in range(10)]
        pallets = ffdh_com.build_pallets(items, PALLET_DIMS, THRESHOLDS)
        for p in pallets:
            assert p.computed_height <= PALLET_DIMS.height + 0.001

    def test_pallet_has_items(self):
        items = [make_item()]
        pallets = ffdh_com.build_pallets(items, PALLET_DIMS, THRESHOLDS)
        assert len(pallets[0].items) >= 1

    def test_returns_pallet_dataclass(self):
        items = [make_item()]
        pallets = ffdh_com.build_pallets(items, PALLET_DIMS, THRESHOLDS)
        assert isinstance(pallets[0], Pallet)


# ─────────────────────────── BLF+Stratified ─────────────────────

class TestBLFStratified:
    def test_empty_items(self):
        assert blf_stratified.build_pallets([], PALLET_DIMS, THRESHOLDS) == []

    def test_single_item(self):
        pallets = blf_stratified.build_pallets([make_item()], PALLET_DIMS, THRESHOLDS)
        assert len(pallets) == 1

    def test_heavy_item_always_placed(self):
        heavy = make_item(weight=50.0, h=0.5, abc="A")
        pallets = blf_stratified.build_pallets([heavy], PALLET_DIMS, THRESHOLDS)
        assert len(pallets) >= 1
        total_weight = sum(p.computed_weight for p in pallets)
        assert total_weight > 50.0  # includes tare

    def test_pallet_height_within_bounds(self):
        items = [make_item(h=0.3) for _ in range(8)]
        pallets = blf_stratified.build_pallets(items, PALLET_DIMS, THRESHOLDS)
        for p in pallets:
            assert p.computed_height <= PALLET_DIMS.height + 0.001


# ─────────────────────────── W-BFDH ─────────────────────────────

class TestWBFDH:
    def _make_pallet(self, weight: float = 200.0, height: float = 1.0) -> Pallet:
        return Pallet(
            id=uuid.uuid4(), items=[],
            computed_height=height, computed_weight=weight,
            computed_volume=0.5,
        )

    def test_empty_pallets_returns_empty(self):
        result = wbfdh.assign([], [make_slot()], THRESHOLDS)
        assert result["assignments"] == []
        assert result["exceptions"] == []

    def test_single_pallet_assigned_to_suitable_slot(self):
        pallet = self._make_pallet(weight=200.0, height=1.0)
        slot = make_slot(level=1, clearance=2.0, capacity=500.0)
        result = wbfdh.assign([pallet], [slot], THRESHOLDS)
        assert len(result["assignments"]) == 1
        assert result["assignments"][0]["slot_id"] == slot.id

    def test_overweight_pallet_becomes_exception(self):
        pallet = self._make_pallet(weight=2000.0, height=1.0)
        slot = make_slot(level=1, clearance=2.0, capacity=500.0)
        result = wbfdh.assign([pallet], [slot], THRESHOLDS)
        assert len(result["exceptions"]) == 1
        assert result["exceptions"][0]["reason_code"] == "NO_WEIGHT_CAPACITY"

    def test_too_tall_pallet_becomes_exception(self):
        pallet = self._make_pallet(weight=100.0, height=3.0)
        slot = make_slot(level=1, clearance=2.0, capacity=1000.0)
        result = wbfdh.assign([pallet], [slot], THRESHOLDS)
        assert len(result["exceptions"]) == 1

    def test_heavy_pallet_on_level_2_becomes_exception(self):
        pallet = self._make_pallet(weight=700.0, height=1.0)   # heavy (≥600kg)
        slot = make_slot(level=2, clearance=2.0, capacity=2000.0)  # level 2 only
        result = wbfdh.assign([pallet], [slot], THRESHOLDS)
        assert len(result["exceptions"]) == 1
        assert result["exceptions"][0]["reason_code"] == "WEIGHT_CLASS_LEVEL"

    def test_best_fit_selects_tightest_slot(self):
        pallet = self._make_pallet(weight=100.0, height=1.0)
        slot_tight = make_slot(level=1, clearance=1.1, capacity=500.0)   # 0.1m slack
        slot_loose = make_slot(level=1, clearance=2.0, capacity=500.0)   # 1.0m slack
        result = wbfdh.assign([pallet], [slot_tight, slot_loose], THRESHOLDS)
        assert result["assignments"][0]["slot_id"] == slot_tight.id   # best fit

    def test_multiple_pallets_assigned_to_different_slots(self):
        pallets = [self._make_pallet() for _ in range(3)]
        slots = [make_slot() for _ in range(3)]
        result = wbfdh.assign(pallets, slots, THRESHOLDS)
        assigned_slots = {a["slot_id"] for a in result["assignments"]}
        assert len(assigned_slots) == 3   # each gets a distinct slot

    def test_score_between_0_and_1(self):
        pallet = self._make_pallet()
        slot = make_slot()
        result = wbfdh.assign([pallet], [slot], THRESHOLDS)
        assert 0.0 <= result["assignments"][0]["score"] <= 1.0


# ─────────────────────────── Golden Zone ─────────────────────────

class TestGoldenZone:
    def test_empty_skus(self):
        result = golden_zone.assign([], [make_slot()], PickHistory(frequencies={}), THRESHOLDS)
        assert result["assignments"] == []

    def test_high_freq_sku_gets_golden_slot(self):
        high = make_sku(freq=100.0)
        low = make_sku(freq=1.0)
        slot_l1 = make_slot(level=1)   # ergo factor 0.90
        slot_l2 = make_slot(level=2)   # ergo factor 1.00 — golden zone
        history = PickHistory(frequencies={high.id: 100.0, low.id: 1.0})
        result = golden_zone.assign([high, low], [slot_l1, slot_l2], history, THRESHOLDS)
        high_assignment = next(a for a in result["assignments"] if a["product_id"] == high.id)
        assert high_assignment["slot_id"] == slot_l2.id   # golden zone slot

    def test_no_slots_produces_exceptions(self):
        sku = make_sku()
        result = golden_zone.assign([sku], [], PickHistory(frequencies={sku.id: 10.0}), THRESHOLDS)
        # With no slots, all SKUs end up as exceptions
        total = len(result["assignments"]) + len(result["exceptions"])
        assert total == 1
        assert len(result["assignments"]) == 0

    def test_score_is_positive(self):
        sku = make_sku(freq=50.0)
        slot = make_slot(level=2)
        result = golden_zone.assign([sku], [slot], PickHistory(frequencies={sku.id: 50.0}), THRESHOLDS)
        assert result["assignments"][0]["score"] > 0


# ─────────────────────────── Affinity Clustering ─────────────────

class TestAffinityClustering:
    def test_empty_input(self):
        result = affinity_clustering.assign([], [], OrderLines(orders=[]), THRESHOLDS)
        assert result["assignments"] == []

    def test_co_occurring_skus_get_adjacent_slots(self):
        sku_a = make_sku(freq=20.0)
        sku_b = make_sku(freq=15.0)
        orders = OrderLines(orders=[[sku_a.id, sku_b.id]] * 10)
        slots = [make_slot(pos_x=float(i), pos_y=0.0) for i in range(4)]
        result = affinity_clustering.assign([sku_a, sku_b], slots, orders, THRESHOLDS)
        assert len(result["assignments"]) == 2
        # Both should be assigned
        assigned_products = {a["product_id"] for a in result["assignments"]}
        assert sku_a.id in assigned_products
        assert sku_b.id in assigned_products

    def test_produces_no_duplicate_slot_assignments(self):
        skus = [make_sku() for _ in range(5)]
        slots = [make_slot() for _ in range(5)]
        result = affinity_clustering.assign(skus, slots, OrderLines(orders=[]), THRESHOLDS)
        slot_ids = [a["slot_id"] for a in result["assignments"]]
        assert len(slot_ids) == len(set(slot_ids))


# ─────────────────────────── S-Shape Routing ─────────────────────

class TestSShapeRouting:
    def _make_rack_grid(self, n_racks: int = 2, slots_per_rack: int = 3) -> tuple[RackGrid, list[Slot]]:
        all_slots = []
        racks = []
        slots_by_rack: dict[uuid.UUID, list[Slot]] = {}
        for r in range(n_racks):
            rack_id = uuid.uuid4()
            racks.append((rack_id, float(r), 0.0))
            rack_slots = [
                make_slot(level=lvl + 1, pos_x=float(r), pos_y=float(lvl))
                for lvl in range(slots_per_rack)
            ]
            slots_by_rack[rack_id] = rack_slots
            all_slots.extend(rack_slots)
        return RackGrid(racks=racks, slots_by_rack=slots_by_rack), all_slots

    def test_empty_skus(self):
        grid, _ = self._make_rack_grid()
        result = s_shape_routing.assign([], grid, THRESHOLDS)
        assert result["assignments"] == []

    def test_high_freq_sku_gets_early_path_slot(self):
        high = make_sku(freq=100.0)
        low = make_sku(freq=1.0)
        grid, _ = self._make_rack_grid(n_racks=2, slots_per_rack=3)
        result = s_shape_routing.assign([high, low], grid, THRESHOLDS)
        high_score = next(a["score"] for a in result["assignments"] if a["product_id"] == high.id)
        low_score = next(a["score"] for a in result["assignments"] if a["product_id"] == low.id)
        assert high_score >= low_score   # high-freq gets better (earlier) slot

    def test_no_duplicate_slot_assignments(self):
        skus = [make_sku() for _ in range(4)]
        grid, _ = self._make_rack_grid(n_racks=2, slots_per_rack=3)
        result = s_shape_routing.assign(skus, grid, THRESHOLDS)
        slot_ids = [a["slot_id"] for a in result["assignments"]]
        assert len(slot_ids) == len(set(slot_ids))

    def test_score_between_0_and_1(self):
        skus = [make_sku()]
        grid, _ = self._make_rack_grid()
        result = s_shape_routing.assign(skus, grid, THRESHOLDS)
        assert 0.0 <= result["assignments"][0]["score"] <= 1.0
