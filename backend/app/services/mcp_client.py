from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.core.config import settings


def get_mcp_server_dir() -> Path:
    if settings.mcp_server_dir:
        return Path(settings.mcp_server_dir)

    # Monorepo layout: <repo>/mcp relative to backend/app/services/
    monorepo_mcp = Path(__file__).resolve().parents[3] / "mcp"
    # Container layout: /app/mcp next to the packaged app/
    packaged_mcp = Path(__file__).resolve().parents[2] / "mcp"

    for candidate in (monorepo_mcp, packaged_mcp):
        if candidate.is_dir():
            return candidate

    return monorepo_mcp


@asynccontextmanager
async def maintenance_mcp_session():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "server.py"],
        cwd=str(get_mcp_server_dir()),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def list_maintenance_tools():
    async with maintenance_mcp_session() as session:
        return await session.list_tools()


async def call_maintenance_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    tenant_slug: str | None = None,
):
    """Invoke an MCP tool, injecting tenant_slug for tenant-scoped demo data."""

    payload = dict(arguments or {})
    if tenant_slug:
        payload["tenant_slug"] = tenant_slug
    if not payload.get("tenant_slug"):
        raise ValueError("tenant_slug is required for MCP tool calls.")

    async with maintenance_mcp_session() as session:
        return await session.call_tool(
            name,
            payload,
        )
