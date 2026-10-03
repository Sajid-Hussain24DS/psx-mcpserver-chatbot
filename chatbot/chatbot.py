from __future__ import annotations

import asyncio
import difflib
import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from chatbot.mcp_client import mcp_session
from chatbot.formatters import (
    format_industries,
    format_stock_data,
    format_symbols,
    format_top_bottom,
)
from chatbot.llm import create_llm_client


load_dotenv()



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
    """
    Application-side orchestrator for Groq + MCP.

    The LLM only requests tools. This class is responsible for
    validating/routing those requests, executing MCP tools, passing
    results back to the LLM, and returning the final answer.
    """

    def __init__(self) -> None:
        self.tools: list[Any] = []
        self.tool_map: dict[str, Any] = {}

        self.last_tool: str | None = None
        self.last_arguments: dict[str, Any] = {}
        self.last_debug: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = str(text).lower().strip()
        return re.sub(r"\s+", " ", text)

    # ------------------------------------------------------------------
    # MCP
    # ------------------------------------------------------------------

    async def _load_tools(self, session: ClientSession) -> list[Any]:
        response = await session.list_tools()
        self.tools = list(response.tools or [])
        self.tool_map = {tool.name: tool for tool in self.tools}
        return self.tools

    async def _call_tool(
        self,
        session: ClientSession,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        arguments = arguments or {}

        if tool_name not in self.tool_map:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

        started = time.perf_counter()
        self.last_tool = tool_name
        self.last_arguments = arguments

        try:
            result = await session.call_tool(
                tool_name,
                arguments=arguments,
            )

            self.last_debug = {
                "status": "success",
                "tool": tool_name,
                "arguments": arguments,
                "duration_ms": round(
                    (time.perf_counter() - started) * 1000,
                    2,
                ),
                "result_received": True,
            }

            return result

        except Exception as exc:
            self.last_debug = {
                "status": "error",
                "tool": tool_name,
                "arguments": arguments,
                "duration_ms": round(
                    (time.perf_counter() - started) * 1000,
                    2,
                ),
                "result_received": False,
                "error": str(exc),
            }
            raise

    # ------------------------------------------------------------------
    # Industry detection
    # ------------------------------------------------------------------

    async def _find_industry_in_question(
                
            self,
            session: ClientSession,
            question: str,
        ) -> str | None:
                
            question_normalized = self._normalize_text(question)

            try:
                result = await self._call_tool(
                    session,
                    "get_industries",
                    {},
                )

                industries = self._extract_tool_result(result)

                if isinstance(industries, dict):
                    possible_industries = (
                        industries.get("industries")
                        or industries.get("data")
                        or industries.get("results")
                        or []
                    )
                elif isinstance(industries, list):
                    possible_industries = industries
                else:
                    possible_industries = []

                candidates: list[tuple[str, str]] = []

                for item in possible_industries:
                    if isinstance(item, dict):
                        name = (
                            item.get("industry")
                            or item.get("name")
                            or item.get("sector")
                        )
                    else:
                        name = str(item)

                    if not name:
                        continue

                    original_name = str(name).strip()
                    normalized_name = self._normalize_text(original_name)

                    candidates.append(
                        (normalized_name, original_name)
                    )

                # --------------------------------------------------------------
                # Direct phrase match
                # --------------------------------------------------------------
                for normalized_name, original_name in candidates:
                    if normalized_name in question_normalized:
                        return original_name

                # --------------------------------------------------------------
                # Normalize common user wording
                #
                # This does NOT hardcode the industry list.
                # The actual industries still come from get_industries().
                # --------------------------------------------------------------
                aliases = {
                    "banking": "bank",
                    "banks": "bank",
                    "bank": "bank",
                    "textiles": "textile",
                    "chemicals": "chemical",
                    "pharmaceuticals": "pharmaceutical",
                    "automobiles": "automobile",
                    "securities": "security",
                    "companies": "company",
                    "industries": "industry",
                }

                def normalize_token(token: str) -> str:
                    token = token.lower().strip()

                    if token in aliases:
                        return aliases[token]

                    if len(token) > 4 and token.endswith("ies"):
                        return token[:-3] + "y"

                    if len(token) > 4 and token.endswith("s"):
                        return token[:-1]

                    return token

                question_tokens = {
                    normalize_token(token)
                    for token in re.findall(
                        r"[a-z0-9]+",
                        question_normalized,
                    )
                    if len(token) >= 3
                }

                # --------------------------------------------------------------
                # Token matching
                #
                # Example:
                # "which banking stocks..."
                #
                # banking -> bank
                # COMMERCIAL BANKS -> commercial + bank
                #
                # Therefore COMMERCIAL BANKS is detected.
                # --------------------------------------------------------------
                best_match: str | None = None
                best_score = 0.0

                for normalized_name, original_name in candidates:
                    industry_tokens = {
                        normalize_token(token)
                        for token in re.findall(
                            r"[a-z0-9]+",
                            normalized_name,
                        )
                        if len(token) >= 3
                    }

                    overlap = question_tokens.intersection(
                        industry_tokens
                    )

                    if not overlap:
                        continue

                    score = len(overlap) / len(industry_tokens)

                    if score > best_score:
                        best_score = score
                        best_match = original_name

                if best_match is not None and best_score >= 0.5:
                    return best_match

                # --------------------------------------------------------------
                # Fuzzy fallback
                # --------------------------------------------------------------
                question_words = [
                    word
                    for word in question_tokens
                    if len(word) >= 4
                ]

                for normalized_name, original_name in candidates:
                    industry_tokens = [
                        normalize_token(token)
                        for token in re.findall(
                            r"[a-z0-9]+",
                            normalized_name,
                        )
                        if len(token) >= 4
                    ]

                    for industry_token in industry_tokens:
                        for question_word in question_words:
                            ratio = difflib.SequenceMatcher(
                                None,
                                industry_token,
                                question_word,
                            ).ratio()

                            if ratio >= 0.80:
                                return original_name

            except Exception:
                return None

            return None

    # ------------------------------------------------------------------
    # Direct deterministic routing
    # ------------------------------------------------------------------

    async def _detect_direct_tool(
        self,
        session: ClientSession,
        question: str,
    ) -> tuple[str | None, dict[str, Any]]:
        q = self._normalize_text(question)

        if (
            "list symbols" in q
            or "all symbols" in q
            or "stock symbols" in q
            or q in {"symbols", "symbol"}
        ):
            return "get_symbols", {}

        if (
            "list industries" in q
            or "all industries" in q
            or q == "industries"
            or q == "industry"
        ):
            return "get_industries", {}

        industry = None

        if (
            "top change" in q
            or "top 10 change" in q
            or "highest change" in q
            or "top gainers" in q
            or "top gainer" in q
        ):
            industry = await self._find_industry_in_question(
                session,
                question,
            )
            return (
                "get_top_change",
                {"industry": industry} if industry else {},
            )

        if (
            "bottom change" in q
            or "bottom 10 change" in q
            or "lowest change" in q
            or "top losers" in q
            or "losers" in q
        ):
            industry = await self._find_industry_in_question(
                session,
                question,
            )
            return (
                "get_bottom_change",
                {"industry": industry} if industry else {},
            )

        if (
            "top volume" in q
            or "highest volume" in q
            or "most volume" in q
        ):
            industry = await self._find_industry_in_question(
                session,
                question,
            )
            return (
                "get_top_volume",
                {"industry": industry} if industry else {},
            )

        if (
            "bottom volume" in q
            or "lowest volume" in q
            or "least volume" in q
        ):
            industry = await self._find_industry_in_question(
                session,
                question,
            )
            return (
                "get_bottom_volume",
                {"industry": industry} if industry else {},
            )

        return None, {}

    # ------------------------------------------------------------------
    # Tool schema conversion
    # ------------------------------------------------------------------

    def _openai_tools(self) -> list[dict[str, Any]]:
        openai_tools: list[dict[str, Any]] = []

        for tool in self.tools:
            input_schema = getattr(
                tool,
                "inputSchema",
                None,
            )

            if input_schema is None:
                input_schema = getattr(
                    tool,
                    "input_schema",
                    None,
                )

            if not input_schema:
                input_schema = {
                    "type": "object",
                    "properties": {},
                }

            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": (
                            getattr(tool, "description", None)
                            or f"PSX MCP tool: {tool.name}"
                        ),
                        "parameters": input_schema,
                    },
                }
            )

        return openai_tools

    # ------------------------------------------------------------------
    # Result extraction / formatting
    # ------------------------------------------------------------------

    def _extract_tool_result(self, result: Any) -> Any:
        if result is None:
            return None

        content = getattr(
            result,
            "content",
            None,
        )

        if content is None:
            return result

        structured = getattr(
            result,
            "structuredContent",
            None,
        )

        if structured is None:
            structured = getattr(
                result,
                "structured_content",
                None,
            )

        if structured is not None:
            return structured

        extracted: list[Any] = []

        for item in content:
            text_value = getattr(
                item,
                "text",
                None,
            )

            if text_value is not None:
                extracted.append(text_value)
            else:
                extracted.append(item)

        if len(extracted) == 1:
            value = extracted[0]

            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value

            return value

        return extracted

    def _format_tool_result(
        self,
        tool_name: str,
        result: Any,
    ) -> str:
        data = self._extract_tool_result(result)

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
            # Do not allow a presentation formatter to break the agent.
            pass

        if isinstance(data, str):
            return data

        try:
            return json.dumps(
                data,
                ensure_ascii=False,
                default=str,
            )
        except (TypeError, ValueError):
            return str(data)

    def _tool_result_for_llm(
        self,
        tool_name: str,
        result: Any,
    ) -> str:
        """
        Send compact structured data to the LLM when possible.
        The user-facing formatter remains separate.
        """
        data = self._extract_tool_result(result)

        try:
            return json.dumps(
                {
                    "tool": tool_name,
                    "data": data,
                },
                ensure_ascii=False,
                default=str,
            )
        except (TypeError, ValueError):
            return str(data)

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    @staticmethod
    def _system_prompt() -> str:
        return """
You are a PSX data chatbot. You have access to MCP tools containing the current PSX dataset.

Rules:
1. Use MCP tools for any PSX fact; never answer market data from memory.
2. Use only the supplied MCP tools and their actual results.
3. Never invent, rename, or guess symbols, industries, prices, change %, volume, or company data.
4. For an industry request, use the exact industry value returned by `get_industries`.
5. Natural-language industry terms may be normalized only when they map clearly to one live industry.
6. If a term matches multiple live industries, do not guess; ask the user to specify.
7. Example: "banking" → "COMMERCIAL BANKS". "technology" → "TECHNOLOGY & COMMUNICATION".
8. Example: "textile" is ambiguous when TEXTILE COMPOSITE, TEXTILE SPINNING, and TEXTILE WEAVING all exist; ask which one.
9. For ranking requests, preserve the tool's ranking direction and returned values exactly.
10. Use conversation history for follow-up context when the user's subject is clear.
11. Do not call tools for greetings or casual conversation.
12. After receiving tool data, answer directly and concisely. Use a table for multiple stocks when useful.
13. If tool data is missing or a tool fails, state that the requested PSX data could not be retrieved. Do not fabricate a result.
14. You are a PSX data assistant, not a financial advisor.
""".strip()

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    async def _ask_llm(
        self,
        client: Any,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        return await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=tools or None,
            tool_choice="auto" if tools else None,
        )

    @staticmethod
    def _parse_tool_arguments(
        raw_arguments: str | None,
    ) -> dict[str, Any]:
        raw_arguments = raw_arguments or "{}"

        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON tool arguments: {exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "Tool arguments must be a JSON object."
            )

        return parsed

    # ------------------------------------------------------------------
    # Main async flow
    # ------------------------------------------------------------------

    async def _chat_async(
        self,
        user_message: str,
        history: list | None = None,
    ) -> str:
        self.last_tool = None
        self.last_arguments = {}
        self.last_debug = None

        try:

            async with mcp_session() as session:


                    await self._load_tools(session)

                    # --------------------------------------------------
                    # Deterministic route for common PSX requests.
                    # Crucially, this uses the SAME async MCP session.
                    # --------------------------------------------------
                    direct_tool, direct_arguments = (
                        await self._detect_direct_tool(
                            session,
                            user_message,
                        )
                    )

                    if direct_tool:
                        try:
                            result = await self._call_tool(
                                session,
                                direct_tool,
                                direct_arguments,
                            )

                            return self._format_tool_result(
                                direct_tool,
                                result,
                            )

                        except Exception:
                            # Fall through to the LLM route.
                            pass

                    llm_client = create_llm_client()
                    openai_tools = self._openai_tools()

                    messages: list[dict[str, Any]] = [
                        {
                            "role": "system",
                            "content": self._system_prompt(),
                        }
                    ]

                    if history:
                        for item in history:
                            if not isinstance(item, dict):
                                continue

                            role = item.get("role")
                            content = item.get("content")

                            if (
                                role in {"user", "assistant"}
                                and content
                            ):
                                messages.append(
                                    {
                                        "role": role,
                                        "content": str(content),
                                    }
                                )

                    messages.append(
                        {
                            "role": "user",
                            "content": user_message,
                        }
                    )

                    total_tool_calls = 0

                    for _ in range(MAX_TOOL_ITERATIONS):
                        response = await self._ask_llm(
                            llm_client,
                            messages,
                            openai_tools,
                        )

                        if not response.choices:
                            return "I could not generate a response."

                        message = response.choices[0].message
                        tool_calls = getattr(
                            message,
                            "tool_calls",
                            None,
                        )

                        if not tool_calls:
                            return (
                                message.content
                                or "I could not generate a response."
                            )

                        # Reproduce the assistant tool-call message exactly
                        # enough for the next Groq request.
                        assistant_message: dict[str, Any] = {
                            "role": "assistant",
                            "content": message.content or "",
                            "tool_calls": [],
                        }

                        for tool_call in tool_calls:
                            function = tool_call.function

                            assistant_message["tool_calls"].append(
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": function.name,
                                        "arguments": (
                                            function.arguments or "{}"
                                        ),
                                    },
                                }
                            )

                        messages.append(assistant_message)

                        for tool_call in tool_calls:
                            total_tool_calls += 1

                            if total_tool_calls > MAX_TOOL_CALLS:
                                return (
                                    "The request required too many tool calls "
                                    "and was stopped safely."
                                )

                            function = tool_call.function
                            tool_name = function.name

                            try:
                                arguments = self._parse_tool_arguments(
                                    function.arguments
                                )

                                if tool_name not in self.tool_map:
                                    raise ValueError(
                                        f"Unknown MCP tool requested: {tool_name}"
                                    )

                                tool_result = await self._call_tool(
                                    session,
                                    tool_name,
                                    arguments,
                                )

                                llm_content = self._tool_result_for_llm(
                                    tool_name,
                                    tool_result,
                                )

                            except Exception as tool_error:
                                self.last_debug = {
                                    "status": "error",
                                    "tool": tool_name,
                                    "arguments": (
                                        arguments
                                        if "arguments" in locals()
                                        else {}
                                    ),
                                    "result_received": False,
                                    "error": str(tool_error),
                                }

                                llm_content = json.dumps(
                                    {
                                        "tool": tool_name,
                                        "error": str(tool_error),
                                    },
                                    ensure_ascii=False,
                                )

                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": tool_name,
                                    "content": llm_content,
                                }
                            )

                    return (
                        "I was unable to complete the request within "
                        "the allowed tool-call limit."
                    )

        except Exception as error:
            self.last_debug = {
                "status": "connection_error",
                "tool": self.last_tool,
                "arguments": self.last_arguments,
                "result_received": False,
                "error": str(error),
            }

            # Do not expose raw internal stack/error details to end users.
            return (
                "I could not retrieve the requested PSX data right now. "
                "Please try again."
            )

    # ------------------------------------------------------------------
    # Public sync API for Streamlit / scripts
    # ------------------------------------------------------------------

    def chat(
        self,
        user_message: str,
        history: list | None = None,
    ) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self._chat_async(
                    user_message=user_message,
                    history=history,
                )
            )

        raise RuntimeError(
            "chat() cannot be called from an active event loop. "
            "Use: await PSXChatbot()._chat_async(...)"
        )


def ask_chatbot(
    user_message: str,
    history: list | None = None,
) -> dict[str, Any]:
    """
    Stateless application entry point.

    A fresh PSXChatbot is created per request so mutable MCP/debug
    state is not shared between Streamlit users.
    """
    chatbot = PSXChatbot()
    answer = chatbot.chat(
        user_message=user_message,
        history=history,
    )

    return {
        "answer": answer,
        "tool": chatbot.last_tool,
        "arguments": chatbot.last_arguments,
        "debug": chatbot.last_debug,
    }
