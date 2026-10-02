from __future__ import annotations

from typing import Any


# =========================================================
# DATA NORMALIZATION
# =========================================================

def _to_list(data: Any) -> list:

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        for key in (
            "data",
            "results",
            "result",
            "items",
            "stocks",
            "symbols",
            "industries",
            "records",
        ):

            value = data.get(key)

            if isinstance(value, list):
                return value

            if isinstance(value, dict):

                nested = _to_list(value)

                if nested:
                    return nested

        if any(
            key in data
            for key in (
                "symbol",
                "Symbol",
                "ticker",
                "Ticker",
            )
        ):

            return [data]

    return []


# =========================================================
# VALUE HELPERS
# =========================================================

def _get_value(
    item: Any,
    *keys: str,
    default: Any = "",
) -> Any:

    if not isinstance(
        item,
        dict,
    ):

        return default

    for key in keys:

        if (
            key in item
            and item[key] is not None
        ):

            return item[key]

    return default


def _format_number(
    value: Any,
) -> str:

    try:

        return f"{float(value):,.0f}"

    except (
        TypeError,
        ValueError,
    ):

        return str(value)


def _format_percent(
    value: Any,
) -> str:

    try:

        number = float(value)

        return f"{number:.2f}%"

    except (
        TypeError,
        ValueError,
    ):

        return str(value)


# =========================================================
# RANKINGS
# =========================================================

def format_ranking_result(
    tool_name: str,
    data: Any,
) -> str:

    rows = _to_list(data)

    titles = {

        "get_top_volume":
            "Top 10 stocks by trading volume:",

        "get_bottom_volume":
            "Bottom 10 stocks by trading volume:",

        "get_top_change":
            "Top 10 stocks by change percentage:",

        "get_bottom_change":
            "Bottom 10 stocks by change percentage:",
    }

    title = titles.get(
        tool_name,
        "PSX stock ranking:",
    )

    if not rows:

        return (
            "No stock data was returned "
            "by the PSX MCP server."
        )

    output = [
        title,
        "",
    ]

    for index, item in enumerate(
        rows[:10],
        start=1,
    ):

        symbol = _get_value(
            item,
            "symbol",
            "Symbol",
            "ticker",
            "Ticker",
            default="N/A",
        )

        name = _get_value(
            item,
            "name",
            "company_name",
            "companyName",
            "Name",
            default="",
        )

        change = _get_value(
            item,
            "change_percent",
            "change_percentage",
            "changePercent",
            "change %",
            "change",
            default=None,
        )

        volume = _get_value(
            item,
            "volume",
            "Volume",
            "trading_volume",
            "tradingVolume",
            default=None,
        )

        line = f"{index}. {symbol}"

        if name:
            line += f" - {name}"

        if "volume" in tool_name:

            if volume is not None:

                line += (
                    f" - Volume: "
                    f"{_format_number(volume)}"
                )

        elif "change" in tool_name:

            if change is not None:

                line += (
                    f" - Change: "
                    f"{_format_percent(change)}"
                )

        output.append(line)

    return "\n".join(output)


# =========================================================
# RANKING FOLLOW-UP
# =========================================================

def answer_ranking_followup(
    user_question: str,
    tool_name: str,
    data: Any,
) -> str:

    rows = _to_list(data)

    if not rows:

        return (
            "No stock data was returned "
            "by the PSX MCP server."
        )

    first = rows[0]

    symbol = _get_value(
        first,
        "symbol",
        "Symbol",
        "ticker",
        "Ticker",
        default="N/A",
    )

    name = _get_value(
        first,
        "name",
        "company_name",
        "companyName",
        "Name",
        default="",
    )

    change = _get_value(
        first,
        "change_percent",
        "change_percentage",
        "changePercent",
        "change",
        default=None,
    )

    volume = _get_value(
        first,
        "volume",
        "Volume",
        "trading_volume",
        default=None,
    )

    answer = str(symbol)

    if name:
        answer += f" - {name}"

    if volume is not None:

        answer += (
            f" - Volume: "
            f"{_format_number(volume)}"
        )

    if change is not None:

        answer += (
            f" - Change: "
            f"{_format_percent(change)}"
        )

    return answer


