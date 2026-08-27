"""Idempotent seed for the public Enterprise Agentic AI Playground.

Creates/reuses demo tenants, operational/commercial data, and indexes tenant
documents into Qdrant through the existing ingestion pipeline.

Usage:
  PYTHONPATH=. uv run --env-file .env.development python scripts/seed_demo_playground.py
  PYTHONPATH=. uv run --env-file .env.production python scripts/seed_demo_playground.py
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import settings
from app.core.demo_tenants import DEMO_TENANTS, DemoTenantSpec
from app.db.session import SessionLocal, close_db
from app.models import (
    Asset,
    Company,
    CompanyPayment,
    CompanyRevenue,
    CompanyTransaction,
    Document,
    MaintenanceRecord,
    MaintenanceTicket,
    Tenant,
)
from app.services.document_ingestion import ingest_document
from app.services.rag_cache_service import increment_rag_cache_version
from app.services.redis_service import close_redis, init_redis

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DATA_ROOT = REPO_ROOT / "data" / "demo_tenants"


async def get_or_create_tenant(session, spec: DemoTenantSpec) -> Tenant:
    result = await session.execute(select(Tenant).where(Tenant.name == spec.name))
    tenant = result.scalar_one_or_none()

    if tenant is not None:
        print(f"Reusing tenant: {spec.name} ({tenant.id})")
        return tenant

    tenant = Tenant(name=spec.name)
    session.add(tenant)
    await session.flush()
    print(f"Created tenant: {spec.name} ({tenant.id})")
    return tenant


async def get_or_create_asset(
    session,
    *,
    tenant_id: UUID,
    asset_code: str,
    name: str,
    location: str,
    status: str,
    active_error_code: str | None,
) -> Asset:
    result = await session.execute(
        select(Asset).where(
            Asset.tenant_id == tenant_id,
            Asset.asset_code == asset_code,
        )
    )
    asset = result.scalar_one_or_none()

    if asset is not None:
        asset.name = name
        asset.location = location
        asset.status = status
        asset.active_error_code = active_error_code
        return asset

    asset = Asset(
        tenant_id=tenant_id,
        asset_code=asset_code,
        name=name,
        location=location,
        status=status,
        active_error_code=active_error_code,
    )
    session.add(asset)
    await session.flush()
    return asset


async def add_record_if_missing(
    session,
    *,
    tenant_id: UUID,
    asset_id: UUID,
    maintenance_date: date,
    maintenance_type: str,
    description: str,
    technician: str,
) -> None:
    result = await session.execute(
        select(MaintenanceRecord.id).where(
            MaintenanceRecord.tenant_id == tenant_id,
            MaintenanceRecord.asset_id == asset_id,
            MaintenanceRecord.maintenance_date == maintenance_date,
            MaintenanceRecord.description == description,
        )
    )

    if result.scalar_one_or_none() is not None:
        return

    session.add(
        MaintenanceRecord(
            tenant_id=tenant_id,
            asset_id=asset_id,
            maintenance_date=maintenance_date,
            maintenance_type=maintenance_type,
            description=description,
            technician=technician,
        )
    )


async def add_ticket_if_missing(
    session,
    *,
    tenant_id: UUID,
    asset_id: UUID,
    issue: str,
    priority: str,
    status: str,
) -> None:
    result = await session.execute(
        select(MaintenanceTicket.id).where(
            MaintenanceTicket.tenant_id == tenant_id,
            MaintenanceTicket.asset_id == asset_id,
            MaintenanceTicket.issue == issue,
        )
    )

    if result.scalar_one_or_none() is not None:
        return

    session.add(
        MaintenanceTicket(
            tenant_id=tenant_id,
            asset_id=asset_id,
            issue=issue,
            priority=priority,
            status=status,
        )
    )


async def ingest_demo_document(
    session,
    *,
    tenant_id: UUID,
    source_path: Path,
) -> None:
    filename = source_path.name
    content = source_path.read_bytes()
    checksum = hashlib.sha256(content).hexdigest()

    result = await session.execute(
        select(Document).where(
            Document.tenant_id == tenant_id,
            Document.filename == filename,
        )
    )
    document = result.scalar_one_or_none()

    if document is not None and document.checksum_sha256 == checksum:
        print(f"  skip document (unchanged): {filename}")
        return

    document_id = document.id if document is not None else uuid4()
    storage_dir = Path(settings.document_storage_path) / str(tenant_id) / str(document_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / filename
    file_path.write_bytes(content)

    await ingest_document(
        tenant_id=tenant_id,
        document_id=document_id,
        filename=filename,
        file_path=file_path,
    )

    if document is None:
        document = Document(
            id=document_id,
            tenant_id=tenant_id,
            filename=filename,
            content_type="text/plain",
            file_size_bytes=len(content),
            checksum_sha256=checksum,
            status="indexed",
        )
        session.add(document)
    else:
        document.content_type = "text/plain"
        document.file_size_bytes = len(content)
        document.checksum_sha256 = checksum
        document.status = "indexed"

    await session.flush()
    await increment_rag_cache_version(tenant_id)
    print(f"  indexed document: {filename}")


async def seed_atlas(session, tenant: Tenant) -> None:
    machine_42 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="MACHINE-42",
        name="Hydraulic Press 42",
        location="Assembly Line 2",
        status="warning",
        active_error_code="AX-4317",
    )
    machine_17 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="MACHINE-17",
        name="Assembly Machine 17",
        location="Assembly Line 1",
        status="operational",
        active_error_code=None,
    )
    robot_07 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="ROBOT-07",
        name="Welding Robot 07",
        location="Welding Cell 3",
        status="maintenance",
        active_error_code="RB-2201",
    )
    cnc_11 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="CNC-11",
        name="CNC Milling Center 11",
        location="Machining Area",
        status="warning",
        active_error_code="AX-2204",
    )
    await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="PRESS-05",
        name="Mechanical Press 05",
        location="Stamping Area",
        status="operational",
        active_error_code=None,
    )

    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=machine_42.id,
        maintenance_date=date(2026, 8, 5),
        maintenance_type="corrective",
        description="Hydraulic filter replaced.",
        technician="Technician A",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=machine_42.id,
        maintenance_date=date(2026, 8, 12),
        maintenance_type="inspection",
        description="Pressure sensor calibrated.",
        technician="Technician B",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=machine_42.id,
        maintenance_date=date(2026, 8, 18),
        maintenance_type="inspection",
        description="Hydraulic hose inspected.",
        technician="Technician A",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=robot_07.id,
        maintenance_date=date(2026, 8, 14),
        maintenance_type="inspection",
        description="Joint encoder inspected.",
        technician="Technician D",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=robot_07.id,
        maintenance_date=date(2026, 8, 20),
        maintenance_type="scheduled",
        description="Joint lubrication completed.",
        technician="Technician D",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=cnc_11.id,
        maintenance_date=date(2026, 8, 9),
        maintenance_type="corrective",
        description="Coolant circuit cleaned.",
        technician="Technician C",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=cnc_11.id,
        maintenance_date=date(2026, 8, 16),
        maintenance_type="inspection",
        description="Spindle temperature sensor checked.",
        technician="Technician C",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=machine_17.id,
        maintenance_date=date(2026, 8, 1),
        maintenance_type="scheduled",
        description="Routine scheduled maintenance completed.",
        technician="Technician C",
    )

    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=machine_42.id,
        issue="Hydraulic pressure investigation for MACHINE-42",
        priority="high",
        status="open",
    )
    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=robot_07.id,
        issue="Torque deviation inspection for ROBOT-07",
        priority="medium",
        status="open",
    )
    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=machine_17.id,
        issue="Routine lubrication completed for MACHINE-17",
        priority="low",
        status="closed",
    )


async def seed_borealis(session, tenant: Tenant) -> None:
    chiller_12 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="CHILLER-12",
        name="Main Chiller 12",
        location="Cold Storage Building A",
        status="warning",
        active_error_code="CL-209",
    )
    await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="FREEZER-03",
        name="Freezer Unit 03",
        location="Frozen Zone B",
        status="operational",
        active_error_code=None,
    )
    dock_07 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="DOCK-07",
        name="Loading Dock 07",
        location="Outbound Loading",
        status="maintenance",
        active_error_code="CL-730",
    )
    condenser_04 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="CONDENSER-04",
        name="Condenser Unit 04",
        location="Roof Plant Area",
        status="warning",
        active_error_code="CL-511",
    )
    sensor_hub_02 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="SENSOR-HUB-02",
        name="Temperature Sensor Hub 02",
        location="Chilled Zone",
        status="warning",
        active_error_code="E-100",
    )

    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=chiller_12.id,
        maintenance_date=date(2026, 8, 7),
        maintenance_type="inspection",
        description="Refrigerant pressure inspection completed.",
        technician="Cold Tech A",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=condenser_04.id,
        maintenance_date=date(2026, 8, 11),
        maintenance_type="corrective",
        description="Condenser motor replacement.",
        technician="Cold Tech B",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=dock_07.id,
        maintenance_date=date(2026, 8, 15),
        maintenance_type="corrective",
        description="Dock seal replacement.",
        technician="Facilities Tech",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=sensor_hub_02.id,
        maintenance_date=date(2026, 8, 19),
        maintenance_type="inspection",
        description="Temperature sensor recalibration.",
        technician="Cold Tech A",
    )

    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=chiller_12.id,
        issue="Low suction pressure investigation for CHILLER-12",
        priority="high",
        status="open",
    )
    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=sensor_hub_02.id,
        issue="Evaporator sensor communication failure for SENSOR-HUB-02",
        priority="high",
        status="open",
    )
    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=dock_07.id,
        issue="Thermal seal breach repair for DOCK-07",
        priority="medium",
        status="open",
    )
    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=condenser_04.id,
        issue="Historical condenser fan replacement completed",
        priority="medium",
        status="closed",
    )


async def seed_helios(session, tenant: Tenant) -> None:
    turbine_08 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="TURBINE-08",
        name="Wind Turbine 08",
        location="North Ridge",
        status="warning",
        active_error_code="WT-302",
    )
    await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="TURBINE-03",
        name="Wind Turbine 03",
        location="North Ridge",
        status="operational",
        active_error_code=None,
    )
    inverter_04 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="INVERTER-04",
        name="Power Inverter 04",
        location="Solar Field A",
        status="maintenance",
        active_error_code="INV-604",
    )
    inverter_09 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="INVERTER-09",
        name="Power Inverter 09",
        location="Solar Field B",
        status="warning",
        active_error_code="E-100",
    )
    transformer_02 = await get_or_create_asset(
        session,
        tenant_id=tenant.id,
        asset_code="TRANSFORMER-02",
        name="Transformer 02",
        location="Substation",
        status="operational",
        active_error_code=None,
    )

    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=turbine_08.id,
        maintenance_date=date(2026, 8, 6),
        maintenance_type="inspection",
        description="Yaw drive inspection completed.",
        technician="Field Tech A",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=turbine_08.id,
        maintenance_date=date(2026, 8, 13),
        maintenance_type="inspection",
        description="Gearbox oil sampling completed.",
        technician="Field Tech B",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=inverter_04.id,
        maintenance_date=date(2026, 8, 10),
        maintenance_type="inspection",
        description="Inverter firmware inspection.",
        technician="Electrical Tech",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=inverter_09.id,
        maintenance_date=date(2026, 8, 17),
        maintenance_type="corrective",
        description="Communications gateway restart.",
        technician="Controls Tech",
    )
    await add_record_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=transformer_02.id,
        maintenance_date=date(2026, 8, 21),
        maintenance_type="inspection",
        description="Transformer thermal inspection.",
        technician="Electrical Tech",
    )

    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=turbine_08.id,
        issue="Yaw motor overload investigation for TURBINE-08",
        priority="high",
        status="open",
    )
    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=inverter_09.id,
        issue="Inverter communication timeout for INVERTER-09",
        priority="high",
        status="open",
    )
    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=inverter_04.id,
        issue="DC bus overvoltage safe-state review for INVERTER-04",
        priority="medium",
        status="open",
    )
    await add_ticket_if_missing(
        session,
        tenant_id=tenant.id,
        asset_id=transformer_02.id,
        issue="Quarterly transformer inspection completed",
        priority="low",
        status="closed",
    )


async def get_or_create_company(
    session,
    *,
    tenant_id: UUID,
    internal_customer_id: str,
    company_name: str,
    official_name: str,
    domain: str,
    aliases: str,
    industry: str,
    country: str,
    account_health: str,
    health_score: int,
    last_review_date: date,
) -> Company:
    result = await session.execute(
        select(Company).where(
            Company.tenant_id == tenant_id,
            Company.internal_customer_id == internal_customer_id,
        )
    )
    company = result.scalar_one_or_none()
    if company is not None:
        company.company_name = company_name
        company.official_name = official_name
        company.domain = domain
        company.aliases = aliases
        company.industry = industry
        company.country = country
        company.account_health = account_health
        company.health_score = health_score
        company.last_review_date = last_review_date
        return company

    company = Company(
        tenant_id=tenant_id,
        internal_customer_id=internal_customer_id,
        company_name=company_name,
        official_name=official_name,
        domain=domain,
        aliases=aliases,
        industry=industry,
        country=country,
        account_health=account_health,
        health_score=health_score,
        last_review_date=last_review_date,
    )
    session.add(company)
    await session.flush()
    return company


async def add_revenue_if_missing(
    session,
    *,
    tenant_id: UUID,
    company_id: UUID,
    period_label: str,
    fiscal_year: int,
    amount: Decimal,
    currency: str = "USD",
    metric: str = "annual_revenue",
) -> None:
    result = await session.execute(
        select(CompanyRevenue).where(
            CompanyRevenue.tenant_id == tenant_id,
            CompanyRevenue.company_id == company_id,
            CompanyRevenue.period_label == period_label,
            CompanyRevenue.metric == metric,
        )
    )
    if result.scalar_one_or_none() is not None:
        return
    session.add(
        CompanyRevenue(
            tenant_id=tenant_id,
            company_id=company_id,
            period_label=period_label,
            fiscal_year=fiscal_year,
            currency=currency,
            amount=amount,
            metric=metric,
        )
    )


async def add_transaction_if_missing(
    session,
    *,
    tenant_id: UUID,
    company_id: UUID,
    reference: str,
    txn_date: date,
    amount: Decimal,
    txn_type: str,
    status: str,
    currency: str = "USD",
) -> None:
    result = await session.execute(
        select(CompanyTransaction).where(
            CompanyTransaction.tenant_id == tenant_id,
            CompanyTransaction.reference == reference,
        )
    )
    if result.scalar_one_or_none() is not None:
        return
    session.add(
        CompanyTransaction(
            tenant_id=tenant_id,
            company_id=company_id,
            txn_date=txn_date,
            amount=amount,
            currency=currency,
            txn_type=txn_type,
            status=status,
            reference=reference,
        )
    )


async def add_payment_if_missing(
    session,
    *,
    tenant_id: UUID,
    company_id: UUID,
    reference: str,
    payment_date: date,
    amount: Decimal,
    method: str,
    status: str,
    currency: str = "USD",
) -> None:
    result = await session.execute(
        select(CompanyPayment).where(
            CompanyPayment.tenant_id == tenant_id,
            CompanyPayment.reference == reference,
        )
    )
    if result.scalar_one_or_none() is not None:
        return
    session.add(
        CompanyPayment(
            tenant_id=tenant_id,
            company_id=company_id,
            payment_date=payment_date,
            amount=amount,
            currency=currency,
            method=method,
            status=status,
            reference=reference,
        )
    )


async def seed_northstar(session, tenant: Tenant) -> None:
    """Synthetic commercial portfolio for real public company entities."""

    portfolio = [
        {
            "internal_customer_id": "CUST-SPOTIFY",
            "company_name": "Spotify",
            "official_name": "Spotify AB",
            "domain": "spotify.com",
            "aliases": "Spotify Inc,Spotify Technology",
            "industry": "Streaming media",
            "country": "Sweden",
            "account_health": "healthy",
            "health_score": 88,
            "last_review_date": date(2025, 11, 12),
            "revenue": Decimal("14500000.00"),
            "txn_amount": Decimal("1250000.00"),
            "payment_amount": Decimal("1250000.00"),
            "payment_status": "completed",
        },
        {
            "internal_customer_id": "CUST-SIEMENS",
            "company_name": "Siemens",
            "official_name": "Siemens AG",
            "domain": "siemens.com",
            "aliases": "Siemens AG,Siemens Industry",
            "industry": "Industrial technology",
            "country": "Germany",
            "account_health": "watch",
            "health_score": 68,
            "last_review_date": date(2025, 10, 3),
            "revenue": Decimal("9200000.00"),
            "txn_amount": Decimal("980000.00"),
            "payment_amount": Decimal("720000.00"),
            "payment_status": "partial",
        },
        {
            "internal_customer_id": "CUST-SHOPIFY",
            "company_name": "Shopify",
            "official_name": "Shopify Inc.",
            "domain": "shopify.com",
            "aliases": "Shopify Inc",
            "industry": "E-commerce platform",
            "country": "Canada",
            "account_health": "healthy",
            "health_score": 91,
            "last_review_date": date(2025, 12, 1),
            "revenue": Decimal("7800000.00"),
            "txn_amount": Decimal("650000.00"),
            "payment_amount": Decimal("650000.00"),
            "payment_status": "completed",
        },
        {
            "internal_customer_id": "CUST-ADOBE",
            "company_name": "Adobe",
            "official_name": "Adobe Inc.",
            "domain": "adobe.com",
            "aliases": "Adobe Systems,Adobe Inc",
            "industry": "Creative software",
            "country": "United States",
            "account_health": "healthy",
            "health_score": 84,
            "last_review_date": date(2025, 9, 18),
            "revenue": Decimal("11200000.00"),
            "txn_amount": Decimal("900000.00"),
            "payment_amount": Decimal("900000.00"),
            "payment_status": "completed",
        },
        {
            "internal_customer_id": "CUST-MICROSOFT",
            "company_name": "Microsoft",
            "official_name": "Microsoft Corporation",
            "domain": "microsoft.com",
            "aliases": "MSFT,Microsoft Corp",
            "industry": "Enterprise software",
            "country": "United States",
            "account_health": "at_risk",
            "health_score": 42,
            "last_review_date": date(2025, 8, 22),
            "revenue": Decimal("22100000.00"),
            "txn_amount": Decimal("2100000.00"),
            "payment_amount": Decimal("900000.00"),
            "payment_status": "late",
        },
    ]

    for item in portfolio:
        company = await get_or_create_company(
            session,
            tenant_id=tenant.id,
            internal_customer_id=item["internal_customer_id"],
            company_name=item["company_name"],
            official_name=item["official_name"],
            domain=item["domain"],
            aliases=item["aliases"],
            industry=item["industry"],
            country=item["country"],
            account_health=item["account_health"],
            health_score=item["health_score"],
            last_review_date=item["last_review_date"],
        )
        await add_revenue_if_missing(
            session,
            tenant_id=tenant.id,
            company_id=company.id,
            period_label="2025",
            fiscal_year=2025,
            amount=item["revenue"],
        )
        await add_transaction_if_missing(
            session,
            tenant_id=tenant.id,
            company_id=company.id,
            reference=f"INV-{item['internal_customer_id']}-2025-01",
            txn_date=date(2025, 1, 15),
            amount=item["txn_amount"],
            txn_type="invoice",
            status="open" if item["payment_status"] != "completed" else "paid",
        )
        await add_payment_if_missing(
            session,
            tenant_id=tenant.id,
            company_id=company.id,
            reference=f"PAY-{item['internal_customer_id']}-2025-01",
            payment_date=date(2025, 2, 10),
            amount=item["payment_amount"],
            method="wire",
            status=item["payment_status"],
        )


SEEDERS = {
    "atlas-manufacturing": seed_atlas,
    "borealis-cold-chain": seed_borealis,
    "helios-energy-services": seed_helios,
    "northstar-commercial": seed_northstar,
}


async def main() -> None:
    if not DEMO_DATA_ROOT.exists():
        raise SystemExit(f"Demo data directory not found: {DEMO_DATA_ROOT}")

    await init_redis()

    try:
        async with SessionLocal() as session:
            for spec in DEMO_TENANTS:
                print(f"\n=== {spec.name} ===")
                tenant = await get_or_create_tenant(session, spec)
                await SEEDERS[spec.slug](session, tenant)

                docs_dir = DEMO_DATA_ROOT / spec.slug
                document_paths = sorted(docs_dir.glob("*.txt"))

                if not document_paths:
                    print(f"  warning: no documents in {docs_dir}")

                for path in document_paths:
                    await ingest_demo_document(
                        session,
                        tenant_id=tenant.id,
                        source_path=path,
                    )

            await session.commit()
            print("\nDemo playground seed completed.")
    finally:
        await close_redis()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
