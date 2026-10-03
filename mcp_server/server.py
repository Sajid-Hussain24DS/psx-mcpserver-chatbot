import logging
import sys

from fastmcp import FastMCP
import os
try:
    from mcp_server.api_client import request_psx_api
except ModuleNotFoundError:
    from api_client import request_psx_api

from starlette.requests import Request
from starlette.responses import JSONResponse

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

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request):
    return JSONResponse(
        {
            "status": "healthy",
            "service": "PSX MCP Server",
        }
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
# TOOL 4 — GET STOCK BY SYMBOL
# =========================================================

@mcp.tool(
    description=(
        "Look up a specific PSX stock by its symbol. "
        "Use this when the user asks about an individual "
        "stock such as HBL, OGDC, MEBL, LUCK, etc. "
        "Returns the stock's available PSX data including "
        "current price, change, volume, market cap, and industry."
    )
)
async def get_stock_by_symbol(
    symbol: str,
) -> dict:

    symbol = symbol.strip().upper()

    log(
        "get_stock_by_symbol",
        "started",
        symbol=symbol,
    )

    # First verify that the symbol exists
    symbols_result = await request_psx_api(
        "/symbols"
    )

    symbols_data = symbols_result.get(
        "data",
        [],
    )

    available_symbols = {
        str(item.get("symbol", "")).strip().upper()
        for item in symbols_data
        if isinstance(item, dict)
    }

    if symbol not in available_symbols:
        return {
            "found": False,
            "symbol": symbol,
            "message": (
                f"{symbol} is not available in "
                "the current PSX symbol data."
            ),
        }

    # Get available industries
    industries_result = await request_psx_api(
        "/industries"
    )

    industries_data = industries_result.get(
        "data",
        [],
    )

    # Search the verified symbol across industries
    for item in industries_data:

        if isinstance(item, str):
            industry = item

        elif isinstance(item, dict):
            industry = (
                item.get("industry")
                or item.get("name")
                or item.get("sector")
            )

        else:
            continue

        if not industry:
            continue

        try:
            stocks_result = await request_psx_api(
                "/stocks",
                params={
                    "industry": industry,
                },
            )

            stocks = stocks_result.get(
                "data",
                [],
            )

            for stock in stocks:

                if not isinstance(stock, dict):
                    continue

                stock_symbol = str(
                    stock.get("symbol", "")
                ).strip().upper()

                if stock_symbol == symbol:

                    log(
                        "get_stock_by_symbol",
                        "success",
                        symbol=symbol,
                        industry=industry,
                    )

                    return {
                        "found": True,
                        "symbol": symbol,
                        "industry": industry,
                        "data": stock,
                    }

        except Exception as exc:

            log(
                "get_stock_by_symbol",
                "industry_error",
                symbol=symbol,
                industry=industry,
                error=str(exc),
            )

            continue

    log(
        "get_stock_by_symbol",
        "not_found",
        symbol=symbol,
    )

    return {
        "found": False,
        "symbol": symbol,
        "message": (
            f"{symbol} exists in the PSX symbol list, "
            "but its financial data could not be found "
            "in the available industry data."
        ),
    }
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
    port=int(os.getenv("PORT", "5173")),
    path="/mcp",
)