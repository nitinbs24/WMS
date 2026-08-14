"""
Data source adapter interface.

Provides an abstract protocol so the v1 mock source and the Phase 2
Odoo JSON-RPC source can be swapped without changing any calling code.
"""
from __future__ import annotations

from typing import Protocol

from app.algorithms.types import Item, OrderLines, PickHistory


class DataSource(Protocol):
    """
    Abstract interface for product data ingestion.
    v1: MockDataSource (loads from seed JSON files)
    Phase 2: OdooDataSource (JSON-RPC calls to live Odoo instance)
    """

    async def get_items(self) -> list[Item]:
        """Return all products as Item objects ready for algorithm consumption."""
        ...

    async def get_pick_history(self, lookback_days: int) -> PickHistory:
        """Return aggregated pick frequencies within the lookback window."""
        ...

    async def get_order_lines(self) -> OrderLines:
        """Return order co-occurrence data for Apriori Affinity Clustering."""
        ...
