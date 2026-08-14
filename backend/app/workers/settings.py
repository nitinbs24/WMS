"""
arq worker — optimization job execution.

The worker process is started with:
  python -m arq app.workers.settings.WorkerSettings

It picks up jobs enqueued by POST /api/v1/runs and executes them
in a separate process so CPU-bound algorithm work never blocks the API.
"""
from __future__ import annotations

import uuid

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import get_settings
from app.services.optimization_service import execute_run

settings = get_settings()


async def startup(ctx: dict) -> None:
    """Create a DB session factory shared across jobs in this worker process."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    ctx["session_factory"] = async_sessionmaker(bind=engine, expire_on_commit=False)
    ctx["engine"] = engine


async def shutdown(ctx: dict) -> None:
    await ctx["engine"].dispose()


async def run_optimization(ctx: dict, run_id: str) -> dict:
    """
    Execute a single optimization run end-to-end.

    Job lifecycle: queued → running → completed | completed_with_exceptions | failed
    Retry policy: max_tries=2 (1 automatic retry on unhandled exception).

    Args:
        ctx: arq context dict (contains session_factory from startup)
        run_id: UUID string of the OptimizationRun row to execute

    Returns:
        dict with status and summary_metrics (arq stores this as job result)
    """
    session_factory = ctx["session_factory"]
    rid = uuid.UUID(run_id)

    async with session_factory() as db:
        await execute_run(db, rid)

    return {"run_id": run_id, "status": "done"}


async def scheduled_run_dispatch(ctx: dict) -> None:
    """
    arq cron task — fires every hour.
    Reads active Schedule rows from DB and enqueues run_optimization for any
    whose cron_expression matches the current time.
    """
    # Phase 5 — basic implementation: enqueue any due schedules
    from sqlalchemy import select
    from app.models.schedule import Schedule
    import croniter, datetime

    session_factory = ctx["session_factory"]
    now = datetime.datetime.now(datetime.timezone.utc)

    async with session_factory() as db:
        result = await db.execute(select(Schedule).where(Schedule.is_active == True))  # noqa: E712
        schedules = list(result.scalars().all())

    queue = await ctx["redis"].default_queue_name if hasattr(ctx, "redis") else None
    for schedule in schedules:
        try:
            cron_it = croniter.croniter(schedule.cron_expression, now)
            last = cron_it.get_prev(datetime.datetime)
            # Fire if within last 5 minutes (cron precision)
            if (now - last).total_seconds() <= 300:
                from arq import ArqRedis
                redis: ArqRedis = ctx["redis"]
                await redis.enqueue_job(
                    "run_optimization",
                    str(schedule.id),
                )
        except Exception:
            pass   # bad cron expression — skip silently


class WorkerSettings:
    """arq worker configuration."""
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [run_optimization]
    cron_jobs = [
        cron(scheduled_run_dispatch, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_tries = 2        # 1 retry on failure
    job_timeout = 3600   # 1 hour max per run
    keep_result = 3600   # keep job result for 1 hour
