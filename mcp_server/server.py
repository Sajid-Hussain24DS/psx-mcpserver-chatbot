import logging
import sys

from fastmcp import FastMCP

from .api_client import request_psx_api


# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "[%(levelname)s] "
        "%(message)s"
    ),
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
)


logger = logging.getLogger(
    "psx_mcp_server"
)


def log(
    method: str,
    status: str,
    **data,
):
    logger.info(
        f"method={method} "
        f"status={status} "
        f"data={data}"
    )


# =========================================================
# FastMCP Server
# =========================================================

mcp = FastMCP(
    "PSX MCP Server"
)


# =========================================================
# TOOL 1 — GET SYMBOLS
# =========================================================

@mcp.tool(
    description=(
        "Get the list of available "
        "PSX stock symbols."
    )
)
async def get_symbols() -> dict:

    log(
        "get_symbols",
        "started",
    )

    return await request_psx_api(
        "/symbols"
    )


# =========================================================
# TOOL 2 — GET INDUSTRIES
# =========================================================

@mcp.tool(
    description=(
        "Get the list of available "
        "PSX industries."
    )
)
async def get_industries() -> dict:

    log(
        "get_industries",
        "started",
    )

    return await request_psx_api(
        "/industries"
    )


# =========================================================
# TOOL 3 — GET STOCKS BY INDUSTRY
# =========================================================

@mcp.tool(
    description=(
        "Get all PSX stocks belonging "
        "to a specific industry."
    )
)
async def get_stocks(
    industry: str,
) -> dict:

    log(
        "get_stocks",
        "started",
        industry=industry,
    )

    return await request_psx_api(
        "/stocks",
        params={
            "industry": industry,
        },
    )


# =========================================================
# TOOL 4 — TOP 10 BY CHANGE
# =========================================================

@mcp.tool(
    description=(
        "Get the top 10 PSX stocks "
        "by change percentage."
    )
)
async def get_top_change(
    industry: str | None = None,
) -> dict:

    log(
        "get_top_change",
        "started",
        industry=industry,
    )

    params = {}

    if industry:
        params["industry"] = industry

    return await request_psx_api(
        "/stocks/change/top",
        params=params,
    )


# =========================================================
# TOOL 5 — BOTTOM 10 BY CHANGE
# =========================================================

@mcp.tool(
    description=(
        "Get the bottom 10 PSX stocks "
        "by change percentage."
    )
)
async def get_bottom_change(
    industry: str | None = None,
) -> dict:

    log(
        "get_bottom_change",
        "started",
        industry=industry,
    )

    params = {}

    if industry:
        params["industry"] = industry

    return await request_psx_api(
        "/stocks/change/bottom",
        params=params,
    )


# =========================================================
# TOOL 6 — TOP 10 BY VOLUME
# =========================================================

@mcp.tool(
    description=(
        "Get the top 10 PSX stocks "
        "by trading volume."
    )
)
async def get_top_volume(
    industry: str | None = None,
) -> dict:

    log(
        "get_top_volume",
        "started",
        industry=industry,
    )

    params = {}

    if industry:
        params["industry"] = industry

    return await request_psx_api(
        "/stocks/volume/top",
        params=params,
    )


# =========================================================
# TOOL 7 — BOTTOM 10 BY VOLUME
# =========================================================

@mcp.tool(
    description=(
        "Get the bottom 10 PSX stocks "
        "by trading volume."
    )
)
async def get_bottom_volume(
    industry: str | None = None,
) -> dict:

    log(
        "get_bottom_volume",
        "started",
        industry=industry,
    )

    params = {}

    if industry:
        params["industry"] = industry

    return await request_psx_api(
        "/stocks/volume/bottom",
        params=params,
    )


# =========================================================
# Run Server
# =========================================================

if __name__ == "__main__":

    log(
        "system",
        "starting_server",
        server="PSX MCP Server",
        transport="streamable-http",
    )

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=5173,
        path="/mcp",
    )