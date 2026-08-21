import pytest


@pytest.mark.asyncio
async def test_create_user(client):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Tenant A"},
    )

    tenant_id = tenant_response.json()["id"]

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/users",
        json={
            "email": "kaan@example.com",
            "full_name": "Kaan Kureli",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == tenant_id
    assert data["email"] == "kaan@example.com"
    assert data["full_name"] == "Kaan Kureli"


@pytest.mark.asyncio
async def test_list_users_is_tenant_scoped(client):
    tenant_a = await client.post(
        "/api/v1/tenants",
        json={"name": "Tenant A"},
    )

    tenant_b = await client.post(
        "/api/v1/tenants",
        json={"name": "Tenant B"},
    )

    tenant_a_id = tenant_a.json()["id"]
    tenant_b_id = tenant_b.json()["id"]

    await client.post(
        f"/api/v1/tenants/{tenant_a_id}/users",
        json={
            "email": "user-a@example.com",
            "full_name": "User A",
        },
    )

    await client.post(
        f"/api/v1/tenants/{tenant_b_id}/users",
        json={
            "email": "user-b@example.com",
            "full_name": "User B",
        },
    )

    response = await client.get(
        f"/api/v1/tenants/{tenant_a_id}/users",
    )

    assert response.status_code == 200

    users = response.json()

    assert len(users) == 1
    assert users[0]["email"] == "user-a@example.com"
    assert users[0]["tenant_id"] == tenant_a_id


@pytest.mark.asyncio
async def test_duplicate_email_in_same_tenant_returns_conflict(client):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Tenant A"},
    )

    tenant_id = tenant_response.json()["id"]

    payload = {
        "email": "kaan@example.com",
        "full_name": "Kaan Kureli",
    }

    first_response = await client.post(
        f"/api/v1/tenants/{tenant_id}/users",
        json=payload,
    )

    second_response = await client.post(
        f"/api/v1/tenants/{tenant_id}/users",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_same_email_is_allowed_in_different_tenants(client):
    tenant_a = await client.post(
        "/api/v1/tenants",
        json={"name": "Tenant A"},
    )

    tenant_b = await client.post(
        "/api/v1/tenants",
        json={"name": "Tenant B"},
    )

    email = "kaan@example.com"

    response_a = await client.post(
        f"/api/v1/tenants/{tenant_a.json()['id']}/users",
        json={
            "email": email,
            "full_name": "Kaan A",
        },
    )

    response_b = await client.post(
        f"/api/v1/tenants/{tenant_b.json()['id']}/users",
        json={
            "email": email,
            "full_name": "Kaan B",
        },
    )

    assert response_a.status_code == 201
    assert response_b.status_code == 201


@pytest.mark.asyncio
async def test_create_user_for_unknown_tenant_returns_not_found(client):
    fake_tenant_id = "00000000-0000-0000-0000-000000000001"

    response = await client.post(
        f"/api/v1/tenants/{fake_tenant_id}/users",
        json={
            "email": "kaan@example.com",
            "full_name": "Kaan Kureli",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant not found."
