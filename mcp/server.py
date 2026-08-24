from mcp.server import MCPServer
from pydantic import BaseModel


class AssetStatus(BaseModel):
    asset_id: str
    status: str
    location: str | None
    active_error_code: str | None


class MaintenanceRecord(BaseModel):
    date: str
    description: str
    technician: str


class MaintenanceHistory(BaseModel):
    asset_id: str
    records: list[MaintenanceRecord]


class MaintenanceTicket(BaseModel):
    ticket_id: str
    asset_code: str
    issue: str
    priority: str
    status: str


mcp = MCPServer("Enterprise Maintenance Tools")


@mcp.tool()
def create_maintenance_ticket(
    asset_code: str,
    issue: str,
    priority: str,
) -> MaintenanceTicket:
    """
    Request creation of a maintenance ticket.

    This write action must be approved and executed by the host
    application through the HITL workflow.
    """

    raise RuntimeError(
        "This write action must be executed through the approved HITL workflow."
    )


@mcp.tool()
def get_asset_status(asset_id: str) -> AssetStatus:
    """Return the current operational status of an enterprise asset."""

    assets = {
        "MACHINE-42": AssetStatus(
            asset_id="MACHINE-42",
            status="warning",
            location="Assembly Line 2",
            active_error_code="AX-4317",
        ),
        "MACHINE-17": AssetStatus(
            asset_id="MACHINE-17",
            status="operational",
            location="Assembly Line 1",
            active_error_code=None,
        ),
    }

    return assets.get(
        asset_id,
        AssetStatus(
            asset_id=asset_id,
            status="unknown",
            location=None,
            active_error_code=None,
        ),
    )


@mcp.tool()
def get_maintenance_history(asset_id: str) -> MaintenanceHistory:
    """Return the maintenance history for an enterprise asset."""

    histories = {
        "MACHINE-42": MaintenanceHistory(
            asset_id="MACHINE-42",
            records=[
                MaintenanceRecord(
                    date="2026-08-10",
                    description="Hydraulic pressure sensor inspected.",
                    technician="Technician A",
                ),
                MaintenanceRecord(
                    date="2026-07-22",
                    description="Hydraulic fluid level checked.",
                    technician="Technician B",
                ),
            ],
        ),
        "MACHINE-17": MaintenanceHistory(
            asset_id="MACHINE-17",
            records=[
                MaintenanceRecord(
                    date="2026-08-01",
                    description="Routine scheduled maintenance completed.",
                    technician="Technician C",
                ),
            ],
        ),
    }

    return histories.get(
        asset_id,
        MaintenanceHistory(
            asset_id=asset_id,
            records=[],
        ),
    )


if __name__ == "__main__":
    mcp.run()
