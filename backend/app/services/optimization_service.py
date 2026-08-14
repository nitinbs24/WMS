"""
Optimization orchestration service.

This is the single place that:
1. Loads all input data from DB + data source
2. Dispatches to the correct algorithm module(s)
3. Persists the SlotAssignment + RunException rows
4. Updates OptimizationRun.status and summary_metrics

Called exclusively by the arq worker task (never inline in an API handler).
No HTTP context, no FastAPI dependencies — just DB session + run_id.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.safety import SafetyViolation, validate_placement
from app.algorithms.types import (
    Dims, Item, OrderLines, Pallet as AlgoPallet, PickHistory,
    RackGrid, SKU, Slot as AlgoSlot, Thresholds,
)
from app.algorithms.space import ffdh_com, blf_stratified, wbfdh
from app.algorithms.picking import golden_zone, affinity_clustering, s_shape_routing
from app.data_sources.mock_source import MockDataSource
from app.models.optimization import OptimizationRun, RunException, SlotAssignment
from app.models.product import Pallet as DBPallet, Product
from app.models.warehouse import Slot

_PALLET_DIMS = Dims(length=1.2, width=0.8, height=2.0)


async def execute_run(db: AsyncSession, run_id: uuid.UUID) -> None:
    """
    Full optimization pipeline. Called by the arq worker.
    Updates run status throughout; never raises (catches and marks failed).
    """
    # 1. Load run config
    result = await db.execute(select(OptimizationRun).where(OptimizationRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        return   # stale job — run deleted

    # Mark running
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        await _do_run(db, run)
    except Exception as exc:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.summary_metrics = {"error": str(exc)}
        await db.commit()
        raise


async def _do_run(db: AsyncSession, run: OptimizationRun) -> None:
    """Inner pipeline — separated so the outer wrapper can catch cleanly."""
    thresholds = _thresholds_from_snapshot(run.thresholds_snapshot)

    # 2. Load warehouse slots
    result = await db.execute(select(Slot))
    db_slots = list(result.scalars().all())
    algo_slots = [_db_slot_to_algo(s) for s in db_slots]
    open_slots = [s for s in algo_slots if s.status == "empty"]

    source = MockDataSource()

    if run.goal == "space_efficiency":
        result_data, algo_pallets = await _run_space(run, open_slots, thresholds, source)
    else:
        result_data, algo_pallets = await _run_picking(run, open_slots, thresholds, source, db)

    # 3. Persist algorithm pallets to DB so FK constraints are satisfied
    pallet_id_map: dict[uuid.UUID, uuid.UUID] = {}  # algo_id → db_id
    for ap in algo_pallets:
        db_p = DBPallet(
            computed_height=ap.computed_height,
            computed_weight=ap.computed_weight,
            computed_volume=ap.computed_volume,
            stability_status=ap.stability_status,
        )
        db.add(db_p)
        await db.flush()   # get DB-assigned id
        pallet_id_map[ap.id] = db_p.id
    assignments = result_data["assignments"]
    exceptions = result_data["exceptions"]

    for a in assignments:
        algo_pid = a.get("pallet_id")
        db.add(SlotAssignment(
            run_id=run.id,
            pallet_id=pallet_id_map.get(algo_pid) if algo_pid else None,
            product_id=a.get("product_id"),
            slot_id=a["slot_id"],
            score=float(a["score"]),
        ))

    for e in exceptions:
        algo_pid = e.get("pallet_id")
        db.add(RunException(
            run_id=run.id,
            pallet_id=pallet_id_map.get(algo_pid) if algo_pid else None,
            product_id=e.get("product_id"),
            reason_code=e["reason_code"],
            reason_detail=e.get("reason_detail", ""),
        ))

    # 4. Update slot statuses for assigned slots
    assigned_slot_ids = {a["slot_id"] for a in assignments}
    if assigned_slot_ids:
        await db.execute(
            update(Slot)
            .where(Slot.id.in_(assigned_slot_ids))
            .values(status="occupied")
        )

    # 5. Compute summary metrics
    fill_rate = len(assignments) / max(len(algo_slots), 1)
    run.status = "completed" if not exceptions else "completed_with_exceptions"
    run.completed_at = datetime.now(timezone.utc)
    run.summary_metrics = {
        "assignments": len(assignments),
        "exceptions": len(exceptions),
        "fill_rate_pct": round(fill_rate * 100, 2),
        "total_slots": len(algo_slots),
        "open_slots_before": len(open_slots),
    }
    await db.commit()


async def _run_space(
    run: OptimizationRun,
    open_slots: list[AlgoSlot],
    thresholds: Thresholds,
    source: MockDataSource,
) -> tuple[dict, list]:
    items = await source.get_items()

    # Item → Pallet
    if run.algorithm == "ffdh_com":
        pallets = ffdh_com.build_pallets(items, _PALLET_DIMS, thresholds)
    elif run.algorithm == "blf_stratified":
        pallets = blf_stratified.build_pallets(items, _PALLET_DIMS, thresholds)
    else:
        raise ValueError(f"Unknown space algorithm: {run.algorithm}")

    # Pallet → Slot (always W-BFDH)
    return wbfdh.assign(pallets, open_slots, thresholds), pallets


async def _run_picking(
    run: OptimizationRun,
    open_slots: list[AlgoSlot],
    thresholds: Thresholds,
    source: MockDataSource,
    db: AsyncSession,
) -> tuple[dict, list]:
    items = await source.get_items()
    pick_history = await source.get_pick_history(thresholds.pick_lookback_days)
    order_lines = await source.get_order_lines()

    # Load actual DB product IDs keyed by SKU so FK refs are valid
    db_result = await db.execute(select(Product.id, Product.sku))
    db_sku_to_id: dict[str, uuid.UUID] = {row.sku: row.id for row in db_result}

    # Build pick_history with DB IDs (source uses uuid5 IDs, DB uses gen_random_uuid)
    db_pick_freq: dict[uuid.UUID, float] = {}
    for item in items:
        db_id = db_sku_to_id.get(item.sku)
        if db_id:
            # Map uuid5 freq → DB id freq
            src_freq = pick_history.frequencies.get(item.id, 0.0)
            db_pick_freq[db_id] = src_freq

    # Remap order_lines to use DB IDs
    src_to_db: dict[uuid.UUID, uuid.UUID] = {
        item.id: db_sku_to_id[item.sku] for item in items if item.sku in db_sku_to_id
    }
    remapped_orders = [
        [src_to_db[pid] for pid in order if pid in src_to_db]
        for order in order_lines.orders
    ]
    db_order_lines = OrderLines(orders=[o for o in remapped_orders if o])

    from app.algorithms.types import PickHistory as PH
    db_pick_history = PH(frequencies=db_pick_freq)

    # Convert Item → SKU using DB IDs
    skus = [
        SKU(
            id=db_sku_to_id[item.sku],
            sku=item.sku,
            abc_class=item.abc_class,
            pick_frequency=db_pick_freq.get(db_sku_to_id.get(item.sku, item.id), 0.0),
            dims=item.dims,
            weight=item.weight,
        )
        for item in items
        if item.sku in db_sku_to_id
    ]

    if run.algorithm == "golden_zone":
        return golden_zone.assign(skus, open_slots, db_pick_history, thresholds), []
    elif run.algorithm == "affinity_clustering":
        return affinity_clustering.assign(skus, open_slots, db_order_lines, thresholds), []
    elif run.algorithm == "s_shape_routing":
        grid = _build_rack_grid(open_slots)
        return s_shape_routing.assign(skus, grid, thresholds), []
    else:
        raise ValueError(f"Unknown picking algorithm: {run.algorithm}")



def _thresholds_from_snapshot(snapshot: dict) -> Thresholds:
    return Thresholds(
        heavy_weight_kg=snapshot.get("heavy_weight_kg", 600.0),
        medium_weight_kg=snapshot.get("medium_weight_kg", 300.0),
        com_threshold=snapshot.get("com_threshold", 0.55),
        blf_com_threshold=snapshot.get("blf_com_threshold", 0.60),
        aisle_a_density_cap=snapshot.get("aisle_a_density_cap", 0.35),
        ergonomic_factors=snapshot.get("ergonomic_factors", {"L1": 0.90, "L2": 1.00, "L3": 0.70, "L4": 0.50}),
        pick_lookback_days=snapshot.get("pick_lookback_days", 90),
    )


def _db_slot_to_algo(slot: Slot) -> AlgoSlot:
    return AlgoSlot(
        id=slot.id,
        rack_id=slot.rack_id,
        level=slot.level,
        clearance_height=float(slot.clearance_height),
        weight_capacity=float(slot.weight_capacity),
        pos_x=float(slot.pos_x),
        pos_y=float(slot.pos_y),
        pos_z=float(slot.pos_z),
        is_aisle_boundary=slot.is_aisle_boundary,
        status=slot.status,
    )


def _build_rack_grid(slots: list[AlgoSlot]) -> RackGrid:
    """Build RackGrid from open slots for S-Shape routing."""
    rack_ids: list[uuid.UUID] = []
    slots_by_rack: dict[uuid.UUID, list[AlgoSlot]] = {}
    seen: set[uuid.UUID] = set()

    for slot in slots:
        if slot.rack_id not in seen:
            rack_ids.append(slot.rack_id)
            seen.add(slot.rack_id)
        slots_by_rack.setdefault(slot.rack_id, []).append(slot)

    # (rack_id, aisle_pos≈pos_y, rack_pos≈pos_x)
    racks = [(rid, slots_by_rack[rid][0].pos_y, slots_by_rack[rid][0].pos_x) for rid in rack_ids]
    return RackGrid(racks=racks, slots_by_rack=slots_by_rack)
