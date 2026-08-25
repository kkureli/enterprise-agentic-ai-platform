import asyncio

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters


async def main():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()

            print("TOOLS:")
            for tool in tools.tools:
                print(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                )

            result = await session.call_tool(
                "get_asset_status",
                arguments={
                    "asset_id": "MACHINE-42",
                    "tenant_slug": "atlas-manufacturing",
                },
            )

            print("\nTOOL RESULT:")
            print(result.structured_content)


asyncio.run(main())
