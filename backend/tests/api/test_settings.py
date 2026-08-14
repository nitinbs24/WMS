"""
Settings API tests.
Tests: GET thresholds (seeded), POST new version, version increment.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_thresholds(client: AsyncClient, admin_token: str, default_thresholds):
    resp = await client.get(
        "/api/v1/settings/thresholds",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 1
    assert data["is_active"] is True
    assert "heavy_weight_kg" in data


@pytest.mark.asyncio
async def test_get_thresholds_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/settings/thresholds")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_new_threshold_version(client: AsyncClient, admin_token: str, default_thresholds):
    resp = await client.post(
        "/api/v1/settings/thresholds",
        json={"heavy_weight_kg": 700.0, "medium_weight_kg": 350.0, "com_threshold": 0.60,
              "blf_com_threshold": 0.65, "aisle_a_density_cap": 0.40,
              "ergonomic_factors": {"L1": 0.90, "L2": 1.00, "L3": 0.70, "L4": 0.50},
              "pick_lookback_days": 60},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == 2
    assert data["heavy_weight_kg"] == 700.0
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_history_shows_both_versions(client: AsyncClient, admin_token: str, default_thresholds):
    # Create v2
    await client.post(
        "/api/v1/settings/thresholds",
        json={"heavy_weight_kg": 700.0, "medium_weight_kg": 350.0, "com_threshold": 0.60,
              "blf_com_threshold": 0.65, "aisle_a_density_cap": 0.40,
              "ergonomic_factors": {}, "pick_lookback_days": 60},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.get(
        "/api/v1/settings/thresholds/history",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 2
    # Only latest should be active
    assert sum(1 for h in history if h["is_active"]) == 1
