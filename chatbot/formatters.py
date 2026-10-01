

def format_ranking_result(
    tool_name: str,
    data: list,
) -> str:

    lines = []


    if tool_name == "get_top_volume":

        lines.append(
            "Top 10 stocks by trading volume:"
        )

        for index, stock in enumerate(
            data,
            start=1,
        ):

            symbol = stock.get(
                "symbol",
                "",
            )

            name = stock.get(
                "name",
                "",
            )

            volume = stock.get(
                "volume",
                0,
            )

            lines.append(
                f"{index}. {symbol} - {name} "
                f"- Volume: {volume:,}"
            )


    elif tool_name == "get_bottom_volume":

        lines.append(
            "Bottom 10 stocks by trading volume:"
        )

        for index, stock in enumerate(
            data,
            start=1,
        ):

            symbol = stock.get(
                "symbol",
                "",
            )

            name = stock.get(
                "name",
                "",
            )

            volume = stock.get(
                "volume",
                0,
            )

            lines.append(
                f"{index}. {symbol} - {name} "
                f"- Volume: {volume:,}"
            )


    elif tool_name == "get_top_change":

        lines.append(
            "Top 10 stocks by change percentage:"
        )

        for index, stock in enumerate(
            data,
            start=1,
        ):

            symbol = stock.get(
                "symbol",
                "",
            )

            name = stock.get(
                "name",
                "",
            )

            change = stock.get(
                "change_percent",
                0,
            )

            lines.append(
                f"{index}. {symbol} - {name} "
                f"- Change: {change}%"
            )


    elif tool_name == "get_bottom_change":

        lines.append(
            "Bottom 10 stocks by change percentage:"
        )

        for index, stock in enumerate(
            data,
            start=1,
        ):

            symbol = stock.get(
                "symbol",
                "",
            )

            name = stock.get(
                "name",
                "",
            )

            change = stock.get(
                "change_percent",
                0,
            )

            lines.append(
                f"{index}. {symbol} - {name} "
                f"- Change: {change}%"
            )


    return "\n".join(lines)



def answer_ranking_followup(
    user_question: str,
    tool_name: str,
    data: list,
):

    if not data:
        return None


    question = user_question.lower()


    # -----------------------------------------------------
    # Highest trading volume
    # -----------------------------------------------------

    if (
        tool_name == "get_top_volume"
        and (
            "which one" in question
            or "which stock" in question
            or "highest" in question
            or "maximum" in question
            or "highest trading volume" in question
        )
    ):

        stock = data[0]

        symbol = stock.get(
            "symbol",
            "",
        )

        name = stock.get(
            "name",
            "",
        )

        volume = stock.get(
            "volume",
            0,
        )

        return (
            f"{symbol} ({name}) has the highest "
            f"trading volume at {volume:,}."
        )



    if (
        tool_name == "get_bottom_volume"
        and (
            "which one" in question
            or "which stock" in question
            or "lowest" in question
            or "minimum" in question
            or "lowest trading volume" in question
        )
    ):

        stock = data[0]

        symbol = stock.get(
            "symbol",
            "",
        )

        name = stock.get(
            "name",
            "",
        )

        volume = stock.get(
            "volume",
            0,
        )

        return (
            f"{symbol} ({name}) has the lowest "
            f"trading volume at {volume:,}."
        )



    if (
        tool_name == "get_top_change"
        and (
            "which one" in question
            or "which stock" in question
            or "highest" in question
            or "maximum" in question
            or "highest change" in question
        )
    ):

        stock = data[0]

        symbol = stock.get(
            "symbol",
            "",
        )

        name = stock.get(
            "name",
            "",
        )

        change = stock.get(
            "change_percent",
            0,
        )

        return (
            f"{symbol} ({name}) has the highest "
            f"change percentage at {change}%."
        )


    if (
        tool_name == "get_bottom_change"
        and (
            "which one" in question
            or "which stock" in question
            or "lowest" in question
            or "minimum" in question
            or "lowest change" in question
        )
    ):

        stock = data[0]

        symbol = stock.get(
            "symbol",
            "",
        )

        name = stock.get(
            "name",
            "",
        )

        change = stock.get(
            "change_percent",
            0,
        )

        return (
            f"{symbol} ({name}) has the lowest "
            f"change percentage at {change}%."
        )


    return None



def format_symbols(
    data: list,
) -> str:

    if not data:

        return (
            "No PSX stock symbols were found."
        )


    symbols = []


    for item in data:

        if isinstance(
            item,
            dict,
        ):

            symbol = item.get(
                "symbol",
                "",
            )

        else:

            symbol = str(item)


        if symbol:

            symbols.append(symbol)


    return (
        f"The PSX database contains "
        f"{len(symbols)} active stock symbols:"
        f"\n\n"
        + ", ".join(symbols)
    )



def format_industries(
    data: list,
) -> str:

    if not data:

        return (
            "No PSX industries were found."
        )


    industries = []


    for item in data:

        if isinstance(
            item,
            dict,
        ):

            industry = item.get(
                "industry",
                "",
            )

        else:

            industry = str(item)


        if industry:

            industries.append(industry)


    lines = [
        "Available PSX industries:",
        "",
    ]


    for index, industry in enumerate(
        industries,
        start=1,
    ):

        lines.append(
            f"{index}. {industry}"
        )


    return "\n".join(lines)



def format_all_stocks(
    data: list,
    industry: str = "",
) -> str:

    if not data:

        if industry:

            return (
                f"No stocks were found for the "
                f"{industry} industry."
            )

        return "No stocks were found."


    lines = []


    if industry:

        lines.append(
            f"Stocks in the {industry} industry:"
        )

    else:

        lines.append(
            "PSX stocks:"
        )


    lines.append("")


    for index, stock in enumerate(
        data,
        start=1,
    ):

        symbol = stock.get(
            "symbol",
            "",
        )

        name = stock.get(
            "name",
            "",
        )

        change = stock.get(
            "change_percent"
        )

        volume = stock.get(
            "volume"
        )


        line = (
            f"{index}. {symbol} - {name}"
        )


        if change is not None:

            line += (
                f" - Change: {change}%"
            )


        if volume is not None:

            line += (
                f" - Volume: {volume:,}"
            )


        lines.append(line)


    return "\n".join(lines)