from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.asset import Asset
from app.models.maintenance_record import MaintenanceRecord
from app.models.maintenance_ticket import MaintenanceTicket
from app.models.tenant import Tenant
from app.schemas.operations import (
    AssetRead,
    MaintenanceRecordRead,
    MaintenanceTicketRead,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}",
    tags=["Operations"],
)


async def _require_tenant(
    db: AsyncSession,
    tenant_id: UUID,
) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    return tenant


@router.get(
    "/assets",
    response_model=list[AssetRead],
)
async def list_assets(
    tenant_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Asset]:
    await _require_tenant(db, tenant_id)

    result = await db.execute(
        select(Asset).where(Asset.tenant_id == tenant_id).order_by(Asset.asset_code.asc())
    )

    return list(result.scalars().all())


@router.get(
    "/maintenance-records",
    response_model=list[MaintenanceRecordRead],
)
async def list_maintenance_records(
    tenant_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MaintenanceRecordRead]:
    await _require_tenant(db, tenant_id)

    result = await db.execute(
        select(MaintenanceRecord)
        .options(selectinload(MaintenanceRecord.asset))
        .where(MaintenanceRecord.tenant_id == tenant_id)
        .order_by(
            MaintenanceRecord.maintenance_date.desc(),
            MaintenanceRecord.created_at.desc(),
        )
    )

    records = result.scalars().all()

    return [
        MaintenanceRecordRead(
            id=record.id,
            tenant_id=record.tenant_id,
            asset_id=record.asset_id,
            asset_code=record.asset.asset_code if record.asset else None,
            maintenance_date=record.maintenance_date,
            maintenance_type=record.maintenance_type,
            description=record.description,
            technician=record.technician,
            created_at=record.created_at,
        )
        for record in records
    ]


@router.get(
    "/maintenance-tickets",
    response_model=list[MaintenanceTicketRead],
)
async def list_maintenance_tickets(
    tenant_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MaintenanceTicketRead]:
    await _require_tenant(db, tenant_id)

    result = await db.execute(
        select(MaintenanceTicket)
        .options(selectinload(MaintenanceTicket.asset))
        .where(MaintenanceTicket.tenant_id == tenant_id)
        .order_by(
            MaintenanceTicket.created_at.desc(),
        )
    )

    tickets = result.scalars().all()

    return [
        MaintenanceTicketRead(
            id=ticket.id,
            tenant_id=ticket.tenant_id,
            asset_id=ticket.asset_id,
            asset_code=ticket.asset.asset_code if ticket.asset else None,
            issue=ticket.issue,
            priority=ticket.priority,
            status=ticket.status,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )
        for ticket in tickets
    ]