# =========================================================
# SYMBOLS
# =========================================================

def format_symbols(
    data: Any,
) -> str:

    rows = _to_list(data)

    if not rows:

        return "No PSX symbols were returned."

    symbols = []

    for item in rows:

        if isinstance(
            item,
            dict,
        ):

            symbol = _get_value(
                item,
                "symbol",
                "Symbol",
                "ticker",
                "Ticker",
                default="",
            )

        else:

            symbol = str(item)

        if symbol:

            symbols.append(
                str(symbol)
            )

    # Remove duplicate symbols.
    unique_symbols = []

    seen = set()

    for symbol in symbols:

        key = symbol.strip().upper()

        if key not in seen:

            seen.add(key)

            unique_symbols.append(
                symbol
            )

    return (
        f"Total PSX symbols: "
        f"{len(unique_symbols)}\n\n"
        + ", ".join(
            unique_symbols
        )
    )


# =========================================================
# INDUSTRIES
# =========================================================

def format_industries(
    data: Any,
) -> str:

    rows = _to_list(data)

    if not rows:

        return (
            "No PSX industries were returned."
        )

    industries = []

    for item in rows:

        if isinstance(
            item,
            dict,
        ):

            industry = _get_value(
                item,
                "industry",
                "Industry",
                "name",
                "Name",
                default="",
            )

        else:

            industry = str(item)

        if industry:

            industries.append(
                str(industry)
            )

    unique_industries = []

    seen = set()

    for industry in industries:

        key = industry.strip().lower()

        if key not in seen:

            seen.add(key)

            unique_industries.append(
                industry
            )

    output = [
        (
            f"Total industries: "
            f"{len(unique_industries)}"
        ),
        "",
    ]

    for index, industry in enumerate(
        unique_industries,
        start=1,
    ):

        output.append(
            f"{index}. {industry}"
        )

    return "\n".join(output)


# =========================================================
# ALL / INDUSTRY STOCKS
# =========================================================

def format_all_stocks(
    data: Any,
    industry: str = "",
) -> str:

    rows = _to_list(data)

    if not rows:

        return (
            "No PSX stock data was returned."
        )

    if industry:

        title = (
            f"PSX stocks in "
            f"{industry}:"
        )

    else:

        title = "All PSX stocks:"

    output = [
        f"Total stocks: {len(rows)}",
        "",
        title,
        "",
    ]

    for index, item in enumerate(
        rows,
        start=1,
    ):

        symbol = _get_value(
            item,
            "symbol",
            "Symbol",
            "ticker",
            "Ticker",
            default="N/A",
        )

        name = _get_value(
            item,
            "name",
            "company_name",
            "companyName",
            "Name",
            default="",
        )

        change = _get_value(
            item,
            "change_percent",
            "change_percentage",
            "changePercent",
            "change %",
            "change",
            default=None,
        )

        volume = _get_value(
            item,
            "volume",
            "Volume",
            "trading_volume",
            "tradingVolume",
            default=None,
        )

        row_industry = _get_value(
            item,
            "industry",
            "Industry",
            default="",
        )

        line = f"{index}. {symbol}"

        if name:

            line += (
                f" - {name}"
            )

        if row_industry and not industry:

            line += (
                f" - Industry: "
                f"{row_industry}"
            )

        if change is not None:

            line += (
                f" - Change: "
                f"{_format_percent(change)}"
            )

        if volume is not None:

            line += (
                f" - Volume: "
                f"{_format_number(volume)}"
            )

        output.append(line)

    return "\n".join(output)


# =========================================================
# COMPATIBILITY WRAPPERS
# =========================================================

def format_top_bottom(
    data: Any,
    tool_name: str,
) -> str:

    return format_ranking_result(
        tool_name,
        data,
    )


def format_stock_data(
    data: Any,
    industry: str = "",
) -> str:

    return format_all_stocks(
        data,
        industry,
    )