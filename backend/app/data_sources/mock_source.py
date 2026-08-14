"""
MockDataSource — loads from seed JSON files under backend/seed/.

Returns Item, PickHistory and OrderLines ready for algorithm consumption.
All product_id values use uuid5(DNS, sku) so they are stable and
reproducible without needing the DB to be seeded first.
"""
from __future__ import annotations

import json
import uuid
from collections import defaultdict
from pathlib import Path

from app.algorithms.types import Dims, Item, OrderLines, PickHistory

_SEED = Path(__file__).parent.parent.parent / "seed"


def _sku_id(sku: str) -> uuid.UUID:
    """Stable deterministic UUID keyed by SKU string."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, sku)


class MockDataSource:
    """Load product / pick / order data from local seed JSON files."""

    async def get_items(self) -> list[Item]:
        with (_SEED / "products.json").open() as f:
            records = json.load(f)
        items = []
        for r in records:
            items.append(
                Item(
                    id=_sku_id(r["sku"]),
                    sku=r["sku"],
                    dims=Dims(
                        length=float(r["length"]),
                        width=float(r["width"]),
                        height=float(r["height"]),
                    ),
                    weight=float(r["weight"]),
                    abc_class=r["abc_class"],
                    category=r.get("category", ""),
                    quantity=1,
                )
            )
        return items

    async def get_pick_history(self, lookback_days: int = 90) -> PickHistory:
        with (_SEED / "pick_events.json").open() as f:
            events = json.load(f)
        freq: dict[uuid.UUID, float] = defaultdict(float)
        for e in events:
            freq[uuid.UUID(e["product_id"])] += 1.0
        return PickHistory(frequencies=dict(freq))

    async def get_order_lines(self) -> OrderLines:
        with (_SEED / "order_lines.json").open() as f:
            lines = json.load(f)
        orders_map: dict[str, list[uuid.UUID]] = defaultdict(list)
        for line in lines:
            orders_map[line["order_id"]].append(uuid.UUID(line["product_id"]))
        return OrderLines(orders=list(orders_map.values()))
