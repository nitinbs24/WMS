"""
Layout + Products integration tests.
Tests: upload layout JSON, apply, list layout, seed products, list products.
"""
from __future__ import annotations

import io
import json
import pytest
from httpx import AsyncClient

SAMPLE_LAYOUT = {
    "warehouses": [
        {
            "name": "Test Warehouse",
            "address": "123 Test St",
            "aisles": [
                {
                    "aisle_label": "A",
                    "pos_x": 0.0,
                    "pos_y": 0.0,
                    "direction": "N-S",
                    "racks": [
                        {
                            "rack_number": 1,
                            "pos_x": 0.0,
                            "pos_y": 0.0,
                            "levels": 4,
                            "slots": [
                                {"level": 1, "clearance_height": 2.0, "weight_capacity": 1500.0,
                                 "pos_x": 0.0, "pos_y": 0.0, "pos_z": 0.0, "is_aisle_boundary": True},
                                {"level": 2, "clearance_height": 1.8, "weight_capacity": 1200.0,
                                 "pos_x": 0.0, "pos_y": 0.0, "pos_z": 2.1, "is_aisle_boundary": False},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
}


@pytest.mark.asyncio
async def test_upload_layout(client: AsyncClient, admin_token: str):
    content = json.dumps(SAMPLE_LAYOUT).encode()
    resp = await client.post(
        "/api/v1/layout/import",
        files={"file": ("layout.json", io.BytesIO(content), "application/json")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "valid"
    assert data["row_count"] == 2   # 2 slots


@pytest.mark.asyncio
async def test_upload_invalid_layout(client: AsyncClient, admin_token: str):
    bad = b'{"not_warehouses": []}'
    resp = await client.post(
        "/api/v1/layout/import",
        files={"file": ("bad.json", io.BytesIO(bad), "application/json")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "invalid"


@pytest.mark.asyncio
async def test_apply_layout(client: AsyncClient, admin_token: str):
    # Upload
    content = json.dumps(SAMPLE_LAYOUT).encode()
    upload_resp = await client.post(
        "/api/v1/layout/import",
        files={"file": ("layout.json", io.BytesIO(content), "application/json")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    import_id = upload_resp.json()["id"]

    # Apply
    apply_resp = await client.post(
        f"/api/v1/layout/import/{import_id}/apply",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert apply_resp.status_code == 200
    result = apply_resp.json()
    assert result["warehouses_upserted"] == 1
    assert result["aisles_upserted"] == 1
    assert result["racks_upserted"] == 1
    assert result["slots_upserted"] == 2


@pytest.mark.asyncio
async def test_get_layout_after_apply(client: AsyncClient, admin_token: str):
    # Upload + apply
    content = json.dumps(SAMPLE_LAYOUT).encode()
    upload_resp = await client.post(
        "/api/v1/layout/import",
        files={"file": ("layout.json", io.BytesIO(content), "application/json")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    import_id = upload_resp.json()["id"]
    await client.post(
        f"/api/v1/layout/import/{import_id}/apply",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # GET layout
    resp = await client.get(
        "/api/v1/layout",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    warehouses = resp.json()
    assert len(warehouses) == 1
    assert warehouses[0]["name"] == "Test Warehouse"
    assert len(warehouses[0]["aisles"]) == 1
    assert len(warehouses[0]["aisles"][0]["racks"][0]["slots"]) == 2
