from typing import Any
from uuid import UUID

from app.services.maintenance_ticket_service import (
    create_maintenance_ticket,
)

APPROVED_WRITE_ACTIONS = {
    "create_maintenance_ticket",
}


class UnsupportedApprovedActionError(ValueError):
    pass


async def execute_approved_action(
    tenant_id: UUID,
    pending_action: dict[str, Any],
) -> dict[str, Any]:
    tool_name = pending_action.get("tool_name")
    arguments = pending_action.get("arguments")

    if tool_name not in APPROVED_WRITE_ACTIONS:
        raise UnsupportedApprovedActionError(f"Approved action is not allowed: {tool_name}")

    if not isinstance(arguments, dict):
        raise ValueError("Pending action arguments are invalid.")

    if tool_name == "create_maintenance_ticket":
        ticket = await create_maintenance_ticket(
            tenant_id=tenant_id,
            asset_code=arguments["asset_code"],
            issue=arguments["issue"],
            priority=arguments["priority"],
        )

        return {
            "tool_name": tool_name,
            "ticket_id": str(ticket.id),
            "asset_id": str(ticket.asset_id),
            "issue": ticket.issue,
            "priority": ticket.priority,
            "status": ticket.status,
        }

    raise UnsupportedApprovedActionError(f"No executor implemented for action: {tool_name}")
