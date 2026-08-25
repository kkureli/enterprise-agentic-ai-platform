from mcp.server import MCPServer
from pydantic import BaseModel


class AssetStatus(BaseModel):
    asset_id: str
    status: str
    location: str | None
    active_error_code: str | None
    tenant_slug: str


class MaintenanceRecord(BaseModel):
    date: str
    description: str
    technician: str


class MaintenanceHistory(BaseModel):
    asset_id: str
    records: list[MaintenanceRecord]
    tenant_slug: str


class MaintenanceTicket(BaseModel):
    ticket_id: str
    asset_code: str
    issue: str
    priority: str
    status: str


# Demo MCP data is explicitly keyed by tenant slug so reads cannot cross tenants.
TENANT_ASSETS: dict[str, dict[str, AssetStatus]] = {
    "atlas-manufacturing": {
        "MACHINE-42": AssetStatus(
            asset_id="MACHINE-42",
            status="warning",
            location="Assembly Line 2",
            active_error_code="AX-4317",
            tenant_slug="atlas-manufacturing",
        ),
        "MACHINE-17": AssetStatus(
            asset_id="MACHINE-17",
            status="operational",
            location="Assembly Line 1",
            active_error_code=None,
            tenant_slug="atlas-manufacturing",
        ),
    },
    "borealis-cold-chain": {
        "CHILLER-12": AssetStatus(
            asset_id="CHILLER-12",
            status="warning",
            location="Cold Storage Building A",
            active_error_code="CL-209",
            tenant_slug="borealis-cold-chain",
        ),
        "FREEZER-03": AssetStatus(
            asset_id="FREEZER-03",
            status="operational",
            location="Frozen Zone B",
            active_error_code=None,
            tenant_slug="borealis-cold-chain",
        ),
    },
    "helios-energy-services": {
        "TURBINE-08": AssetStatus(
            asset_id="TURBINE-08",
            status="warning",
            location="Wind Ridge Pad 8",
            active_error_code="WT-302",
            tenant_slug="helios-energy-services",
        ),
    },
}

TENANT_HISTORIES: dict[str, dict[str, MaintenanceHistory]] = {
    "atlas-manufacturing": {
        "MACHINE-42": MaintenanceHistory(
            asset_id="MACHINE-42",
            tenant_slug="atlas-manufacturing",
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
            tenant_slug="atlas-manufacturing",
            records=[
                MaintenanceRecord(
                    date="2026-08-01",
                    description="Routine scheduled maintenance completed.",
                    technician="Technician C",
                ),
            ],
        ),
    },
    "borealis-cold-chain": {
        "CHILLER-12": MaintenanceHistory(
            asset_id="CHILLER-12",
            tenant_slug="borealis-cold-chain",
            records=[
                MaintenanceRecord(
                    date="2026-08-07",
                    description="Refrigerant pressure inspection completed.",
                    technician="Cold Tech A",
                ),
            ],
        ),
    },
    "helios-energy-services": {
        "TURBINE-08": MaintenanceHistory(
            asset_id="TURBINE-08",
            tenant_slug="helios-energy-services",
            records=[
                MaintenanceRecord(
                    date="2026-08-12",
                    description="Yaw motor inspection completed.",
                    technician="Field Tech A",
                ),
            ],
        ),
    },
}

mcp = MCPServer("Enterprise Maintenance Tools")

READ_TOOLS = frozenset({"get_asset_status", "get_maintenance_history"})
WRITE_TOOLS = frozenset({"create_maintenance_ticket"})


def _require_tenant_slug(tenant_slug: str | None) -> str:
    if not tenant_slug or not str(tenant_slug).strip():
        raise ValueError("tenant_slug is required for tenant-scoped MCP tools.")
    return str(tenant_slug).strip()


@mcp.tool()
def create_maintenance_ticket(
    asset_code: str,
    issue: str,
    priority: str,
    tenant_slug: str | None = None,
) -> MaintenanceTicket:
    """
    Request creation of a maintenance ticket.

    This write action must be approved and executed by the host
    application through the HITL workflow. tenant_slug is required by the host.
    """

    _require_tenant_slug(tenant_slug)
    raise RuntimeError(
        "This write action must be executed through the approved HITL workflow."
    )


@mcp.tool()
def get_asset_status(asset_id: str, tenant_slug: str | None = None) -> AssetStatus:
    """Return the current operational status of an enterprise asset for one tenant."""

    slug = _require_tenant_slug(tenant_slug)
    assets = TENANT_ASSETS.get(slug, {})
    found = assets.get(asset_id)
    if found is not None:
        return found

    return AssetStatus(
        asset_id=asset_id,
        status="unknown",
        location=None,
        active_error_code=None,
        tenant_slug=slug,
    )


@mcp.tool()
def get_maintenance_history(
    asset_id: str,
    tenant_slug: str | None = None,
) -> MaintenanceHistory:
    """Return the maintenance history for an enterprise asset for one tenant."""

    slug = _require_tenant_slug(tenant_slug)
    histories = TENANT_HISTORIES.get(slug, {})
    found = histories.get(asset_id)
    if found is not None:
        return found

    return MaintenanceHistory(asset_id=asset_id, records=[], tenant_slug=slug)


if __name__ == "__main__":
    mcp.run()
