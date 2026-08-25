import asyncio
from datetime import date

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import (
    Asset,
    Document,
    MaintenanceRecord,
    MaintenanceTicket,
    Tenant,
)

DEMO_TENANT_NAME = "Enterprise Demo"


async def get_target_tenant_id(session):
    # First, reuse our deterministic demo tenant if it already exists.
    result = await session.execute(select(Tenant.id).where(Tenant.name == DEMO_TENANT_NAME))
    tenant_id = result.scalar_one_or_none()

    if tenant_id is not None:
        return tenant_id

    # Preserve the previous behavior for an existing database:
    # use the tenant that owns the most documents.
    result = await session.execute(
        select(Tenant.id)
        .outerjoin(Document, Document.tenant_id == Tenant.id)
        .group_by(Tenant.id)
        .order_by(func.count(Document.id).desc())
        .limit(1)
    )
    tenant_id = result.scalar_one_or_none()

    if tenant_id is not None:
        return tenant_id

    # Completely empty database: create a demo tenant.
    tenant = Tenant(name=DEMO_TENANT_NAME)
    session.add(tenant)
    await session.flush()

    print(f"Created demo tenant: {tenant.id}")

    return tenant.id


async def get_or_create_asset(
    session,
    *,
    tenant_id,
    asset_code,
    name,
    location,
    status,
    active_error_code,
):
    result = await session.execute(
        select(Asset).where(
            Asset.tenant_id == tenant_id,
            Asset.asset_code == asset_code,
        )
    )
    asset = result.scalar_one_or_none()

    if asset is not None:
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
    tenant_id,
    asset_id,
    maintenance_date,
    maintenance_type,
    description,
    technician,
):
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
    tenant_id,
    asset_id,
    issue,
    priority,
    status,
):
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


async def main():
    async with SessionLocal() as session:
        tenant_id = await get_target_tenant_id(session)

        machine_42 = await get_or_create_asset(
            session,
            tenant_id=tenant_id,
            asset_code="MACHINE-42",
            name="Hydraulic Press 42",
            location="Assembly Line 2",
            status="warning",
            active_error_code="AX-4317",
        )

        machine_17 = await get_or_create_asset(
            session,
            tenant_id=tenant_id,
            asset_code="MACHINE-17",
            name="Assembly Machine 17",
            location="Assembly Line 1",
            status="operational",
            active_error_code=None,
        )

        robot_07 = await get_or_create_asset(
            session,
            tenant_id=tenant_id,
            asset_code="ROBOT-07",
            name="Welding Robot 07",
            location="Assembly Line 3",
            status="maintenance",
            active_error_code="RB-2201",
        )

        await add_record_if_missing(
            session,
            tenant_id=tenant_id,
            asset_id=machine_42.id,
            maintenance_date=date(2026, 8, 10),
            maintenance_type="inspection",
            description="Hydraulic pressure sensor inspected.",
            technician="Technician A",
        )

        await add_record_if_missing(
            session,
            tenant_id=tenant_id,
            asset_id=machine_42.id,
            maintenance_date=date(2026, 8, 18),
            maintenance_type="corrective",
            description="Hydraulic fluid level checked and adjusted.",
            technician="Technician B",
        )

        await add_record_if_missing(
            session,
            tenant_id=tenant_id,
            asset_id=machine_17.id,
            maintenance_date=date(2026, 8, 1),
            maintenance_type="scheduled",
            description="Routine scheduled maintenance completed.",
            technician="Technician C",
        )

        await add_record_if_missing(
            session,
            tenant_id=tenant_id,
            asset_id=robot_07.id,
            maintenance_date=date(2026, 8, 20),
            maintenance_type="corrective",
            description="Welding arm calibration performed.",
            technician="Technician D",
        )

        await add_ticket_if_missing(
            session,
            tenant_id=tenant_id,
            asset_id=machine_42.id,
            issue="Hydraulic pressure loss",
            priority="high",
            status="open",
        )

        await add_ticket_if_missing(
            session,
            tenant_id=tenant_id,
            asset_id=machine_42.id,
            issue="Pressure sensor requires inspection",
            priority="medium",
            status="open",
        )

        await add_ticket_if_missing(
            session,
            tenant_id=tenant_id,
            asset_id=machine_17.id,
            issue="Routine lubrication required",
            priority="low",
            status="closed",
        )

        await add_ticket_if_missing(
            session,
            tenant_id=tenant_id,
            asset_id=robot_07.id,
            issue="Welding arm calibration fault",
            priority="high",
            status="open",
        )

        await session.commit()

        print(f"Operational seed completed for tenant: {tenant_id}")


if __name__ == "__main__":
    asyncio.run(main())
