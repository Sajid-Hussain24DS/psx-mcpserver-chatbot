from __future__ import annotations

import asyncio
import difflib
import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from chatbot.formatters import (
    format_industries,
    format_stock_data,
    format_symbols,
    format_top_bottom,
)
from chatbot.llm import create_llm_client


load_dotenv()


MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    
    "http://127.0.0.1:5173/mcp",
)

LLM_PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "groq",
).lower()

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "openai/gpt-oss-120b",
)

MAX_TOOL_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", "6"))
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "12"))


class PSXChatbot:
    def __init__(self) -> None:
        self.tools: list[Any] = []
        self.tool_map: dict[str, Any] = {}

        self.last_tool: str | None = None
        self.last_arguments: dict[str, Any] | None = None
        self.last_debug: list[dict[str, Any]] = []

    # ---------------------------------------------------------
    # TEXT HELPERS
    # ---------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    # ---------------------------------------------------------
    # MCP
    # ---------------------------------------------------------

    async def _load_tools(self, session: ClientSession) -> list[Any]:
        result = await session.list_tools()

        self.tools = list(result.tools or [])
        self.tool_map = {
            tool.name: tool
            for tool in self.tools
        }

        return self.tools

    async def _call_tool(
        self,
        session: ClientSession,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:

        if tool_name not in self.tool_map:
            raise ValueError(
                f"MCP tool '{tool_name}' is not available."
            )

        self.last_tool = tool_name
        self.last_arguments = arguments

        started = time.time()

        result = await session.call_tool(
            tool_name,
            arguments,
        )

        elapsed = round(time.time() - started, 3)

        self.last_debug.append(
            {
                "tool": tool_name,
                "arguments": arguments,
                "elapsed_seconds": elapsed,
                "success": True,
            }
        )

        return result

    # ---------------------------------------------------------
    # OPTIONAL INDUSTRY DETECTION HELPERS
    #
    # These are kept from the existing architecture.
    # They are NOT used for routing anymore.
    # The LLM now decides which MCP tool to call.
    # ---------------------------------------------------------

    async def _find_industry_in_question(
        self,
        session: ClientSession,
        question: str,
    ) -> str | None:

        try:
            result = await self._call_tool(
                session,
                "get_industries",
                {},
            )

            data = self._extract_tool_result(result)

            if not isinstance(data, list):
                return None

            industries: list[str] = []

            for item in data:
                if isinstance(item, str):
                    industries.append(item)

                elif isinstance(item, dict):
                    for key in ("industry", "name", "sector"):
                        value = item.get(key)

                        if value:
                            industries.append(str(value))
                            break

            if not industries:
                return None

            normalized_question = self._normalize_text(question)

            # Exact match
            for industry in industries:
                normalized_industry = self._normalize_text(industry)

                if normalized_industry in normalized_question:
                    return industry

            # Fuzzy match
            words = normalized_question.split()

            for industry in industries:
                normalized_industry = self._normalize_text(industry)

                score = difflib.SequenceMatcher(
                    None,
                    normalized_industry,
                    normalized_question,
                ).ratio()

                if score >= 0.80:
                    return industry

                for word in words:
                    if len(word) >= 4:
                        word_score = difflib.SequenceMatcher(
                            None,
                            normalized_industry,
                            word,
                        ).ratio()

                        if word_score >= 0.90:
                            return industry

        except Exception:
            return None

        return None

    # ---------------------------------------------------------
    # OLD DIRECT ROUTER
    #
    # Kept for compatibility with the existing file, but it is
    # NO LONGER called from _chat_async().
    #
    # The LLM is now responsible for selecting MCP tools.
    # ---------------------------------------------------------

    async def _detect_direct_tool(
        self,
        session: ClientSession,
        question: str,
    ) -> tuple[str, dict[str, Any]] | None:

        q = self._normalize_text(question)

        industry = await self._find_industry_in_question(
            session,
            question,
        )

        if (
            "top" in q
            and "change" in q
        ):
            arguments = {}

            if industry:
                arguments["industry"] = industry

            return "get_top_change", arguments

        if (
            "bottom" in q
            and "change" in q
        ):
            arguments = {}

            if industry:
                arguments["industry"] = industry

            return "get_bottom_change", arguments

        if (
            "top" in q
            and "volume" in q
        ):
            arguments = {}

            if industry:
                arguments["industry"] = industry

            return "get_top_volume", arguments

        if (
            "bottom" in q
            and "volume" in q
        ):
            arguments = {}

            if industry:
                arguments["industry"] = industry

            return "get_bottom_volume", arguments

        if "industry" in q or "industries" in q:
            return "get_industries", {}

        if "symbol" in q or "symbols" in q:
            return "get_symbols", {}

        if "stock" in q:
            arguments = {}

            if industry:
                arguments["industry"] = industry

            return "get_stocks", arguments

        return None

    # ---------------------------------------------------------
    # OPENAI / GROQ TOOL SCHEMA
    # ---------------------------------------------------------

    def _openai_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []

        for tool in self.tools:
            schema = getattr(
                tool,
                "inputSchema",
                None,
            )

            if schema is None:
                schema = getattr(
                    tool,
                    "input_schema",
                    None,
                )

            if schema is None:
                schema = {
                    "type": "object",
                    "properties": {},
                }

            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": (
                            getattr(tool, "description", None)
                            or f"MCP tool: {tool.name}"
                        ),
                        "parameters": schema,
                    },
                }
            )

        return tools

    # ---------------------------------------------------------
    # MCP RESULT EXTRACTION
    # ---------------------------------------------------------

    def _extract_tool_result(self, result: Any) -> Any:

        if result is None:
            return None

        # MCP CallToolResult usually has .content
        content = getattr(
            result,
            "content",
            None,
        )

        if content is None:
            return result

        extracted: list[Any] = []

        for item in content:

            text_value = getattr(
                item,
                "text",
                None,
            )

            if text_value is not None:
                try:
                    extracted.append(
                        json.loads(text_value)
                    )
                except Exception:
                    extracted.append(text_value)

                continue

            extracted.append(item)

        if len(extracted) == 1:
            return extracted[0]

        return extracted

    # ---------------------------------------------------------
    # FORMATTER
    #
    # Kept for existing compatibility / UI use.
    # It is NOT used as the final answer in the normal LLM flow.
    # ---------------------------------------------------------

    def _format_tool_result(
        self,
        tool_name: str,
        data: Any,
    ) -> str:

        try:

            if tool_name == "get_symbols":
                return format_symbols(data)

            if tool_name == "get_industries":
                return format_industries(data)

            if tool_name == "get_stocks":
                return format_stock_data(data)

            if tool_name in {
                "get_top_change",
                "get_bottom_change",
                "get_top_volume",
                "get_bottom_volume",
            }:
                return format_top_bottom(
                    data,
                    tool_name,
                )

        except Exception:
            pass

        if isinstance(data, str):
            return data

        try:
            return json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        except Exception:
            return str(data)

    # ---------------------------------------------------------
    # MCP RESULT → LLM
    # ---------------------------------------------------------

    def _tool_result_for_llm(
        self,
        tool_name: str,
        data: Any,
    ) -> str:

        payload = {
            "tool": tool_name,
            "data": data,
        }

        try:
            return json.dumps(
                payload,
                ensure_ascii=False,
                default=str,
            )
        except Exception:
            return str(payload)

    # ---------------------------------------------------------
    # SYSTEM PROMPT
    # ---------------------------------------------------------

    def _system_prompt(self) -> str:

        return """
You are a professional Pakistan Stock Exchange (PSX) data chatbot.

Your job is to answer user questions using the available MCP tools.

IMPORTANT DATA-GROUNDING RULES:

1. Any question asking for PSX facts, stock data, symbols,
   industries, rankings, changes, volumes, or other market
   information MUST be answered using MCP data.

2. Never answer a PSX factual question from your pretrained
   knowledge.

3. Never use external websites, web search, outside databases,
   or unstated information as a source of PSX facts.

4. The MCP tools and their returned data are the source of truth
   for PSX information in this chatbot.

5. Dynamically understand the user's question and select the
   MCP tool or tools that can provide the required information.

6. Do not depend on predefined questions or fixed keyword
   patterns. Users may ask PSX questions naturally in different
   ways.

7. You may call multiple MCP tools when a question requires
   information from more than one source.

8. Use conversation history to understand follow-up questions
   and references to previous results.

9. After receiving MCP results, analyze, compare, summarize,
   filter, or explain those results when appropriate.

10. Any PSX factual claim in your final answer must be supported
    by the MCP data retrieved during the current conversation.

11. Do not introduce unsupported PSX facts from your own
    knowledge.

12. If the available MCP data does not contain the information
    required to answer the question, clearly say that the
    requested information is not available in the current PSX
    data.

13. If an MCP tool fails or returns no useful data, do not
    fabricate an answer. Explain that the requested data could
    not be retrieved.

14. Do not describe data as real-time unless the underlying
    PSX data source actually provides real-time data.

15. You are a data assistant, not a financial advisor.

16. Keep answers clear, concise, and useful.

For non-PSX conversational questions such as greetings, respond
normally without unnecessarily calling PSX tools.
"""

    # ---------------------------------------------------------
    # LLM CALL
    # ---------------------------------------------------------

    async def _ask_llm(
        self,
        client: Any,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
    ) -> Any:

        kwargs: dict[str, Any] = {
            "model": LLM_MODEL,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
            else:
                kwargs["tool_choice"] = "auto"

        return await client.chat.completions.create(
            **kwargs
        )

    # ---------------------------------------------------------
    # TOOL ARGUMENT PARSER
    # ---------------------------------------------------------

    def _parse_tool_arguments(
        self,
        arguments: Any,
    ) -> dict[str, Any]:

        if arguments is None:
            return {}

        if isinstance(arguments, dict):
            return arguments

        if isinstance(arguments, str):

            try:
                parsed = json.loads(arguments)

                if isinstance(parsed, dict):
                    return parsed

            except json.JSONDecodeError:
                return {}

        return {}

    # ---------------------------------------------------------
    # MAIN CHAT FLOW
    # ---------------------------------------------------------

    async def _chat_async(
        self,
        question: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:

        self.last_tool = None
        self.last_arguments = None
        self.last_debug = []

        try:

            # -------------------------------------------------
            # CONNECT TO MCP
            # -------------------------------------------------

            async with streamable_http_client(
    MCP_SERVER_URL
) as (
    read_stream,
    write_stream,
):

                async with ClientSession(
                    read_stream,
                    write_stream,
                ) as session:

                    await session.initialize()

                    # -----------------------------------------
                    # LOAD ALL AVAILABLE MCP TOOLS
                    # -----------------------------------------

                    await self._load_tools(session)

                    if not self.tools:
                        return (
                            "No PSX MCP tools are currently "
                            "available."
                        )

                    openai_tools = self._openai_tools()

                    # -----------------------------------------
                    # LLM CLIENT
                    # -----------------------------------------

                    client = create_llm_client()

                    # -----------------------------------------
                    # MESSAGE HISTORY
                    # -----------------------------------------

                    messages: list[dict[str, Any]] = [
                        {
                            "role": "system",
                            "content": self._system_prompt(),
                        }
                    ]

                    if history:

                        for item in history:

                            role = item.get("role")
                            content = item.get("content")

                            if role in {
                                "user",
                                "assistant",
                            } and content:

                                messages.append(
                                    {
                                        "role": role,
                                        "content": content,
                                    }
                                )

                    messages.append(
                        {
                            "role": "user",
                            "content": question,
                        }
                    )

                    # -----------------------------------------
                    # LLM ↔ MCP TOOL LOOP
                    # -----------------------------------------

                    total_tool_calls = 0

                    for _iteration in range(
                        MAX_TOOL_ITERATIONS
                    ):

                        response = await self._ask_llm(
                            client=client,
                            messages=messages,
                            tools=openai_tools,
                            tool_choice="auto",
                        )

                        if not response.choices:
                            return (
                                "I could not generate an answer "
                                "for that request."
                            )

                        message = response.choices[0].message

                        tool_calls = (
                            getattr(
                                message,
                                "tool_calls",
                                None,
                            )
                            or []
                        )

                        # -------------------------------------
                        # NO TOOL CALL
                        # -------------------------------------

                        if not tool_calls:

                            answer = (
                                getattr(
                                    message,
                                    "content",
                                    None,
                                )
                                or ""
                            ).strip()

                            if answer:
                                return answer

                            return (
                                "I could not generate a useful "
                                "answer for that request."
                            )

                        # -------------------------------------
                        # STORE ASSISTANT TOOL CALL MESSAGE
                        # -------------------------------------

                        assistant_tool_calls = []

                        for tool_call in tool_calls:

                            function = tool_call.function

                            assistant_tool_calls.append(
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": function.name,
                                        "arguments": (
                                            function.arguments
                                            or "{}"
                                        ),
                                    },
                                }
                            )

                        messages.append(
                            {
                                "role": "assistant",
                                "content": (
                                    getattr(
                                        message,
                                        "content",
                                        None,
                                    )
                                    or ""
                                ),
                                "tool_calls": (
                                    assistant_tool_calls
                                ),
                            }
                        )

                        # -------------------------------------
                        # EXECUTE MCP TOOLS
                        # -------------------------------------

                        for tool_call in tool_calls:

                            total_tool_calls += 1

                            if (
                                total_tool_calls
                                > MAX_TOOL_CALLS
                            ):
                                return (
                                    "I stopped the request because "
                                    "too many data-tool calls were "
                                    "required."
                                )

                            function = tool_call.function

                            tool_name = function.name

                            arguments = (
                                self._parse_tool_arguments(
                                    function.arguments
                                )
                            )

                            # -----------------------------
                            # Validate actual MCP tool
                            # -----------------------------

                            if (
                                tool_name
                                not in self.tool_map
                            ):

                                tool_output = json.dumps(
                                    {
                                        "error": (
                                            f"MCP tool "
                                            f"'{tool_name}' "
                                            "is not available."
                                        )
                                    }
                                )

                            else:

                                try:

                                    result = (
                                        await self._call_tool(
                                            session,
                                            tool_name,
                                            arguments,
                                        )
                                    )

                                    data = (
                                        self._extract_tool_result(
                                            result
                                        )
                                    )

                                    # ---------------------------------
                                    # IMPORTANT:
                                    # Send raw/complete MCP data back
                                    # to LLM instead of returning the
                                    # formatter directly to the user.
                                    # ---------------------------------

                                    tool_output = (
                                        self._tool_result_for_llm(
                                            tool_name,
                                            data,
                                        )
                                    )

                                except Exception as exc:

                                    self.last_debug.append(
                                        {
                                            "tool": tool_name,
                                            "arguments": arguments,
                                            "success": False,
                                            "error": str(exc),
                                        }
                                    )

                                    tool_output = json.dumps(
                                        {
                                            "tool": tool_name,
                                            "error": (
                                                "The MCP tool "
                                                "could not retrieve "
                                                "the requested data."
                                            ),
                                        },
                                        ensure_ascii=False,
                                    )

                            # -----------------------------
                            # Return MCP result to LLM
                            # -----------------------------

                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": (
                                        tool_call.id
                                    ),
                                    "content": tool_output,
                                }
                            )

                    # -------------------------------------------------
                    # MAX ITERATIONS
                    # -------------------------------------------------

                    return (
                        "I could not complete the request within "
                        "the allowed data retrieval steps."
                    )

        except Exception as exc:

            self.last_debug.append(
                {
                    "success": False,
                    "error": f"{type(exc).__name__}: {exc!r}",
                }
            )

            return (
                f"DEBUG ERROR: {type(exc).__name__}: {exc!r}"
            )

    # ---------------------------------------------------------
    # SYNC WRAPPER
    # ---------------------------------------------------------

    def chat(
        self,
        question: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:

        return asyncio.run(
            self._chat_async(
                question,
                history,
            )
        )


# -------------------------------------------------------------
# PUBLIC FUNCTION
# -------------------------------------------------------------

def ask_chatbot(
    question: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:

    chatbot = PSXChatbot()

    answer = chatbot.chat(
        question,
        history,
    )

    return {
        "answer": answer,
        "tool": chatbot.last_tool,
        "arguments": chatbot.last_arguments,
        "debug": chatbot.last_debug,
    }