"""
Optimization runs integration tests.

Strategy: POST /runs to create a queued run, then call the optimization
service directly (synchronously) to avoid needing a live arq/Redis.
Tests verify the full pipeline: create → execute → check assignments.
"""
from __future__ import annotations

import io
import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.optimization_service import execute_run


# ─── helpers ───────────────────────────────────────────────────────────────

SAMPLE_LAYOUT = {
    "warehouses": [{
        "name": "Runs Test Warehouse",
        "address": None,
        "aisles": [{
            "aisle_label": "A",
            "pos_x": 0.0, "pos_y": 0.0, "direction": "N-S",
            "racks": [
                {
                    "rack_number": i + 1,
                    "pos_x": float(i), "pos_y": 0.0, "levels": 4,
                    "slots": [
                        {
                            "level": lvl + 1,
                            "clearance_height": 2.0,
                            "weight_capacity": 1500.0,
                            "pos_x": float(i), "pos_y": 0.0,
                            "pos_z": float(lvl) * 2.1,
                            "is_aisle_boundary": lvl == 0,
                        }
                        for lvl in range(4)
                    ],
                }
                for i in range(5)   # 5 racks × 4 slots = 20 slots
            ],
        }],
    }]
}


async def _apply_layout(client: AsyncClient, admin_token: str) -> None:
    """Upload and apply the sample layout."""
    content = json.dumps(SAMPLE_LAYOUT).encode()
    upload = await client.post(
        "/api/v1/layout/import",
        files={"file": ("layout.json", io.BytesIO(content), "application/json")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    import_id = upload.json()["id"]
    await client.post(
        f"/api/v1/layout/import/{import_id}/apply",
        headers={"Authorization": f"Bearer {admin_token}"},
    )


async def _seed_products(client: AsyncClient, admin_token: str) -> None:
    await client.post("/api/v1/products/seed", headers={"Authorization": f"Bearer {admin_token}"})


# ─── tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_run_invalid_algorithm(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/v1/runs",
        json={"goal": "space_efficiency", "algorithm": "bad_algo", "scope": "full"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_run_staff_forbidden(client: AsyncClient, db_session: AsyncSession):
    from app.models.user import User
    from app.core.security import hash_password
    staff = User(name="Staff", email="staff3@example.com",
                 password_hash=hash_password("pass"), role="staff")
    db_session.add(staff)
    await db_session.commit()
    login = await client.post("/api/v1/auth/login", json={"email": "staff3@example.com", "password": "pass"})
    token = login.json()["access_token"]
    resp = await client.post(
        "/api/v1/runs",
        json={"goal": "space_efficiency", "algorithm": "ffdh_com", "scope": "full"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_run_queued(client: AsyncClient, admin_token: str, default_thresholds):
    resp = await client.post(
        "/api/v1/runs",
        json={"goal": "space_efficiency", "algorithm": "ffdh_com", "scope": "full"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "queued"
    assert data["goal"] == "space_efficiency"
    assert data["algorithm"] == "ffdh_com"


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient, admin_token: str, default_thresholds):
    # Create a run
    await client.post(
        "/api/v1/runs",
        json={"goal": "picking_efficiency", "algorithm": "golden_zone", "scope": "full"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.get("/api/v1/runs", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_run_404(client: AsyncClient, admin_token: str):
    import uuid
    resp = await client.get(
        f"/api/v1/runs/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_space_run_full_pipeline(
    client: AsyncClient,
    admin_token: str,
    default_thresholds,
    db_session: AsyncSession,
):
    """
    Full pipeline test: layout + products → create run → execute → assignments.
    We call execute_run() directly (no arq) so the test is self-contained.
    """
    await _apply_layout(client, admin_token)
    await _seed_products(client, admin_token)

    # Create queued run
    resp = await client.post(
        "/api/v1/runs",
        json={"goal": "space_efficiency", "algorithm": "ffdh_com", "scope": "full"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    run_id = resp.json()["id"]

    # Execute synchronously using the service (bypasses arq)
    import uuid as _uuid
    await execute_run(db_session, _uuid.UUID(run_id))

    # Poll run status
    run_resp = await client.get(
        f"/api/v1/runs/{run_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_data = run_resp.json()
    assert run_data["status"] in ("completed", "completed_with_exceptions")
    assert run_data["summary_metrics"]["assignments"] >= 0

    # Assignments should exist
    asgn_resp = await client.get(
        f"/api/v1/runs/{run_id}/assignments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert asgn_resp.status_code == 200


@pytest.mark.asyncio
async def test_picking_run_full_pipeline(
    client: AsyncClient,
    admin_token: str,
    default_thresholds,
    db_session: AsyncSession,
):
    await _apply_layout(client, admin_token)
    await _seed_products(client, admin_token)

    resp = await client.post(
        "/api/v1/runs",
        json={"goal": "picking_efficiency", "algorithm": "golden_zone", "scope": "full"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = resp.json()["id"]

    import uuid as _uuid
    await execute_run(db_session, _uuid.UUID(run_id))

    run_resp = await client.get(
        f"/api/v1/runs/{run_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert run_resp.json()["status"] in ("completed", "completed_with_exceptions")


@pytest.mark.asyncio
async def test_rollback_run(
    client: AsyncClient,
    admin_token: str,
    default_thresholds,
    db_session: AsyncSession,
):
    await _apply_layout(client, admin_token)
    await _seed_products(client, admin_token)

    resp = await client.post(
        "/api/v1/runs",
        json={"goal": "space_efficiency", "algorithm": "blf_stratified", "scope": "full"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = resp.json()["id"]

    import uuid as _uuid
    await execute_run(db_session, _uuid.UUID(run_id))

    # Rollback
    rb = await client.post(
        f"/api/v1/runs/{run_id}/rollback",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rb.status_code == 200
    assert "rolled_back_slots" in rb.json()
