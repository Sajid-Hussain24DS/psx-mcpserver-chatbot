# from __future__ import annotations

# import asyncio
# import difflib
# import json
# import os
# import re
# import time
# from typing import Any

# from dotenv import load_dotenv
# from chatbot.mcp_client import mcp_session
# from chatbot.formatters import (
#     format_industries,
#     format_stock_data,
#     format_symbols,
#     format_top_bottom,
# )
# from chatbot.llm import create_llm_client


# load_dotenv()



# LLM_PROVIDER = os.getenv(
#     "LLM_PROVIDER",
#     "groq",
# ).lower()

# LLM_MODEL = os.getenv(
#     "LLM_MODEL",
#     "openai/gpt-oss-120b",
# )

# MAX_TOOL_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", "6"))
# MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "12"))


# class PSXChatbot:
#     """
#     Application-side orchestrator for Groq + MCP.

#     The LLM only requests tools. This class is responsible for
#     validating/routing those requests, executing MCP tools, passing
#     results back to the LLM, and returning the final answer.
#     """

#     def __init__(self) -> None:
#         self.tools: list[Any] = []
#         self.tool_map: dict[str, Any] = {}

#         self.last_tool: str | None = None
#         self.last_arguments: dict[str, Any] = {}
#         self.last_debug: dict[str, Any] | None = None

#     # ------------------------------------------------------------------
#     # Text helpers
#     # ------------------------------------------------------------------

#     @staticmethod
#     def _normalize_text(text: str) -> str:
#         text = str(text).lower().strip()
#         return re.sub(r"\s+", " ", text)

#     # ------------------------------------------------------------------
#     # MCP
#     # ------------------------------------------------------------------

#     async def _load_tools(self, session: ClientSession) -> list[Any]:
#         response = await session.list_tools()
#         self.tools = list(response.tools or [])
#         self.tool_map = {tool.name: tool for tool in self.tools}
#         return self.tools

#     async def _call_tool(
#         self,
#         session: ClientSession,
#         tool_name: str,
#         arguments: dict[str, Any] | None = None,
#     ) -> Any:
#         arguments = arguments or {}

#         if tool_name not in self.tool_map:
#             raise ValueError(f"Unknown MCP tool: {tool_name}")

#         started = time.perf_counter()
#         self.last_tool = tool_name
#         self.last_arguments = arguments

#         try:
#             result = await session.call_tool(
#                 tool_name,
#                 arguments=arguments,
#             )

#             self.last_debug = {
#                 "status": "success",
#                 "tool": tool_name,
#                 "arguments": arguments,
#                 "duration_ms": round(
#                     (time.perf_counter() - started) * 1000,
#                     2,
#                 ),
#                 "result_received": True,
#             }

#             return result

#         except Exception as exc:
#             self.last_debug = {
#                 "status": "error",
#                 "tool": tool_name,
#                 "arguments": arguments,
#                 "duration_ms": round(
#                     (time.perf_counter() - started) * 1000,
#                     2,
#                 ),
#                 "result_received": False,
#                 "error": str(exc),
#             }
#             raise

#     # ------------------------------------------------------------------
#     # Industry detection
#     # ------------------------------------------------------------------

#     async def _find_industry_in_question(
                
#             self,
#             session: ClientSession,
#             question: str,
#         ) -> str | None:
                
#             question_normalized = self._normalize_text(question)

#             try:
#                 result = await self._call_tool(
#                     session,
#                     "get_industries",
#                     {},
#                 )

#                 industries = self._extract_tool_result(result)

#                 if isinstance(industries, dict):
#                     possible_industries = (
#                         industries.get("industries")
#                         or industries.get("data")
#                         or industries.get("results")
#                         or []
#                     )
#                 elif isinstance(industries, list):
#                     possible_industries = industries
#                 else:
#                     possible_industries = []

#                 candidates: list[tuple[str, str]] = []

#                 for item in possible_industries:
#                     if isinstance(item, dict):
#                         name = (
#                             item.get("industry")
#                             or item.get("name")
#                             or item.get("sector")
#                         )
#                     else:
#                         name = str(item)

#                     if not name:
#                         continue

#                     original_name = str(name).strip()
#                     normalized_name = self._normalize_text(original_name)

#                     candidates.append(
#                         (normalized_name, original_name)
#                     )

#                 # --------------------------------------------------------------
#                 # Direct phrase match
#                 # --------------------------------------------------------------
#                 for normalized_name, original_name in candidates:
#                     if normalized_name in question_normalized:
#                         return original_name

#                 # --------------------------------------------------------------
#                 # Normalize common user wording
#                 #
#                 # This does NOT hardcode the industry list.
#                 # The actual industries still come from get_industries().
#                 # --------------------------------------------------------------
#                 aliases = {
#                     "banking": "bank",
#                     "banks": "bank",
#                     "bank": "bank",
#                     "textiles": "textile",
#                     "chemicals": "chemical",
#                     "pharmaceuticals": "pharmaceutical",
#                     "automobiles": "automobile",
#                     "securities": "security",
#                     "companies": "company",
#                     "industries": "industry",
#                 }

#                 def normalize_token(token: str) -> str:
#                     token = token.lower().strip()

#                     if token in aliases:
#                         return aliases[token]

#                     if len(token) > 4 and token.endswith("ies"):
#                         return token[:-3] + "y"

#                     if len(token) > 4 and token.endswith("s"):
#                         return token[:-1]

#                     return token

#                 question_tokens = {
#                     normalize_token(token)
#                     for token in re.findall(
#                         r"[a-z0-9]+",
#                         question_normalized,
#                     )
#                     if len(token) >= 3
#                 }

#                 # --------------------------------------------------------------
#                 # Token matching
#                 #
#                 # Example:
#                 # "which banking stocks..."
#                 #
#                 # banking -> bank
#                 # COMMERCIAL BANKS -> commercial + bank
#                 #
#                 # Therefore COMMERCIAL BANKS is detected.
#                 # --------------------------------------------------------------
#                 best_match: str | None = None
#                 best_score = 0.0

#                 for normalized_name, original_name in candidates:
#                     industry_tokens = {
#                         normalize_token(token)
#                         for token in re.findall(
#                             r"[a-z0-9]+",
#                             normalized_name,
#                         )
#                         if len(token) >= 3
#                     }

#                     overlap = question_tokens.intersection(
#                         industry_tokens
#                     )

#                     if not overlap:
#                         continue

#                     score = len(overlap) / len(industry_tokens)

#                     if score > best_score:
#                         best_score = score
#                         best_match = original_name

#                 if best_match is not None and best_score >= 0.5:
#                     return best_match

#                 # --------------------------------------------------------------
#                 # Fuzzy fallback
#                 # --------------------------------------------------------------
#                 question_words = [
#                     word
#                     for word in question_tokens
#                     if len(word) >= 4
#                 ]

#                 for normalized_name, original_name in candidates:
#                     industry_tokens = [
#                         normalize_token(token)
#                         for token in re.findall(
#                             r"[a-z0-9]+",
#                             normalized_name,
#                         )
#                         if len(token) >= 4
#                     ]

#                     for industry_token in industry_tokens:
#                         for question_word in question_words:
#                             ratio = difflib.SequenceMatcher(
#                                 None,
#                                 industry_token,
#                                 question_word,
#                             ).ratio()

#                             if ratio >= 0.80:
#                                 return original_name

#             except Exception:
#                 return None

#             return None

#     # ------------------------------------------------------------------
#     # Direct deterministic routing
#     # ------------------------------------------------------------------

#     async def _detect_direct_tool(
#         self,
#         session: ClientSession,
#         question: str,
#     ) -> tuple[str | None, dict[str, Any]]:
#         q = self._normalize_text(question)

