"""
Mock data source — loads from seed JSON files in backend/seed/.
Implements the DataSource protocol for v1 local development.
Phase 3 will add full implementation with seeded pick history and affinity groups.
"""
from __future__ import annotations

from pathlib import Path

from app.algorithms.types import Item, OrderLines, PickHistory

SEED_DIR = Path(__file__).parent.parent.parent / "seed"


class MockDataSource:
    """Loads mock product/event data from seed JSON files."""

    async def get_items(self) -> list[Item]:
        """Phase 3 — load from seed/products.json"""
        raise NotImplementedError("Implemented in Phase 3")

    async def get_pick_history(self, lookback_days: int = 90) -> PickHistory:
        """Phase 3 — load from seed/pick_events.json and aggregate by window"""
        raise NotImplementedError("Implemented in Phase 3")

    async def get_order_lines(self) -> OrderLines:
        """Phase 3 — load from seed/order_lines.json"""
        raise NotImplementedError("Implemented in Phase 3")
