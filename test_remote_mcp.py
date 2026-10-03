
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = "http://127.0.0.1:5173/mcp"


async def main():
    print(f"Testing: {MCP_URL}\n")

    async with streamable_http_client(MCP_URL) as (
    read_stream,
    write_stream,
):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            print("MCP connected successfully.\n")

            tools = await session.list_tools()

            print("Available tools:")
            for tool in tools.tools:
                print(f" - {tool.name}")

            print("\nTesting get_stock_by_symbol('HBL')...\n")

            result = await session.call_tool(
                "get_stock_by_symbol",
                {"symbol": "HBL"},
            )

            print("RESULT:")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())

