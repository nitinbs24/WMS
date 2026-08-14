"""
Odoo JSON-RPC data source — Phase 2 placeholder.

When Phase 2 begins, this replaces MockDataSource behind the DataSource interface.
Nothing else in the application changes — only this file and the DI binding.
"""
from __future__ import annotations

from app.algorithms.types import Item, OrderLines, PickHistory


class OdooDataSource:
    """
    Phase 2 — connects to live Odoo via JSON-RPC.
    Reads: product.template, stock.move, sale.order.line, stock.quant
    """

    def __init__(self, odoo_url: str, db: str, uid: int, password: str):
        self.odoo_url = odoo_url
        self.db = db
        self.uid = uid
        self.password = password

    async def get_items(self) -> list[Item]:
        raise NotImplementedError("Phase 2")

    async def get_pick_history(self, lookback_days: int = 90) -> PickHistory:
        raise NotImplementedError("Phase 2")

    async def get_order_lines(self) -> OrderLines:
        raise NotImplementedError("Phase 2")
