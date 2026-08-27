from uuid import UUID

import pytest

from app.core.demo_tenants import DEMO_TENANT_NAMES, DEMO_TENANTS, DemoTenantSpec
from app.models.asset import Asset
from app.models.document import Document
from scripts.seed_demo_playground import get_or_create_asset, get_or_create_tenant
from tests.conftest import TestSessionLocal


@pytest.mark.asyncio
async def test_demo_tenants_endpoint_only_returns_known_demo_tenants(client):
    for name in ["Atlas Manufacturing", "Borealis Cold Chain", "Shadow Corp"]:
        response = await client.post("/api/v1/tenants", json={"name": name})
        assert response.status_code == 201

    response = await client.get("/api/v1/demo/tenants")
    assert response.status_code == 200

    payload = response.json()
    names = [item["name"] for item in payload]

    assert names == ["Atlas Manufacturing", "Borealis Cold Chain"]
    assert "Shadow Corp" not in names
    assert "Helios Energy Services" not in names
    assert all(item["description"] for item in payload)
    assert all(item["short_label"] for item in payload)


@pytest.mark.asyncio
async def test_operations_read_apis_are_tenant_scoped(client):
    atlas = await client.post("/api/v1/tenants", json={"name": "Atlas Manufacturing"})
    borealis = await client.post("/api/v1/tenants", json={"name": "Borealis Cold Chain"})
    atlas_id = UUID(atlas.json()["id"])
    borealis_id = UUID(borealis.json()["id"])

    async with TestSessionLocal() as session:
        session.add(
            Asset(
                tenant_id=atlas_id,
                asset_code="MACHINE-42",
                name="Hydraulic Press 42",
                location="Assembly Line 2",
                status="warning",
                active_error_code="AX-4317",
            )
        )
        session.add(
            Asset(
                tenant_id=borealis_id,
                asset_code="CHILLER-12",
                name="Main Chiller 12",
                location="Cold Storage Building A",
                status="warning",
                active_error_code="CL-209",
            )
        )
        await session.commit()

    atlas_assets = await client.get(f"/api/v1/tenants/{atlas_id}/assets")
    borealis_assets = await client.get(f"/api/v1/tenants/{borealis_id}/assets")

    assert atlas_assets.status_code == 200
    assert borealis_assets.status_code == 200

    atlas_codes = [item["asset_code"] for item in atlas_assets.json()]
    borealis_codes = [item["asset_code"] for item in borealis_assets.json()]

    assert atlas_codes == ["MACHINE-42"]
    assert borealis_codes == ["CHILLER-12"]
    assert "CHILLER-12" not in atlas_codes
    assert "MACHINE-42" not in borealis_codes


@pytest.mark.asyncio
async def test_documents_list_is_tenant_scoped(client):
    tenant_a = await client.post("/api/v1/tenants", json={"name": "Atlas Manufacturing"})
    tenant_b = await client.post("/api/v1/tenants", json={"name": "Borealis Cold Chain"})
    tenant_a_id = UUID(tenant_a.json()["id"])
    tenant_b_id = UUID(tenant_b.json()["id"])

    async with TestSessionLocal() as session:
        session.add(
            Document(
                tenant_id=tenant_a_id,
                filename="equipment-error-codes.txt",
                content_type="text/plain",
                file_size_bytes=100,
                checksum_sha256="a" * 64,
                status="indexed",
            )
        )
        session.add(
            Document(
                tenant_id=tenant_b_id,
                filename="refrigeration-error-codes.txt",
                content_type="text/plain",
                file_size_bytes=120,
                checksum_sha256="b" * 64,
                status="indexed",
            )
        )
        await session.commit()

    response_a = await client.get(f"/api/v1/tenants/{tenant_a_id}/documents")
    response_b = await client.get(f"/api/v1/tenants/{tenant_b_id}/documents")

    assert [item["filename"] for item in response_a.json()] == ["equipment-error-codes.txt"]
    assert [item["filename"] for item in response_b.json()] == ["refrigeration-error-codes.txt"]


@pytest.mark.asyncio
async def test_document_inspect_rejects_cross_tenant_access(client, monkeypatch):
    tenant_a = await client.post("/api/v1/tenants", json={"name": "Atlas Manufacturing"})
    tenant_b = await client.post("/api/v1/tenants", json={"name": "Borealis Cold Chain"})
    tenant_a_id = UUID(tenant_a.json()["id"])
    tenant_b_id = UUID(tenant_b.json()["id"])

    async with TestSessionLocal() as session:
        document = Document(
            tenant_id=tenant_a_id,
            filename="equipment-error-codes.txt",
            content_type="text/plain",
            file_size_bytes=100,
            checksum_sha256="c" * 64,
            status="indexed",
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        document_id = document.id

    async def fake_chunks(**kwargs):
        return []

    monkeypatch.setattr(
        "app.api.v1.documents.list_document_chunks",
        fake_chunks,
    )

    denied = await client.get(
        f"/api/v1/tenants/{tenant_b_id}/documents/{document_id}",
    )
    assert denied.status_code == 404

    allowed = await client.get(
        f"/api/v1/tenants/{tenant_a_id}/documents/{document_id}",
    )
    assert allowed.status_code == 200
    assert allowed.json()["note"] == "Indexed content / chunks"


def test_demo_tenant_catalog_includes_e100_isolation_names():
    assert DEMO_TENANT_NAMES == {
        "Atlas Manufacturing",
        "Borealis Cold Chain",
        "Helios Energy Services",
        "Northstar Commercial",
    }
    assert [spec.slug for spec in DEMO_TENANTS] == [
        "atlas-manufacturing",
        "borealis-cold-chain",
        "helios-energy-services",
        "northstar-commercial",
    ]


@pytest.mark.asyncio
async def test_seed_helpers_are_idempotent_for_assets():
    spec = DemoTenantSpec(
        name="Atlas Manufacturing",
        slug="atlas-manufacturing",
        description="test",
        short_label="Manufacturing",
    )

    async with TestSessionLocal() as session:
        tenant = await get_or_create_tenant(session, spec)
        first = await get_or_create_asset(
            session,
            tenant_id=tenant.id,
            asset_code="MACHINE-42",
            name="Hydraulic Press 42",
            location="Assembly Line 2",
            status="warning",
            active_error_code="AX-4317",
        )
        second = await get_or_create_asset(
            session,
            tenant_id=tenant.id,
            asset_code="MACHINE-42",
            name="Hydraulic Press 42",
            location="Assembly Line 2",
            status="warning",
            active_error_code="AX-4317",
        )
        await session.commit()

        assert first.id == second.id
