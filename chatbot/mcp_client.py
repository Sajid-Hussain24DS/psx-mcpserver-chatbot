import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv(override=True)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
print("MCP URL IN USE:", repr(MCP_SERVER_URL))

HORIZON_API_KEY = os.getenv("HORIZON_API_KEY")


@asynccontextmanager
async def mcp_session() -> AsyncIterator[ClientSession]:
    if not MCP_SERVER_URL:
        raise RuntimeError("MCP_SERVER_URL is not configured.")

    headers = {}
    if HORIZON_API_KEY:
        headers["Authorization"] = f"Bearer {HORIZON_API_KEY}"

    timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)

    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as http_client:
        
        async with streamable_http_client(
            MCP_SERVER_URL,
            http_client=http_client,
        ) as (read_stream, write_stream, *_):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session