#         if (
#             "list symbols" in q
#             or "all symbols" in q
#             or "stock symbols" in q
#             or q in {"symbols", "symbol"}
#         ):
#             return "get_symbols", {}

#         if (
#             "list industries" in q
#             or "all industries" in q
#             or q == "industries"
#             or q == "industry"
#         ):
#             return "get_industries", {}

#         industry = None

#         if (
#             "top change" in q
#             or "top 10 change" in q
#             or "highest change" in q
#             or "top gainers" in q
#             or "top gainer" in q
#         ):
#             industry = await self._find_industry_in_question(
#                 session,
#                 question,
#             )
#             return (
#                 "get_top_change",
#                 {"industry": industry} if industry else {},
#             )

#         if (
#             "bottom change" in q
#             or "bottom 10 change" in q
#             or "lowest change" in q
#             or "top losers" in q
#             or "losers" in q
#         ):
#             industry = await self._find_industry_in_question(
#                 session,
#                 question,
#             )
#             return (
#                 "get_bottom_change",
#                 {"industry": industry} if industry else {},
#             )

#         if (
#             "top volume" in q
#             or "highest volume" in q
#             or "most volume" in q
#         ):
#             industry = await self._find_industry_in_question(
#                 session,
#                 question,
#             )
#             return (
#                 "get_top_volume",
#                 {"industry": industry} if industry else {},
#             )

#         if (
#             "bottom volume" in q
#             or "lowest volume" in q
#             or "least volume" in q
#         ):
#             industry = await self._find_industry_in_question(
#                 session,
#                 question,
#             )
#             return (
#                 "get_bottom_volume",
#                 {"industry": industry} if industry else {},
#             )

#         return None, {}

#     # ------------------------------------------------------------------
#     # Tool schema conversion
#     # ------------------------------------------------------------------

#     def _openai_tools(self) -> list[dict[str, Any]]:
#         openai_tools: list[dict[str, Any]] = []

#         for tool in self.tools:
#             input_schema = getattr(
#                 tool,
#                 "inputSchema",
#                 None,
#             )

#             if input_schema is None:
#                 input_schema = getattr(
#                     tool,
#                     "input_schema",
#                     None,
#                 )

#             if not input_schema:
#                 input_schema = {
#                     "type": "object",
#                     "properties": {},
#                 }

#             openai_tools.append(
#                 {
#                     "type": "function",
#                     "function": {
#                         "name": tool.name,
#                         "description": (
#                             getattr(tool, "description", None)
#                             or f"PSX MCP tool: {tool.name}"
#                         ),
#                         "parameters": input_schema,
#                     },
#                 }
#             )

#         return openai_tools

#     # ------------------------------------------------------------------
#     # Result extraction / formatting
#     # ------------------------------------------------------------------

#     def _extract_tool_result(self, result: Any) -> Any:
#         if result is None:
#             return None

#         content = getattr(
#             result,
#             "content",
#             None,
#         )

#         if content is None:
#             return result

#         structured = getattr(
#             result,
#             "structuredContent",
#             None,
#         )

#         if structured is None:
#             structured = getattr(
#                 result,
#                 "structured_content",
#                 None,
#             )

#         if structured is not None:
#             return structured

#         extracted: list[Any] = []

#         for item in content:
#             text_value = getattr(
#                 item,
#                 "text",
#                 None,
#             )

#             if text_value is not None:
#                 extracted.append(text_value)
#             else:
#                 extracted.append(item)

#         if len(extracted) == 1:
#             value = extracted[0]

#             if isinstance(value, str):
#                 try:
#                     return json.loads(value)
#                 except (json.JSONDecodeError, TypeError):
#                     return value

#             return value

#         return extracted

#     def _format_tool_result(
#         self,
#         tool_name: str,
#         result: Any,
#     ) -> str:
#         data = self._extract_tool_result(result)

#         try:
#             if tool_name == "get_symbols":
#                 return format_symbols(data)

#             if tool_name == "get_industries":
#                 return format_industries(data)

#             if tool_name == "get_stocks":
#                 return format_stock_data(data)

#             if tool_name in {
#                 "get_top_change",
#                 "get_bottom_change",
#                 "get_top_volume",
#                 "get_bottom_volume",
#             }:
#                 return format_top_bottom(
#                     data,
#                     tool_name,
#                 )

#         except Exception:
#             # Do not allow a presentation formatter to break the agent.
#             pass

#         if isinstance(data, str):
#             return data

#         try:
#             return json.dumps(
#                 data,
#                 ensure_ascii=False,
#                 default=str,
#             )
#         except (TypeError, ValueError):
#             return str(data)

#     def _tool_result_for_llm(
#         self,
#         tool_name: str,
#         result: Any,
#     ) -> str:
#         """
#         Send compact structured data to the LLM when possible.
#         The user-facing formatter remains separate.
#         """
#         data = self._extract_tool_result(result)

#         try:
#             return json.dumps(
#                 {
#                     "tool": tool_name,
#                     "data": data,
#                 },
#                 ensure_ascii=False,
#                 default=str,
#             )
#         except (TypeError, ValueError):
#             return str(data)

#     # ------------------------------------------------------------------
#     # Prompt
#     # ------------------------------------------------------------------

#     @staticmethod
#     def _system_prompt() -> str:
#         return """
# You are a PSX data chatbot. You have access to MCP tools containing the current PSX dataset.

# Rules:
# 1. Use MCP tools for any PSX fact; never answer market data from memory.
# 2. Use only the supplied MCP tools and their actual results.
# 3. Never invent, rename, or guess symbols, industries, prices, change %, volume, or company data.
# 4. For an industry request, use the exact industry value returned by `get_industries`.
# 5. Natural-language industry terms may be normalized only when they map clearly to one live industry.
# 6. If a term matches multiple live industries, do not guess; ask the user to specify.
# 7. Example: "banking" → "COMMERCIAL BANKS". "technology" → "TECHNOLOGY & COMMUNICATION".
# 8. Example: "textile" is ambiguous when TEXTILE COMPOSITE, TEXTILE SPINNING, and TEXTILE WEAVING all exist; ask which one.
# 9. For ranking requests, preserve the tool's ranking direction and returned values exactly.
# 10. Use conversation history for follow-up context when the user's subject is clear.
# 11. Do not call tools for greetings or casual conversation.
# 12. After receiving tool data, answer directly and concisely. Use a table for multiple stocks when useful.
# 13. If tool data is missing or a tool fails, state that the requested PSX data could not be retrieved. Do not fabricate a result.
# 14. You are a PSX data assistant, not a financial advisor.
# """.strip()

#     # ------------------------------------------------------------------
#     # LLM
#     # ------------------------------------------------------------------

#     async def _ask_llm(
#         self,
#         client: Any,
#         messages: list[dict[str, Any]],
#         tools: list[dict[str, Any]],
#     ) -> Any:
#         return await client.chat.completions.create(
#             model=LLM_MODEL,
#             messages=messages,
#             tools=tools or None,
#             tool_choice="auto" if tools else None,
#         )

#     @staticmethod
#     def _parse_tool_arguments(
#         raw_arguments: str | None,
#     ) -> dict[str, Any]:
#         raw_arguments = raw_arguments or "{}"

#         try:
#             parsed = json.loads(raw_arguments)
#         except json.JSONDecodeError as exc:
#             raise ValueError(
#                 f"Invalid JSON tool arguments: {exc}"
#             ) from exc

#         if not isinstance(parsed, dict):
#             raise ValueError(
#                 "Tool arguments must be a JSON object."
#             )

#         return parsed

#     # ------------------------------------------------------------------
#     # Main async flow
#     # ------------------------------------------------------------------

