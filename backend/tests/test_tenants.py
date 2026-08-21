import pytest


@pytest.mark.asyncio
async def test_create_tenant(client):
    response = await client.post(
        "/api/v1/tenants",
        json={
            "name": "Siemens Manufacturing Demo",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Siemens Manufacturing Demo"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_tenant(client):
    create_response = await client.post(
        "/api/v1/tenants",
        json={
            "name": "Memorial Healthcare Demo",
        },
    )

    tenant_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/tenants/{tenant_id}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == tenant_id
    assert response.json()["name"] == "Memorial Healthcare Demo"


@pytest.mark.asyncio
async def test_duplicate_tenant_returns_conflict(client):
    payload = {
        "name": "Setur Demo",
    }

    first_response = await client.post(
        "/api/v1/tenants",
        json=payload,
    )

    second_response = await client.post(
        "/api/v1/tenants",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == ("Tenant with this name already exists.")
