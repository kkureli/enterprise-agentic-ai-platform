from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Asset, MaintenanceTicket


class AssetNotFoundError(ValueError):
    pass


class InvalidTicketPriorityError(ValueError):
    pass


ALLOWED_PRIORITIES = {
    "low",
    "medium",
    "high",
}


async def create_maintenance_ticket(
    tenant_id: UUID,
    asset_code: str,
    issue: str,
    priority: str,
) -> MaintenanceTicket:
    normalized_priority = priority.lower().strip()

    if normalized_priority not in ALLOWED_PRIORITIES:
        raise InvalidTicketPriorityError(f"Invalid ticket priority: {priority}")

    async with SessionLocal() as session:
        asset = await session.scalar(
            select(Asset).where(
                Asset.tenant_id == tenant_id,
                Asset.asset_code == asset_code,
            )
        )

        if asset is None:
            raise AssetNotFoundError(f"Asset not found: {asset_code}")

        ticket = MaintenanceTicket(
            tenant_id=tenant_id,
            asset_id=asset.id,
            issue=issue,
            priority=normalized_priority,
            status="open",
        )

        session.add(ticket)

        await session.commit()
        await session.refresh(ticket)

        return ticket