#     async def _chat_async(
#         self,
#         user_message: str,
#         history: list | None = None,
#     ) -> str:
#         self.last_tool = None
#         self.last_arguments = {}
#         self.last_debug = None

#         try:

#             async with mcp_session() as session:


#                     await self._load_tools(session)

#                     # --------------------------------------------------
#                     # Deterministic route for common PSX requests.
#                     # Crucially, this uses the SAME async MCP session.
#                     # --------------------------------------------------
#                     direct_tool, direct_arguments = (
#                         await self._detect_direct_tool(
#                             session,
#                             user_message,
#                         )
#                     )

#                     if direct_tool:
#                         try:
#                             result = await self._call_tool(
#                                 session,
#                                 direct_tool,
#                                 direct_arguments,
#                             )

#                             return self._format_tool_result(
#                                 direct_tool,
#                                 result,
#                             )

#                         except Exception:
#                             # Fall through to the LLM route.
#                             pass

#                     llm_client = create_llm_client()
#                     openai_tools = self._openai_tools()

#                     messages: list[dict[str, Any]] = [
#                         {
#                             "role": "system",
#                             "content": self._system_prompt(),
#                         }
#                     ]

#                     if history:
#                         for item in history:
#                             if not isinstance(item, dict):
#                                 continue

#                             role = item.get("role")
#                             content = item.get("content")

#                             if (
#                                 role in {"user", "assistant"}
#                                 and content
#                             ):
#                                 messages.append(
#                                     {
#                                         "role": role,
#                                         "content": str(content),
#                                     }
#                                 )

#                     messages.append(
#                         {
#                             "role": "user",
#                             "content": user_message,
#                         }
#                     )

#                     total_tool_calls = 0

#                     for _ in range(MAX_TOOL_ITERATIONS):
#                         response = await self._ask_llm(
#                             llm_client,
#                             messages,
#                             openai_tools,
#                         )

#                         if not response.choices:
#                             return "I could not generate a response."

#                         message = response.choices[0].message
#                         tool_calls = getattr(
#                             message,
#                             "tool_calls",
#                             None,
#                         )

#                         if not tool_calls:
#                             return (
#                                 message.content
#                                 or "I could not generate a response."
#                             )

#                         # Reproduce the assistant tool-call message exactly
#                         # enough for the next Groq request.
#                         assistant_message: dict[str, Any] = {
#                             "role": "assistant",
#                             "content": message.content or "",
#                             "tool_calls": [],
#                         }

#                         for tool_call in tool_calls:
#                             function = tool_call.function

#                             assistant_message["tool_calls"].append(
#                                 {
#                                     "id": tool_call.id,
#                                     "type": "function",
#                                     "function": {
#                                         "name": function.name,
#                                         "arguments": (
#                                             function.arguments or "{}"
#                                         ),
#                                     },
#                                 }
#                             )

#                         messages.append(assistant_message)

#                         for tool_call in tool_calls:
#                             total_tool_calls += 1

#                             if total_tool_calls > MAX_TOOL_CALLS:
#                                 return (
#                                     "The request required too many tool calls "
#                                     "and was stopped safely."
#                                 )

#                             function = tool_call.function
#                             tool_name = function.name

#                             try:
#                                 arguments = self._parse_tool_arguments(
#                                     function.arguments
#                                 )

#                                 if tool_name not in self.tool_map:
#                                     raise ValueError(
#                                         f"Unknown MCP tool requested: {tool_name}"
#                                     )

#                                 tool_result = await self._call_tool(
#                                     session,
#                                     tool_name,
#                                     arguments,
#                                 )

#                                 llm_content = self._tool_result_for_llm(
#                                     tool_name,
#                                     tool_result,
#                                 )

#                             except Exception as tool_error:
#                                 self.last_debug = {
#                                     "status": "error",
#                                     "tool": tool_name,
#                                     "arguments": (
#                                         arguments
#                                         if "arguments" in locals()
#                                         else {}
#                                     ),
#                                     "result_received": False,
#                                     "error": str(tool_error),
#                                 }

#                                 llm_content = json.dumps(
#                                     {
#                                         "tool": tool_name,
#                                         "error": str(tool_error),
#                                     },
#                                     ensure_ascii=False,
#                                 )

#                             messages.append(
#                                 {
#                                     "role": "tool",
#                                     "tool_call_id": tool_call.id,
#                                     "name": tool_name,
#                                     "content": llm_content,
#                                 }
#                             )

#                     return (
#                         "I was unable to complete the request within "
#                         "the allowed tool-call limit."
#                     )

#         except Exception as error:
#             self.last_debug = {
#                 "status": "connection_error",
#                 "tool": self.last_tool,
#                 "arguments": self.last_arguments,
#                 "result_received": False,
#                 "error": str(error),
#             }

#             # Do not expose raw internal stack/error details to end users.
#             return (
#                 "I could not retrieve the requested PSX data right now. "
#                 "Please try again."
#             )

#     # ------------------------------------------------------------------
#     # Public sync API for Streamlit / scripts
#     # ------------------------------------------------------------------

#     def chat(
#         self,
#         user_message: str,
#         history: list | None = None,
#     ) -> str:
#         try:
#             asyncio.get_running_loop()
#         except RuntimeError:
#             return asyncio.run(
#                 self._chat_async(
#                     user_message=user_message,
#                     history=history,
#                 )
#             )

#         raise RuntimeError(
#             "chat() cannot be called from an active event loop. "
#             "Use: await PSXChatbot()._chat_async(...)"
#         )


# def ask_chatbot(
#     user_message: str,
#     history: list | None = None,
# ) -> dict[str, Any]:
#     """
#     Stateless application entry point.

#     A fresh PSXChatbot is created per request so mutable MCP/debug
#     state is not shared between Streamlit users.
#     """
#     chatbot = PSXChatbot()
#     answer = chatbot.chat(
#         user_message=user_message,
#         history=history,
#     )

#     return {
#         "answer": answer,
#         "tool": chatbot.last_tool,
#         "arguments": chatbot.last_arguments,
#         "debug": chatbot.last_debug,
#     }



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

MAX_TOOL_ITERATIONS = int(
    os.getenv("MAX_TOOL_ITERATIONS", "6")
)

MAX_TOOL_CALLS = int(
    os.getenv("MAX_TOOL_CALLS", "12")
)


