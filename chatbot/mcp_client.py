from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv()
MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "https://sore-tan-dove.fastmcp.app/mcp",
)

HORIZON_API_KEY = os.getenv("HORIZON_API_KEY")


@asynccontextmanager
async def mcp_session() -> AsyncIterator[ClientSession]:
    """
    Create an authenticated MCP session with Horizon.
    """

    if not HORIZON_API_KEY:
        raise RuntimeError(
            "HORIZON_API_KEY is not configured."
        )

    headers = {
        "Authorization": f"Bearer {HORIZON_API_KEY}",
    }

    timeout = httpx.Timeout(
        connect=30.0,
        read=300.0,
        write=30.0,
        pool=30.0,
    )

    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
    ) as http_client:

        async with streamable_http_client(
            MCP_SERVER_URL,
            http_client=http_client,
        ) as (read_stream, write_stream):

            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:

                await session.initialize()

                yield session