import logging
import os

import httpx
from dotenv import load_dotenv


# =========================================================
# Load environment
# =========================================================

load_dotenv()


# =========================================================
# Logger
# =========================================================

logger = logging.getLogger(
    "psx_mcp_server"
)


# =========================================================
# PSX API URL
# =========================================================

PSX_API_URL = os.getenv(
    "PSX_API_URL"
)


if not PSX_API_URL:

    raise RuntimeError(
        "PSX_API_URL is not configured "
        "in the environment."
    )


PSX_API_URL = PSX_API_URL.rstrip("/")


# =========================================================
# Logging helper
# =========================================================

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
# PSX API Request
# =========================================================

async def request_psx_api(
    endpoint: str,
    params: dict | None = None,
) -> dict:

    url = (
        f"{PSX_API_URL}{endpoint}"
    )

    try:

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.get(
                url,
                params=params,
            )

            response.raise_for_status()

            data = response.json()

            log(
                endpoint,
                "success",
                params=params,
            )

            return data


    except httpx.HTTPStatusError as exc:

        log(
            endpoint,
            "http_error",
            status_code=(
                exc.response.status_code
            ),
            params=params,
        )

        raise RuntimeError(
            "PSX API returned "
            f"HTTP {exc.response.status_code}"
        ) from exc


    except httpx.RequestError as exc:

        log(
            endpoint,
            "request_error",
            error=str(exc),
            params=params,
        )

        raise RuntimeError(
            "Unable to connect to "
            "the PSX API."
        ) from exc


    except ValueError as exc:

        log(
            endpoint,
            "invalid_json",
            params=params,
        )

        raise RuntimeError(
            "PSX API returned an "
            "invalid JSON response."
        ) from exc