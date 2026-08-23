from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MCP_SERVER_DIR = Path(__file__).resolve().parents[3] / "mcp"


@asynccontextmanager
async def maintenance_mcp_session():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "server.py"],
        cwd=str(MCP_SERVER_DIR),
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
):
    async with maintenance_mcp_session() as session:
        return await session.call_tool(
            name,
            arguments=arguments,
        )