class PSXChatbot:
    """
    PSX chatbot orchestrator for LLM + MCP.

    The chatbot:
    - discovers MCP tools dynamically
    - handles simple requests deterministically
    - supports multi-step tool calling
    - supports mixed questions
    - preserves conversation context
    - resolves industries from live PSX data
    - verifies stock symbols before answering
    """

    # ------------------------------------------------------------------
    # Common words ignored during industry matching
    # ------------------------------------------------------------------

    _INDUSTRY_STOPWORDS = {
        "show",
        "list",
        "give",
        "tell",
        "find",
        "get",
        "stocks",
        "stock",
        "shares",
        "share",
        "sector",
        "industry",
        "industries",
        "what",
        "which",
        "where",
        "how",
        "current",
        "price",
        "prices",
        "change",
        "changes",
        "volume",
        "highest",
        "lowest",
        "top",
        "bottom",
        "best",
        "worst",
        "please",
        "me",
        "the",
        "for",
        "in",
        "of",
        "by",
        "and",
        "or",
        "on",
        "to",
        "from",
        "with",
        "now",
        "then",
        "also",
    }

    # ------------------------------------------------------------------
    # Industry wording aliases
    # ------------------------------------------------------------------

    _INDUSTRY_ALIASES = {
        "banking": {"bank"},
        "banks": {"bank"},
        "bank": {"bank"},
        "technology": {"technology"},
        "tech": {"technology"},
        "textile": {"textile"},
        "textiles": {"textile"},
        "pharma": {"pharmaceutical"},
        "pharmaceutical": {"pharmaceutical"},
        "pharmaceuticals": {"pharmaceutical"},
        "chemical": {"chemical"},
        "chemicals": {"chemical"},
        "automobile": {"automobile"},
        "automobiles": {"automobile"},
        "auto": {"automobile"},
        "automotive": {"automobile"},
        "insurance": {"insurance"},
        "cement": {"cement"},
        "fertilizer": {"fertilizer"},
        "fertilizers": {"fertilizer"},
        "food": {"food"},
        "paper": {"paper"},
        "power": {"power"},
        "property": {"property"},
        "real estate": {"real", "estate"},
        "refinery": {"refinery"},
        "refineries": {"refinery"},
        "tobacco": {"tobacco"},
        "transport": {"transport"},
        "leather": {"leather"},
        "jute": {"jute"},
        "glass": {"glass"},
        "ceramics": {"ceramic"},
        "cable": {"cable"},
        "engineering": {"engineering"},
        "sugar": {"sugar"},
        "woollen": {"woollen"},
        "wool": {"woollen"},
        "jute": {"jute"},
        "mutual fund": {"mutual", "fund"},
        "mutual funds": {"mutual", "fund"},
    }

    # ------------------------------------------------------------------
    # Industry keywords that can help route a stock query.
    #
    # These are only routing hints.
    # Final stock/industry data must still come from MCP.
    # ------------------------------------------------------------------

    _STOCK_NAME_INDUSTRY_HINTS = {
        "bank": {"bank"},
        "insurance": {"insurance"},
        "cement": {"cement"},
        "fertilizer": {"fertilizer"},
        "chemical": {"chemical"},
        "pharmaceutical": {"pharmaceutical"},
        "pharma": {"pharmaceutical"},
        "textile": {"textile"},
        "spinning": {"spinning"},
        "weaving": {"weaving"},
        "composite": {"composite"},
        "power": {"power"},
        "energy": {"oil", "gas"},
        "oil": {"oil"},
        "petroleum": {"oil"},
        "refinery": {"refinery"},
        "tobacco": {"tobacco"},
        "sugar": {"sugar"},
        "jute": {"jute"},
        "leather": {"leather"},
        "engineering": {"engineering"},
        "glass": {"glass"},
        "ceramic": {"ceramic"},
        "paper": {"paper"},
        "packaging": {"packaging"},
        "automobile": {"automobile"},
        "motor": {"automobile"},
        "transport": {"transport"},
        "technology": {"technology"},
        "communication": {"communication"},
        "real estate": {"real", "estate"},
        "property": {"property"},
    }

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self.tools: list[Any] = []
        self.tool_map: dict[str, Any] = {}

        self.last_tool: str | None = None
        self.last_arguments: dict[str, Any] = {}
        self.last_debug: dict[str, Any] | None = None

        self.requested_symbols: set[str] = set()

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = str(text).lower().strip()
        return re.sub(r"\s+", " ", text)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(
            r"[a-z0-9]+",
            text.lower(),
        )

    @classmethod
    def _meaningful_tokens(
        cls,
        text: str,
    ) -> set[str]:
        return {
            token
            for token in cls._tokens(text)
            if len(token) >= 3
            and token not in cls._INDUSTRY_STOPWORDS
        }

    # ------------------------------------------------------------------
    # Detect whether a query is mixed / multi-intent
    # ------------------------------------------------------------------

    @classmethod
    def _is_mixed_request(
        cls,
        question: str,
    ) -> bool:
        q = cls._normalize_text(question)

        ranking_change = any(
            phrase in q
            for phrase in (
                "top change",
                "top 10 change",
                "highest change",
                "top gainer",
                "top gainers",
                "bottom change",
                "bottom 10 change",
                "lowest change",
                "loser",
                "losers",
            )
        )

        ranking_volume = any(
            phrase in q
            for phrase in (
                "top volume",
                "highest volume",
                "most volume",
                "bottom volume",
                "lowest volume",
                "least volume",
            )
        )

        stock_specific = any(
            phrase in q
            for phrase in (
                "stock price",
                "share price",
                "current price",
                "market price",
                "stock quote",
                "share quote",
                "trading at",
                "how is",
                "performing",
            )
        )

        stock_listing = any(
            phrase in q
            for phrase in (
                "show stocks",
                "list stocks",
                "stocks in",
                "shares in",
                "show shares",
            )
        )

        intent_count = sum(
            [
                ranking_change,
                ranking_volume,
                stock_specific,
                stock_listing,
            ]
        )

        connectors = any(
            connector in q
            for connector in (
                " and ",
                " also ",
                " then ",
                " plus ",
                " as well as ",
                ",",
            )
        )

        if intent_count >= 2:
            return True

        if connectors and intent_count >= 1:
            return True

        return False

    # ------------------------------------------------------------------
    # MCP
    # ------------------------------------------------------------------

    async def _load_tools(
        self,
        session: Any,
    ) -> list[Any]:
        response = await session.list_tools()

        self.tools = list(
            response.tools or []
        )

        self.tool_map = {
            tool.name: tool
            for tool in self.tools
        }

        return self.tools

    async def _call_tool(
        self,
        session: Any,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        arguments = arguments or {}

        if tool_name not in self.tool_map:
            raise ValueError(
                f"Unknown MCP tool: {tool_name}"
            )

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
                    (
                        time.perf_counter()
                        - started
                    )
                    * 1000,
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
                    (
                        time.perf_counter()
                        - started
                    )
                    * 1000,
                    2,
                ),
                "result_received": False,
                "error": str(exc),
            }

            raise

    # ------------------------------------------------------------------
    # Extract MCP result
    # ------------------------------------------------------------------

    def _extract_tool_result(
        self,
        result: Any,
    ) -> Any:
        if result is None:
            return None

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
                extracted.append(
                    text_value
                )
            else:
                extracted.append(
                    item
                )

        if len(extracted) == 1:
            value = extracted[0]

            if isinstance(value, str):
                try:
                    return json.loads(
                        value
                    )
                except (
                    json.JSONDecodeError,
                    TypeError,
                ):
                    return value

            return value

        return extracted

    # ------------------------------------------------------------------
    # Generic list extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_data_list(
        data: Any,
    ) -> list[Any]:
        if isinstance(data, list):
            return data

        if not isinstance(data, dict):
            return []

        for key in (
            "data",
            "results",
            "industries",
            "symbols",
            "stocks",
        ):
            value = data.get(key)

            if isinstance(value, list):
                return value

        return []

    # ------------------------------------------------------------------
    # Extract industry names from live MCP result
    # ------------------------------------------------------------------

    def _extract_industries(
        self,
        data: Any,
    ) -> list[str]:
        items = self._extract_data_list(
            data
        )

        industries: list[str] = []

        for item in items:
            if isinstance(item, dict):
                name = (
                    item.get("industry")
                    or item.get("name")
                    or item.get("sector")
                    or item.get("sector_name")
                )
            else:
                name = str(item)

            if name:
                industries.append(
                    str(name).strip()
                )

        return list(
            dict.fromkeys(industries)
        )

    # ------------------------------------------------------------------
    # Resolve industry using live MCP catalog
    #
    # Returns:
    #   (exact_match, ambiguous_matches)
    # ------------------------------------------------------------------

    async def _resolve_industry_hint(
        self,
        session: Any,
        text: str,
    ) -> tuple[str | None, list[str]]:
        try:
            result = await self._call_tool(
                session,
                "get_industries",
                {},
            )

            data = self._extract_tool_result(
                result
            )

            industry_names = (
                self._extract_industries(
                    data
                )
            )

            candidates = [
                (
                    self._normalize_text(name),
                    name,
                )
                for name in industry_names
            ]

            q = self._normalize_text(
                text
            )

            # ----------------------------------------------------------
            # Exact phrase match
            # ----------------------------------------------------------

            exact = [
                original
                for normalized, original
                in candidates
                if normalized
                and normalized in q
            ]

            if len(exact) == 1:
                return exact[0], []

            if len(exact) > 1:
                return None, exact

            # ----------------------------------------------------------
            # Alias matching
            # ----------------------------------------------------------

            alias_matches: list[str] = []

            for alias, required_tokens in (
                self._INDUSTRY_ALIASES.items()
            ):
                if alias not in q:
                    continue

                for normalized, original in candidates:
                    candidate_tokens = set(
                        self._tokens(
                            normalized
                        )
                    )

                    if required_tokens.issubset(
                        candidate_tokens
                    ):
                        alias_matches.append(
                            original
                        )

            alias_matches = list(
                dict.fromkeys(
                    alias_matches
                )
            )

            if len(alias_matches) == 1:
                return alias_matches[0], []

            if len(alias_matches) > 1:
                return None, alias_matches

            # ----------------------------------------------------------
            # Token overlap
            # ----------------------------------------------------------

            question_tokens = (
                self._meaningful_tokens(
                    q
                )
            )

            scored: list[
                tuple[float, str]
            ] = []

            for normalized, original in (
                candidates
            ):
                industry_tokens = {
                    token
                    for token in self._tokens(
                        normalized
                    )
                    if token not in {
                        "and",
                        "the",
                        "of",
                    }
                }

                overlap = (
                    question_tokens
                    & industry_tokens
                )

                if not overlap:
                    continue

                score = (
                    len(overlap)
                    / max(
                        len(industry_tokens),
                        1,
                    )
                )

                scored.append(
                    (
                        score,
                        original,
                    )
                )

            scored.sort(
                key=lambda item: item[0],
                reverse=True,
            )

            if scored:
                best_score = scored[0][0]

                strong = [
                    name
                    for score, name
                    in scored
                    if score >= 0.5
                    and score >= (
                        best_score - 0.10
                    )
                ]

                strong = list(
                    dict.fromkeys(
                        strong
                    )
                )

                if len(strong) == 1:
                    return strong[0], []

                if len(strong) > 1:
                    return None, strong

            # ----------------------------------------------------------
            # Fuzzy fallback
            # ----------------------------------------------------------

            question_words = [
                token
                for token in question_tokens
                if len(token) >= 4
            ]

            fuzzy_matches: list[str] = []

            for normalized, original in (
                candidates
            ):
                industry_tokens = [
                    token
                    for token in self._tokens(
                        normalized
                    )
                    if len(token) >= 4
                ]

                for industry_token in (
                    industry_tokens
                ):
                    for word in (
                        question_words
                    ):
                        ratio = (
                            difflib.SequenceMatcher(
                                None,
                                industry_token,
                                word,
                            ).ratio()
                        )

                        if ratio >= 0.86:
                            fuzzy_matches.append(
                                original
                            )
                            break

            fuzzy_matches = list(
                dict.fromkeys(
                    fuzzy_matches
                )
            )

            if len(fuzzy_matches) == 1:
                return fuzzy_matches[0], []

            if len(fuzzy_matches) > 1:
                return None, fuzzy_matches

        except Exception:
            return None, []

        return None, []

    async def _find_industry_in_question(
        self,
        session: Any,
        question: str,
    ) -> str | None:
        industry, ambiguous = (
            await self._resolve_industry_hint(
                session,
                question,
            )
        )

        if ambiguous:
            return None

        return industry

    # ------------------------------------------------------------------
    # Recent user context
    # ------------------------------------------------------------------

    @staticmethod
    def _recent_user_context(
        history: list | None,
    ) -> str:
        if not history:
            return ""

        recent: list[str] = []

        for item in reversed(
            history
        ):
            if not isinstance(
                item,
                dict,
            ):
                continue

            if (
                item.get("role")
                != "user"
            ):
                continue

            content = item.get(
                "content"
            )

            if content:
                recent.append(
                    str(content)
                )

            if len(recent) >= 3:
                break

        return " ".join(
            reversed(recent)
        )

    # ------------------------------------------------------------------
    # Deterministic direct routing
    #
    # Used only for simple one-intent requests.
    # Mixed/stock-specific questions go through LLM tool calling.
    # ------------------------------------------------------------------

    async def _detect_direct_tool(
        self,
        session: Any,
        question: str,
        history: list | None = None,
    ) -> tuple[
        str | None,
        dict[str, Any],
    ]:
        q = self._normalize_text(
            question
        )

        # Never use deterministic shortcut
        # for mixed questions.
        if self._is_mixed_request(
            question
        ):
            return None, {}

        # --------------------------------------------------------------
        # Symbols
        # --------------------------------------------------------------

        if (
            "list symbols" in q
            or "all symbols" in q
            or "stock symbols" in q
            or q in {
                "symbols",
                "symbol",
            }
        ):
            return "get_symbols", {}

        # --------------------------------------------------------------
        # Industries
        # --------------------------------------------------------------

        if (
            "list industries" in q
            or "all industries" in q
            or q in {
                "industries",
                "industry",
            }
        ):
            return "get_industries", {}

        # --------------------------------------------------------------
        # Stock-specific queries should use the LLM route because
        # they may require:
        #
        # symbol → industry → get_stocks → row lookup
        # --------------------------------------------------------------

        stock_specific = any(
            phrase in q
            for phrase in (
                "stock price",
                "share price",
                "current price",
                "market price",
                "stock quote",
                "share quote",
                "trading at",
                "how is",
                "performing",
                "tell me about",
            )
        )

        if stock_specific:
            return None, {}

        # --------------------------------------------------------------
        # Resolve industry from current question.
        # If absent, use recent user context for follow-up queries.
        # --------------------------------------------------------------

        industry = None
        ambiguous: list[str] = []

        industry_signal = any(
            token in q
            for token in (
                "bank",
                "banking",
                "banks",
                "textile",
                "technology",
                "tech",
                "pharma",
                "pharmaceutical",
                "chemical",
                "chemicals",
                "cement",
                "fertilizer",
                "insurance",
                "automobile",
                "automotive",
                "oil",
                "gas",
                "paper",
                "power",
                "property",
                "real estate",
                "transport",
                "engineering",
                "sugar",
                "tobacco",
                "leather",
                "jute",
                "glass",
                "ceramic",
                "refinery",
                "wool",
                "sector",
                "industry",
            )
        )

        if industry_signal:
            industry, ambiguous = (
                await self._resolve_industry_hint(
                    session,
                    question,
                )
            )

        if (
            industry is None
            and not ambiguous
        ):
            recent_context = (
                self._recent_user_context(
                    history
                )
            )

            if recent_context:
                industry, ambiguous = (
                    await self._resolve_industry_hint(
                        session,
                        recent_context,
                    )
                )

        # --------------------------------------------------------------
        # Ambiguous industry:
        # do not guess.
        # Let LLM route produce a clarification.
        # --------------------------------------------------------------

        if ambiguous:
            return None, {}

        # --------------------------------------------------------------
        # Simple "show X stocks"
        # --------------------------------------------------------------

        stock_listing = any(
            phrase in q
            for phrase in (
                "show stocks",
                "show shares",
                "list stocks",
                "list shares",
                "stocks in",
                "shares in",
            )
        )

        if stock_listing:
            if industry:
                return (
                    "get_stocks",
                    {
                        "industry": industry
                    },
                )

            return None, {}

        # --------------------------------------------------------------
        # Top change
        # --------------------------------------------------------------

        if any(
            phrase in q
            for phrase in (
                "top change",
                "top 10 change",
                "highest change",
                "top gainers",
                "top gainer",
            )
        ):
            return (
                "get_top_change",
                (
                    {
                        "industry": industry
                    }
                    if industry
                    else {}
                ),
            )

        # --------------------------------------------------------------
        # Bottom change
        # --------------------------------------------------------------

        if any(
            phrase in q
            for phrase in (
                "bottom change",
                "bottom 10 change",
                "lowest change",
                "top losers",
                "losers",
            )
        ):
            return (
                "get_bottom_change",
                (
                    {
                        "industry": industry
                    }
                    if industry
                    else {}
                ),
            )

        # --------------------------------------------------------------
        # Top volume
        # --------------------------------------------------------------

        if any(
            phrase in q
            for phrase in (
                "top volume",
                "highest volume",
                "most volume",
            )
        ):
            return (
                "get_top_volume",
                (
                    {
                        "industry": industry
                    }
                    if industry
                    else {}
                ),
            )

        # --------------------------------------------------------------
        # Bottom volume
        # --------------------------------------------------------------

        if any(
            phrase in q
            for phrase in (
                "bottom volume",
                "lowest volume",
                "least volume",
            )
        ):
            return (
                "get_bottom_volume",
                (
                    {
                        "industry": industry
                    }
                    if industry
                    else {}
                ),
            )

        return None, {}

    # ------------------------------------------------------------------
    # Stock symbol extraction
    # ------------------------------------------------------------------

    def _extract_symbol_records(
        self,
        data: Any,
    ) -> list[dict[str, Any]]:
        items = self._extract_data_list(
            data
        )

        records: list[
            dict[str, Any]
        ] = []

        for item in items:
            if isinstance(item, dict):
                records.append(item)
            else:
                records.append(
                    {
                        "symbol": str(
                            item
                        )
                    }
                )

        return records

    async def _find_requested_symbols(
        self,
        session: Any,
        question: str,
        history: list | None = None,
    ) -> tuple[
        list[str],
        list[str],
        str | None,
    ]:
        """
        Verify possible stock symbols against live get_symbols() data.

        Returns:
            matched_symbols
            matched_names
            routing_hint
        """

        combined = (
            question
            + " "
            + self._recent_user_context(
                history
            )
        )

        q_lower = self._normalize_text(
            combined
        )

        # Avoid unnecessary get_symbols call
        # for unrelated requests.
        stock_signal = any(
            phrase in q_lower
            for phrase in (
                "stock price",
                "share price",
                "current price",
                "market price",
                "stock quote",
                "share quote",
                "trading at",
                "stock",
                "stocks",
                "share",
                "shares",
                "performing",
                "volume",
            )
        )

        uppercase_symbols = re.findall(
            r"\b[A-Z]{2,6}\b",
            combined,
        )

        stock_signal = (
            stock_signal
            or bool(
                uppercase_symbols
            )
        )

        if not stock_signal:
            return [], [], None

        try:
            result = await self._call_tool(
                session,
                "get_symbols",
                {},
            )

            data = self._extract_tool_result(
                result
            )

            records = (
                self._extract_symbol_records(
                    data
                )
            )

            normalized_q = (
                self._normalize_text(
                    combined
                )
            )

            matched_symbols: list[str] = []
            matched_names: list[str] = []

            for record in records:
                symbol = str(
                    record.get(
                        "symbol"
                    )
                    or ""
                ).strip().upper()

                if not symbol:
                    continue

                name = str(
                    record.get(
                        "name"
                    )
                    or ""
                ).strip()

                # ------------------------------------------------------
                # Exact symbol match
                # ------------------------------------------------------

                if re.search(
                    rf"\b{re.escape(symbol.lower())}\b",
                    normalized_q,
                ):
                    matched_symbols.append(
                        symbol
                    )

                    if name:
                        matched_names.append(
                            name
                        )

                    continue

                # ------------------------------------------------------
                # Company-name match when available
                # ------------------------------------------------------

                if name:
                    normalized_name = (
                        self._normalize_text(
                            name
                        )
                    )

                    important_name_tokens = [
                        token
                        for token in self._tokens(
                            normalized_name
                        )
                        if token
                        not in {
                            "limited",
                            "ltd",
                            "plc",
                            "company",
                            "the",
                        }
                    ]

                    if (
                        len(
                            important_name_tokens
                        )
                        >= 1
                    ):
                        name_hits = sum(
                            1
                            for token in important_name_tokens
                            if token in normalized_q
                        )

                        required = (
                            1
                            if len(
                                important_name_tokens
                            )
                            == 1
                            else 2
                        )

                        if (
                            name_hits
                            >= min(
                                required,
                                len(
                                    important_name_tokens
                                ),
                            )
                        ):
                            matched_symbols.append(
                                symbol
                            )
                            matched_names.append(
                                name
                            )

            matched_symbols = list(
                dict.fromkeys(
                    matched_symbols
                )
            )

            matched_names = list(
                dict.fromkeys(
                    matched_names
                )
            )

            self.requested_symbols = set(
                matched_symbols
            )

            # ----------------------------------------------------------
            # Routing hint from symbol metadata if available.
            #
            # This is only a query-routing hint.
            # The final stock row must still verify it.
            # ----------------------------------------------------------

            routing_hint: str | None = None

            live_industry_candidates: list[
                str
            ] = []

            for record in records:
                symbol = str(
                    record.get(
                        "symbol"
                    )
                    or ""
                ).strip().upper()

                if symbol not in matched_symbols:
                    continue

                sector = (
                    record.get(
                        "sector_name"
                    )
                    or record.get(
                        "industry"
                    )
                    or record.get(
                        "sector"
                    )
                )

                if sector:
                    live_industry_candidates.append(
                        str(sector).strip()
                    )

                name = str(
                    record.get(
                        "name"
                    )
                    or ""
                ).strip()

                if name:
                    name_lower = (
                        self._normalize_text(
                            name
                        )
                    )

                    for keyword, token_set in (
                        self._STOCK_NAME_INDUSTRY_HINTS.items()
                    ):
                        if keyword not in name_lower:
                            continue

                        # We only return a textual hint here.
                        # The LLM must verify using MCP tool output.
                        routing_hint = (
                            " ".join(
                                sorted(
                                    token_set
                                )
                            )
                        )

                        break

            if live_industry_candidates:
                routing_hint = (
                    live_industry_candidates[0]
                )

            return (
                matched_symbols,
                matched_names,
                routing_hint,
            )

        except Exception:
            self.requested_symbols = set()

            return [], [], None

    # ------------------------------------------------------------------
    # Tool schema conversion
    # ------------------------------------------------------------------

    def _openai_tools(
        self,
    ) -> list[dict[str, Any]]:
        openai_tools: list[
            dict[str, Any]
        ] = []

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
                            getattr(
                                tool,
                                "description",
                                None,
                            )
                            or (
                                f"PSX MCP tool: "
                                f"{tool.name}"
                            )
                        ),
                        "parameters": input_schema,
                    },
                }
            )

        return openai_tools

    # ------------------------------------------------------------------
    # User-facing formatting
    # ------------------------------------------------------------------

    def _format_tool_result(
        self,
        tool_name: str,
        result: Any,
    ) -> str:
        data = self._extract_tool_result(
            result
        )

        try:
            if tool_name == "get_symbols":
                return format_symbols(
                    data
                )

            if tool_name == "get_industries":
                return format_industries(
                    data
                )

            if tool_name == "get_stocks":
                return format_stock_data(
                    data
                )

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
                ensure_ascii=False,
                default=str,
            )
        except (
            TypeError,
            ValueError,
        ):
            return str(data)

    # ------------------------------------------------------------------
    # Compact result for LLM
    #
    # Important:
    # The user-facing formatter is separate.
    # The LLM does NOT need every PSX field.
    # ------------------------------------------------------------------

    def _tool_result_for_llm(
        self,
        tool_name: str,
        result: Any,
    ) -> str:
        data = self._extract_tool_result(
            result
        )

        if isinstance(
            data,
            str,
        ):
            return data

        if tool_name == "get_industries":
            names = self._extract_industries(
                data
            )

            return json.dumps(
                {
                    "tool": tool_name,
                    "count": len(names),
                    "industries": names,
                },
                ensure_ascii=False,
            )

        if tool_name == "get_symbols":
            records = (
                self._extract_symbol_records(
                    data
                )
            )

            if self.requested_symbols:
                records = [
                    record
                    for record in records
                    if str(
                        record.get(
                            "symbol"
                        )
                        or ""
                    ).upper()
                    in self.requested_symbols
                ]

            compact_symbols = []

            for record in records:
                compact_symbols.append(
                    {
                        "symbol": record.get(
                            "symbol"
                        ),
                        "name": record.get(
                            "name"
                        ),
                    }
                )

            return json.dumps(
                {
                    "tool": tool_name,
                    "count": (
                        data.get(
                            "count"
                        )
                        if isinstance(
                            data,
                            dict,
                        )
                        else len(compact_symbols)
                    ),
                    "matches": compact_symbols,
                },
                ensure_ascii=False,
                default=str,
            )

        # --------------------------------------------------------------
        # Extract stock/ranking rows
        # --------------------------------------------------------------

        rows = self._extract_data_list(
            data
        )

        if rows:
            compact_rows: list[
                dict[str, Any]
            ] = []

            for row in rows:
                if not isinstance(
                    row,
                    dict,
                ):
                    continue

                compact = {
                    "symbol": row.get(
                        "symbol"
                    ),
                    "name": row.get(
                        "name"
                    ),
                    "current_price": row.get(
                        "current_price"
                    ),
                    "ldcp": row.get(
                        "ldcp"
                    ),
                    "change_value": row.get(
                        "change_value"
                    ),
                    "change_percent": row.get(
                        "change_percent"
                    ),
                    "volume": row.get(
                        "volume"
                    ),
                    "sector_name": row.get(
                        "sector_name"
                    ),
                }

                # ------------------------------------------------------
                # For individual-stock lookups,
                # only send matching rows to the LLM.
                # ------------------------------------------------------

                if (
                    tool_name == "get_stocks"
                    and self.requested_symbols
                ):
                    symbol = str(
                        compact.get(
                            "symbol"
                        )
                        or ""
                    ).upper()

                    if symbol not in (
                        self.requested_symbols
                    ):
                        continue

                compact_rows.append(
                    compact
                )

            payload: dict[
                str,
                Any,
            ] = {
                "tool": tool_name,
                "count": len(rows),
            }

            if (
                tool_name == "get_stocks"
                and self.requested_symbols
            ):
                payload[
                    "requested_symbols"
                ] = sorted(
                    self.requested_symbols
                )

                payload[
                    "matches"
                ] = compact_rows

                payload[
                    "match_count"
                ] = len(
                    compact_rows
                )
            else:
                payload[
                    "data"
                ] = compact_rows

            return json.dumps(
                payload,
                ensure_ascii=False,
                default=str,
            )

        # --------------------------------------------------------------
        # Fallback for arbitrary structured data
        # --------------------------------------------------------------

        try:
            return json.dumps(
                {
                    "tool": tool_name,
                    "data": data,
                },
                ensure_ascii=False,
                default=str,
            )
        except (
            TypeError,
            ValueError,
        ):
            return str(data)

    # ------------------------------------------------------------------
    # Dynamic prompt
    # ------------------------------------------------------------------

    @staticmethod
    def _system_prompt() -> str:
        return """
You are a Pakistan Stock Exchange (PSX) data chatbot connected to live PSX data through MCP tools.

Rules:

1. Use MCP tools for every PSX fact. Never invent current prices, changes, volumes, industries, symbols, or company data.
2. MCP tool results are the source of truth.
3. Answer every part of a mixed question. Do not stop after completing only one clause.
4. You may call multiple MCP tools and continue for multiple rounds when needed.
5. For a specific stock:
   - verify the symbol against MCP data when possible;
   - retrieve the stock row through get_stocks;
   - use the exact returned current_price, change_percent, change_value, volume, and other returned fields;
   - do not say that a direct stock-price tool is missing merely because get_stocks requires an industry.
6. When a specific stock is requested but no industry is stated:
   - use the most plausible industry only as a routing hypothesis;
   - call get_stocks with that industry;
   - verify that the requested symbol exists in the returned rows;
   - if it is not present, try another plausible industry when reasonable;
   - only report unavailable after the valid tool routes are exhausted.
7. Never present an inferred industry as verified until the MCP stock result confirms it.
8. If the user explicitly gives an industry, use the exact industry value from the live PSX industry catalog.
9. If an industry term maps to multiple live industries, do not guess. Ask the user to choose.
10. Follow-up questions may depend on the recent conversation. Reuse a clear stock, industry, ranking, or metric context from earlier messages.
11. For ranking requests:
    - top change = highest change percentage;
    - bottom change = lowest change percentage;
    - top volume = highest trading volume;
    - bottom volume = lowest trading volume.
12. Preserve MCP values exactly. Do not round or alter values unless only formatting for readability.
13. If tool output is empty or does not contain the requested symbol, do not fabricate a result.
14. Greetings and casual conversation do not require MCP tools.
15. Give direct, concise answers. Use markdown tables for multiple stock rows when useful.
16. Do not provide guaranteed returns, personalized investment advice, or unsupported recommendations.
""".strip()

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    async def _ask_llm(
        self,
        client: Any,
        messages: list[
            dict[str, Any]
        ],
        tools: list[
            dict[str, Any]
        ],
    ) -> Any:
        return await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=tools or None,
            tool_choice=(
                "auto"
                if tools
                else None
            ),
            temperature=0,
        )

    # ------------------------------------------------------------------
    # Tool arguments parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tool_arguments(
        raw_arguments: str | None,
    ) -> dict[str, Any]:
        raw_arguments = (
            raw_arguments
            or "{}"
        )

        try:
            parsed = json.loads(
                raw_arguments
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid JSON tool arguments"
            ) from exc

        if not isinstance(
            parsed,
            dict,
        ):
            raise ValueError(
                "Tool arguments must be a JSON object."
            )

        return parsed

    # ------------------------------------------------------------------
    # Build dynamic context hints
    # ------------------------------------------------------------------

    async def _build_context_hints(
        self,
        session: Any,
        question: str,
        history: list | None,
    ) -> list[str]:
        hints: list[str] = []

        # --------------------------------------------------------------
        # Verify requested stock symbols when appropriate.
        # --------------------------------------------------------------

        (
            matched_symbols,
            matched_names,
            routing_hint,
        ) = await self._find_requested_symbols(
            session,
            question,
            history,
        )

        if matched_symbols:
            hints.append(
                "Live MCP symbol verification found: "
                + ", ".join(
                    matched_symbols
                )
                + "."
            )

            if matched_names:
                hints.append(
                    "Matching company names: "
                    + ", ".join(
                        matched_names
                    )
                    + "."
                )

            if routing_hint:
                hints.append(
                    "Routing hint only — verify through get_stocks before stating the industry: "
                    + routing_hint
                    + "."
                )

        # --------------------------------------------------------------
        # Resolve explicit/current industry.
        # --------------------------------------------------------------

        combined_current = question

        industry_signal = any(
            token in self._normalize_text(
                combined_current
            )
            for token in (
                "bank",
                "banking",
                "banks",
                "textile",
                "technology",
                "tech",
                "pharma",
                "pharmaceutical",
                "chemical",
                "chemicals",
                "cement",
                "fertilizer",
                "insurance",
                "automobile",
                "automotive",
                "oil",
                "gas",
                "paper",
                "power",
                "property",
                "real estate",
                "transport",
                "engineering",
                "sugar",
                "tobacco",
                "leather",
                "jute",
                "glass",
                "ceramic",
                "refinery",
                "wool",
                "sector",
                "industry",
            )
        )

        if industry_signal:
            industry, ambiguous = (
                await self._resolve_industry_hint(
                    session,
                    combined_current,
                )
            )

            if industry:
                hints.append(
                    "Current live industry match: "
                    + industry
                    + "."
                )

            if ambiguous:
                hints.append(
                    "The current industry wording is ambiguous. Valid live candidates are: "
                    + ", ".join(
                        ambiguous
                    )
                    + ". Do not guess; ask the user to choose."
                )

        # --------------------------------------------------------------
        # Follow-up industry context
        # --------------------------------------------------------------

        recent_user_context = (
            self._recent_user_context(
                history
            )
        )

        if recent_user_context:
            current_has_explicit_industry = (
                industry_signal
            )

            if not current_has_explicit_industry:
                previous_industry, previous_ambiguous = (
                    await self._resolve_industry_hint(
                        session,
                        recent_user_context,
                    )
                )

                if previous_industry:
                    hints.append(
                        "Recent conversation context suggests industry: "
                        + previous_industry
                        + ". Use it for a clear follow-up unless the user changes the subject."
                    )

                if previous_ambiguous:
                    hints.append(
                        "Recent conversation contains ambiguous industry context: "
                        + ", ".join(
                            previous_ambiguous
                        )
                        + ". Do not guess."
                    )

        return hints

    # ------------------------------------------------------------------
    # Main async chatbot flow
    # ------------------------------------------------------------------

    async def _chat_async(
        self,
        user_message: str,
        history: list | None = None,
    ) -> str:
        self.last_tool = None
        self.last_arguments = {}
        self.last_debug = None
        self.requested_symbols = set()

        try:
            async with mcp_session() as session:

                await self._load_tools(
                    session
                )

                # ------------------------------------------------------
                # Simple deterministic route.
                # ------------------------------------------------------

                (
                    direct_tool,
                    direct_arguments,
                ) = await self._detect_direct_tool(
                    session,
                    user_message,
                    history,
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
                        # Fall through to LLM route.
                        pass

                # ------------------------------------------------------
                # LLM route
                # ------------------------------------------------------

                llm_client = create_llm_client()
                openai_tools = (
                    self._openai_tools()
                )

                messages: list[
                    dict[str, Any]
                ] = [
                    {
                        "role": "system",
                        "content": self._system_prompt(),
                    }
                ]

                # ------------------------------------------------------
                # Preserve recent conversation
                # ------------------------------------------------------

                if history:
                    for item in history:
                        if not isinstance(
                            item,
                            dict,
                        ):
                            continue

                        role = item.get(
                            "role"
                        )

                        content = item.get(
                            "content"
                        )

                        if (
                            role
                            in {
                                "user",
                                "assistant",
                            }
                            and content
                        ):
                            messages.append(
                                {
                                    "role": role,
                                    "content": str(
                                        content
                                    ),
                                }
                            )

                # ------------------------------------------------------
                # Dynamic routing hints.
                # These are compact and only added when useful.
                # ------------------------------------------------------

                context_hints = (
                    await self._build_context_hints(
                        session,
                        user_message,
                        history,
                    )
                )

                if context_hints:
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                "Relevant routing context from live MCP lookup:\n"
                                + "\n".join(
                                    f"- {hint}"
                                    for hint in context_hints
                                )
                            ),
                        }
                    )

                messages.append(
                    {
                        "role": "user",
                        "content": user_message,
                    }
                )

                total_tool_calls = 0

                # ------------------------------------------------------
                # Multi-round tool-calling loop
                # ------------------------------------------------------

                for _ in range(
                    MAX_TOOL_ITERATIONS
                ):
                    response = await self._ask_llm(
                        llm_client,
                        messages,
                        openai_tools,
                    )

                    if not response.choices:
                        return (
                            "I could not generate a response."
                        )

                    message = (
                        response.choices[0].message
                    )

                    tool_calls = getattr(
                        message,
                        "tool_calls",
                        None,
                    )

                    # --------------------------------------------------
                    # No more tools → final chatbot answer
                    # --------------------------------------------------

                    if not tool_calls:
                        return (
                            message.content
                            or "I could not generate a response."
                        )

                    # --------------------------------------------------
                    # Preserve assistant tool call message
                    # --------------------------------------------------

                    assistant_message: dict[
                        str,
                        Any,
                    ] = {
                        "role": "assistant",
                        "content": (
                            message.content
                            or ""
                        ),
                        "tool_calls": [],
                    }

                    for tool_call in (
                        tool_calls
                    ):
                        function = (
                            tool_call.function
                        )

                        assistant_message[
                            "tool_calls"
                        ].append(
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": (
                                        function.name
                                    ),
                                    "arguments": (
                                        function.arguments
                                        or "{}"
                                    ),
                                },
                            }
                        )

                    messages.append(
                        assistant_message
                    )

                    # --------------------------------------------------
                    # Execute every tool requested in this round
                    # --------------------------------------------------

                    for tool_call in (
                        tool_calls
                    ):
                        total_tool_calls += 1

                        if (
                            total_tool_calls
                            > MAX_TOOL_CALLS
                        ):
                            return (
                                "The request required too many tool calls and was stopped safely."
                            )

                        function = (
                            tool_call.function
                        )

                        tool_name = (
                            function.name
                        )

                        arguments: dict[
                            str,
                            Any,
                        ] = {}

                        try:
                            arguments = (
                                self._parse_tool_arguments(
                                    function.arguments
                                )
                            )

                            if tool_name not in (
                                self.tool_map
                            ):
                                raise ValueError(
                                    "Unknown MCP tool requested: "
                                    + tool_name
                                )

                            # --------------------------------------------------
                            # For get_stocks, preserve exact stock filtering
                            # context when the user requested specific symbols.
                            # --------------------------------------------------

                            tool_result = (
                                await self._call_tool(
                                    session,
                                    tool_name,
                                    arguments,
                                )
                            )

                            llm_content = (
                                self._tool_result_for_llm(
                                    tool_name,
                                    tool_result,
                                )
                            )

                        except Exception as tool_error:

                            self.last_debug = {
                                "status": "error",
                                "tool": tool_name,
                                "arguments": arguments,
                                "result_received": False,
                                "error": str(
                                    tool_error
                                ),
                            }

                            llm_content = json.dumps(
                                {
                                    "tool": tool_name,
                                    "error": str(
                                        tool_error
                                    ),
                                },
                                ensure_ascii=False,
                            )

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": (
                                    tool_call.id
                                ),
                                "content": llm_content,
                            }
                        )

                return (
                    "I was unable to complete the request within the allowed tool-call limit."
                )

        except Exception as error:

            self.last_debug = {
                "status": "connection_error",
                "tool": self.last_tool,
                "arguments": self.last_arguments,
                "result_received": False,
                "error": str(error),
            }

            return (
                "I could not retrieve the requested PSX data right now. "
                "Please try again."
            )

    # ------------------------------------------------------------------
    # Public sync API
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


# ----------------------------------------------------------------------
# Public application entry point
# ----------------------------------------------------------------------

def ask_chatbot(
    user_message: str,
    history: list | None = None,
) -> dict[str, Any]:
    """
    Stateless application entry point.

    A fresh PSXChatbot is created per request so mutable debug state
    is isolated between Streamlit users.
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