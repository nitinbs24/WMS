"""
arq worker settings and task definitions.

The worker process runs: `python -m arq app.workers.settings.WorkerSettings`
It executes optimization jobs outside the FastAPI request/response cycle.
"""
from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings

settings = get_settings()


async def run_optimization(ctx: dict, run_id: str) -> None:
    """
    Execute a single optimization run.

    Job lifecycle: queued → running → completed | completed_with_exceptions | failed
    Retry policy: 1 automatic retry on unhandled exception (see WorkerSettings).

    Phase 5 — full implementation including:
    - Load run config from DB
    - Load input data (products, pallets/SKUs, slots, thresholds)
    - Call optimization_service.py orchestrator
    - Write SlotAssignment + RunException rows
    - Update OptimizationRun.status + summary_metrics
    """
    raise NotImplementedError("Implemented in Phase 5")


async def scheduled_run_dispatch(ctx: dict) -> None:
    """
    arq cron task — fires on schedule.
    Reads active Schedule rows from DB, creates OptimizationRun rows,
    and enqueues run_optimization for each.
    """
    raise NotImplementedError("Implemented in Phase 5")


class WorkerSettings:
    """arq worker configuration."""
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [run_optimization]
    cron_jobs = [
        cron(scheduled_run_dispatch, minute=0),  # fires hourly — dispatcher checks actual schedules
    ]
    max_tries = 2  # 1 retry on failure
    job_timeout = 3600  # 1 hour max per run
