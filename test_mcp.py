import asyncio
import os

import httpx
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

MCP_URL = os.getenv(
    "MCP_SERVER_URL",
    "https://fluttering-blue-ox.fastmcp.app/mcp",
)

HORIZON_API_KEY = os.getenv("HORIZON_API_KEY")


async def main():
    if not HORIZON_API_KEY:
        raise RuntimeError(
            "HORIZON_API_KEY is missing. Add it to your .env file."
        )

    print(f"Connecting to: {MCP_URL}")

    headers = {
        "Authorization": f"Bearer {HORIZON_API_KEY}",
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=httpx.Timeout(30.0, read=300.0),
    ) as http_client:

        async with streamable_http_client(
            MCP_URL,
            http_client=http_client,
        ) as (read_stream, write_stream):

            print("HTTP connection established")

            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:

                print("Initializing MCP session...")

                await session.initialize()

                print("MCP session initialized")

                tools = await session.list_tools()

                print("\nAvailable tools:")

                for tool in tools.tools:
                    print("-", tool.name)

                print("\nCalling get_symbols...")

                result = await session.call_tool(
                    "get_symbols",
                    arguments={},
                )

                print("\nRESULT:")
                print(result)


if __name__ == "__main__":
    asyncio.run(main())