# from __future__ import annotations

# import asyncio
# import difflib
# import json
# import os
# import re
# import threading
# import webbrowser
# from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
# from urllib.parse import parse_qs, urlparse

# import httpx2
# from dotenv import load_dotenv
# from pydantic import AnyUrl

# from mcp import ClientSession
# from mcp.client.auth import (
#     AuthorizationCodeResult,
#     OAuthClientProvider,
# )
# from mcp.client.streamable_http import (
#     streamable_http_client,
# )
# from mcp.shared.auth import (
#     OAuthClientInformationFull,
#     OAuthClientMetadata,
#     OAuthToken,
# )

# from chatbot.formatters import (
#     format_industries,
#     format_stock_data,
#     format_symbols,
#     format_top_bottom,
# )

# from chatbot.llm import create_llm_client


# load_dotenv()


# # =========================================================
# # CONFIG
# # =========================================================

# MCP_SERVER_URL = os.getenv(
#     "MCP_SERVER_URL",
#     "https://fluttering-blue-ox.fastmcp.app/mcp",
# )

# LLM_PROVIDER = os.getenv(
#     "LLM_PROVIDER",
#     "groq",
# ).lower()

# LLM_MODEL = os.getenv(
#     "LLM_MODEL",
#     "openai/gpt-oss-120b",
# )

# CALLBACK_HOST = "127.0.0.1"
# CALLBACK_PORT = 3030

# CALLBACK_URL = (
#     f"http://{CALLBACK_HOST}:{CALLBACK_PORT}/callback"
# )


# # =========================================================
# # TOKEN STORAGE
# # =========================================================

# class InMemoryTokenStorage:
#     """
#     Keeps OAuth tokens and client information
#     while the current Streamlit process is alive.
#     """

#     def __init__(self) -> None:
#         self.tokens: OAuthToken | None = None
#         self.client_info: (
#             OAuthClientInformationFull | None
#         ) = None

#     async def get_tokens(self):
#         return self.tokens

#     async def set_tokens(
#         self,
#         tokens: OAuthToken,
#     ) -> None:
#         self.tokens = tokens

#     async def get_client_info(self):
#         return self.client_info

#     async def set_client_info(
#         self,
#         client_info: OAuthClientInformationFull,
#     ) -> None:
#         self.client_info = client_info


# _OAUTH_STORAGE = InMemoryTokenStorage()


# # =========================================================
# # OAUTH CALLBACK SERVER
# # =========================================================

# class OAuthCallbackServer:

#     def __init__(
#         self,
#         host: str = CALLBACK_HOST,
#         port: int = CALLBACK_PORT,
#     ) -> None:

#         self.host = host
#         self.port = port

#         self.server = None
#         self.thread = None

#         self.code = None
#         self.state = None
#         self.iss = None
#         self.error = None

#         self.event = threading.Event()

#     def start(self) -> None:

#         callback_server = self

#         class CallbackHandler(
#             BaseHTTPRequestHandler
#         ):

#             def do_GET(self):

#                 parsed = urlparse(self.path)

#                 if parsed.path != "/callback":

#                     self.send_response(404)
#                     self.end_headers()

#                     return

#                 params = parse_qs(
#                     parsed.query
#                 )

#                 callback_server.code = params.get(
#                     "code",
#                     [None],
#                 )[0]

#                 callback_server.state = params.get(
#                     "state",
#                     [None],
#                 )[0]

#                 callback_server.iss = params.get(
#                     "iss",
#                     [None],
#                 )[0]

#                 callback_server.error = params.get(
#                     "error",
#                     [None],
#                 )[0]

#                 callback_server.event.set()

#                 self.send_response(200)

#                 self.send_header(
#                     "Content-Type",
#                     "text/html; charset=utf-8",
#                 )

#                 self.end_headers()

#                 if callback_server.error:

#                     message = (
#                         "<h2>"
#                         "PSX Chatbot authorization failed."
#                         "</h2>"
#                         f"<p>{callback_server.error}</p>"
#                         "<p>You can close this tab.</p>"
#                     )

#                 else:

#                     message = (
#                         "<h2>"
#                         "PSX Chatbot authorized."
#                         "</h2>"
#                         "<p>"
#                         "You can close this tab and return "
#                         "to Streamlit."
#                         "</p>"
#                     )

#                 html = f"""
#                 <!doctype html>
#                 <html>
#                 <head>
#                     <title>PSX Chatbot</title>
#                 </head>
#                 <body>
#                     {message}
#                 </body>
#                 </html>
#                 """

#                 self.wfile.write(
#                     html.encode("utf-8")
#                 )

#             def log_message(
#                 self,
#                 format,
#                 *args,
#             ):
#                 return

#         try:

#             self.server = ThreadingHTTPServer(
#                 (
#                     self.host,
#                     self.port,
#                 ),
#                 CallbackHandler,
#             )

#         except OSError as exc:

#             raise RuntimeError(
#                 f"Port {self.port} is already in use. "
#                 "Close the old PSX chatbot/Streamlit "
#                 "process and start again."
#             ) from exc

#         self.thread = threading.Thread(
#             target=self.server.serve_forever,
#             daemon=True,
#         )

#         self.thread.start()

#     def wait_for_callback(
#         self,
#         timeout: int = 300,
#     ) -> AuthorizationCodeResult:

#         received = self.event.wait(timeout)

#         if not received:

#             raise TimeoutError(
#                 "OAuth callback timed out after "
#                 f"{timeout} seconds."
#             )

#         if self.error:

#             raise RuntimeError(
#                 "OAuth authorization failed: "
#                 f"{self.error}"
#             )

#         if not self.code:

#             raise RuntimeError(
#                 "OAuth callback did not contain "
#                 "an authorization code."
#             )

#         return AuthorizationCodeResult(
#             code=self.code,
#             state=self.state,
#             iss=self.iss,
#         )

#     def stop(self) -> None:

#         if self.server is not None:

#             self.server.shutdown()
#             self.server.server_close()

#             self.server = None


# # =========================================================
# # OAUTH PROVIDER
# # =========================================================

# def create_oauth_provider(
#     callback_server: OAuthCallbackServer,
# ):

#     async def redirect_handler(
#         authorization_url: str,
#     ) -> None:

#         print(
#             "\n========================================"
#         )

#         print(
#             "PSX MCP authorization required."
#         )

#         print(
#             "Opening browser..."
#         )

#         print(
#             "========================================\n"
#         )

#         webbrowser.open_new_tab(
#             authorization_url
#         )

#     async def callback_handler():

#         try:

#             return await asyncio.to_thread(
#                 callback_server.wait_for_callback,
#                 300,
#             )

#         finally:

#             callback_server.stop()

#     return OAuthClientProvider(

#         server_url=MCP_SERVER_URL,

#         client_metadata=OAuthClientMetadata(

#             client_name="PSX Chatbot",

#             redirect_uris=[
#                 AnyUrl(CALLBACK_URL)
#             ],

#             grant_types=[
#                 "authorization_code",
#                 "refresh_token",
#             ],

#             response_types=[
#                 "code"
#             ],

#             scope="user",
#         ),

#         storage=_OAUTH_STORAGE,

#         redirect_handler=redirect_handler,

#         callback_handler=callback_handler,
#     )


# # =========================================================
# # CHATBOT
# # =========================================================

# class PSXChatbot:

#     def __init__(self) -> None:

#         self.tools = []

#         self.tool_map = {}

#         self.last_tool = None

#         self.last_arguments = {}

#         self.conversation_history = []

#     # =====================================================
#     # NORMALIZE TEXT
#     # =====================================================

#     @staticmethod
#     def _normalize_text(value: str) -> str:

#         value = value.lower().strip()

#         value = re.sub(
#             r"[^a-z0-9]+",
#             " ",
#             value,
#         )

#         return " ".join(
#             value.split()
#         )

#     # =====================================================
#     # EXTRACT INDUSTRY FROM QUESTION
#     # =====================================================

#     def _find_industry_in_question(
#         self,
#         user_message: str,
#         industries: list[str],
#     ) -> str | None:

#         question = self._normalize_text(
#             user_message
#         )

#         normalized_industries = []

#         for industry in industries:

#             normalized = self._normalize_text(
#                 industry
#             )

#             if normalized:

#                 normalized_industries.append(
#                     (
#                         normalized,
#                         industry,
#                     )
#                 )

#         # Exact/substring match first.
#         for normalized, original in normalized_industries:

#             if normalized in question:

#                 return original

#         # Extract text after common phrases.
#         patterns = (
#             r"\bstocks?\s+(?:in|of|from)\s+(.+)$",
#             r"\bshares?\s+(?:in|of|from)\s+(.+)$",
#             r"\bcompanies\s+(?:in|of|from)\s+(.+)$",
#             r"\b(?:industry|sector)\s*[:\-]?\s*(.+)$",
#         )

#         candidate = None

#         for pattern in patterns:

#             match = re.search(
#                 pattern,
#                 question,
#             )

#             if match:

#                 candidate = match.group(1).strip()

#                 break

#         if not candidate:

#             return None

#         # Exact candidate match.
#         for normalized, original in normalized_industries:

#             if candidate == normalized:

#                 return original

#         # Conservative fuzzy matching.
#         matches = difflib.get_close_matches(
#             candidate,
#             [
#                 normalized
#                 for normalized, _
#                 in normalized_industries
#             ],
#             n=1,
#             cutoff=0.90,
#         )

#         if matches:

#             matched = matches[0]

#             for normalized, original in normalized_industries:

#                 if normalized == matched:

#                     return original

#         return None

#     # =====================================================
#     # DIRECT TOOL ROUTING
#     # =====================================================

#     async def _detect_direct_tool(
#         self,
#         user_message: str,
#         session,
#     ):

#         q = " ".join(
#             user_message.lower().split()
#         )

#         # -------------------------------------------------
#         # SYMBOLS
#         # -------------------------------------------------

#         if any(
#             word in q
#             for word in (
#                 "symbol",
#                 "symbols",
#                 "ticker",
#                 "tickers",
#             )
#         ):

#             return (
#                 "get_symbols",
#                 {},
#             )

#         # -------------------------------------------------
#         # RANKINGS FIRST
#         # -------------------------------------------------

#         if (
#             (
#                 "top" in q
#                 or "highest" in q
#                 or "gainer" in q
#                 or "gainers" in q
#             )
#             and "volume" in q
#         ):

#             return (
#                 "get_top_volume",
#                 {},
#             )

#         if (
#             (
#                 "bottom" in q
#                 or "lowest" in q
#                 or "loser" in q
#                 or "losers" in q
#             )
#             and "volume" in q
#         ):

#             return (
#                 "get_bottom_volume",
#                 {},
#             )

#         if (
#             (
#                 "top" in q
#                 or "highest" in q
#                 or "gainer" in q
#                 or "gainers" in q
#             )
#             and (
#                 "change" in q
#                 or "percent" in q
#                 or "%" in q
#             )
#         ):

#             return (
#                 "get_top_change",
#                 {},
#             )

#         if (
#             (
#                 "bottom" in q
#                 or "lowest" in q
#                 or "loser" in q
#                 or "losers" in q
#             )
#             and (
#                 "change" in q
#                 or "percent" in q
#                 or "%" in q
#             )
#         ):

#             return (
#                 "get_bottom_change",
#                 {},
#             )

#         # -------------------------------------------------
#         # STOCK WORDS
#         # -------------------------------------------------

#         has_stock_word = any(
#             word in q
#             for word in (
#                 "stock",
#                 "stocks",
#                 "share",
#                 "shares",
#                 "security",
#                 "securities",
#                 "company",
#                 "companies",
#             )
#         )

#         has_all_word = any(
#             word in q
#             for word in (
#                 "all",
#                 "every",
#                 "list",
#                 "show",
#             )
#         )

#         # -------------------------------------------------
#         # STOCK REQUESTS
#         # -------------------------------------------------

#         if has_stock_word:

#             # Ask for a specific industry.
#             if any(
#                 phrase in q
#                 for phrase in (
#                     " in ",
#                     " of ",
#                     " from ",
#                     "industry",
#                     "sector",
#                 )
#             ):

#                 industries_result = (
#                     await self._call_tool(
#                         session,
#                         "get_industries",
#                         {},
#                     )
#                 )

#                 industries_data = (
#                     self._extract_tool_result(
#                         industries_result
#                     )
#                 )

#                 industries = (
#                     self._extract_industry_names(
#                         industries_data
#                     )
#                 )

#                 industry = (
#                     self._find_industry_in_question(
#                         user_message,
#                         industries,
#                     )
#                 )

#                 if industry:

#                     return (
#                         "get_stocks",
#                         {
#                             "industry": industry,
#                         },
#                     )

#             # All stocks.
#             if has_all_word:

#                 return (
#                     "__all_stocks__",
#                     {},
#                 )

#         # -------------------------------------------------
#         # INDUSTRIES
#         # -------------------------------------------------

#         if any(
#             phrase in q
#             for phrase in (
#                 "list industries",
#                 "list industry",
#                 "all industries",
#                 "all industry",
#                 "available industries",
#                 "available sectors",
#                 "industry list",
#                 "sector list",
#                 "list sectors",
#             )
#         ):

#             return (
#                 "get_industries",
#                 {},
#             )

#         return None

#     # =====================================================
#     # EXTRACT INDUSTRY NAMES
#     # =====================================================

#     def _extract_industry_names(
#         self,
#         data,
#     ) -> list[str]:

#         if isinstance(data, list):

#             rows = data

#         elif isinstance(data, dict):

#             rows = []

#             for key in (
#                 "data",
#                 "results",
#                 "result",
#                 "items",
#                 "industries",
#             ):

#                 value = data.get(key)

#                 if isinstance(value, list):

#                     rows = value

#                     break

#         else:

#             rows = []

#         industries = []

#         for item in rows:

#             if isinstance(item, str):

#                 value = item.strip()

#                 if value:
#                     industries.append(value)

#             elif isinstance(item, dict):

#                 for key in (
#                     "industry",
#                     "Industry",
#                     "name",
#                     "Name",
#                 ):

#                     value = item.get(key)

#                     if value:

#                         industries.append(
#                             str(value).strip()
#                         )

#                         break

#         # Remove duplicates while preserving order.
#         unique = []

#         seen = set()

#         for industry in industries:

#             normalized = self._normalize_text(
#                 industry
#             )

#             if (
#                 normalized
#                 and normalized not in seen
#             ):

#                 seen.add(normalized)

#                 unique.append(industry)

#         return unique

#     # =====================================================
#     # MCP CONNECTION
#     # =====================================================

#     async def _connect_mcp(self):

#         callback_server = (
#             OAuthCallbackServer()
#         )

#         callback_server.start()

#         oauth = create_oauth_provider(
#             callback_server
#         )

#         http_client = httpx2.AsyncClient(

#             auth=oauth,

#             timeout=httpx2.Timeout(
#                 30.0,
#                 read=300.0,
#             ),
#         )

#         return (
#             callback_server,
#             http_client,
#         )

#     # =====================================================
#     # LOAD MCP TOOLS
#     # =====================================================

#     async def _load_tools(
#         self,
#         session,
#     ):

#         result = await session.list_tools()

#         self.tools = result.tools

#         self.tool_map = {
#             tool.name: tool
#             for tool in self.tools
#         }

#     # =====================================================
#     # OPENAI TOOL FORMAT
#     # =====================================================

#     def _openai_tools(self):

#         openai_tools = []

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

#             if input_schema is None:

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
#                             tool.description
#                             or f"MCP tool {tool.name}"
#                         ),
#                         "parameters": input_schema,
#                     },
#                 }
#             )

#         return openai_tools

#     # =====================================================
#     # CALL MCP TOOL
#     # =====================================================

#     async def _call_tool(
#         self,
#         session,
#         tool_name: str,
#         arguments: dict,
#     ):

#         self.last_tool = tool_name

#         self.last_arguments = arguments

#         result = await session.call_tool(
#             tool_name,
#             arguments,
#         )

#         # MCP tool-level error.
#         if getattr(
#             result,
#             "is_error",
#             False,
#         ):

#             content = getattr(
#                 result,
#                 "content",
#                 [],
#             )

#             error_text = []

#             for item in content:

#                 text_value = getattr(
#                     item,
#                     "text",
#                     None,
#                 )

#                 if text_value:

#                     error_text.append(
#                         str(text_value)
#                     )

#             message = (
#                 "\n".join(error_text).strip()
#                 or "Unknown MCP tool error."
#             )

#             raise RuntimeError(
#                 f"{tool_name} failed: {message}"
#             )

#         return result

#     # =====================================================
#     # EXTRACT MCP RESULT
#     # =====================================================

#     def _extract_tool_result(
#         self,
#         result,
#     ):

#         if isinstance(
#             result,
#             (list, dict),
#         ):

#             return result

#         # Preferred application data.
#         structured = getattr(
#             result,
#             "structured_content",
#             None,
#         )

#         if structured is not None:

#             return structured

#         structured = getattr(
#             result,
#             "structuredContent",
#             None,
#         )

#         if structured is not None:

#             return structured

#         # Model/content representation.
#         content = getattr(
#             result,
#             "content",
#             None,
#         )

#         if content:

#             collected_text = []

#             for item in content:

#                 text_value = getattr(
#                     item,
#                     "text",
#                     None,
#                 )

#                 if text_value:

#                     collected_text.append(
#                         str(text_value)
#                     )

#             if collected_text:

#                 combined_text = "\n".join(
#                     collected_text
#                 ).strip()

#                 try:

#                     return json.loads(
#                         combined_text
#                     )

#                 except json.JSONDecodeError:

#                     return combined_text

#         model_dump = getattr(
#             result,
#             "model_dump",
#             None,
#         )

#         if callable(model_dump):

#             try:

#                 dumped = model_dump()

#                 if isinstance(
#                     dumped,
#                     (dict, list),
#                 ):

#                     return dumped

#             except Exception:
#                 pass

#         return result

#     # =====================================================
#     # FORMAT MCP RESULT
#     # =====================================================

#     def _format_tool_result(
#         self,
#         tool_name: str,
#         result,
#         arguments: dict,
#     ):

#         raw_data = self._extract_tool_result(
#             result
#         )

#         if tool_name == "get_symbols":

#             return format_symbols(
#                 raw_data
#             )

#         if tool_name == "get_industries":

#             return format_industries(
#                 raw_data
#             )

#         if tool_name == "get_stocks":

#             return format_stock_data(
#                 raw_data,
#                 arguments.get(
#                     "industry",
#                     "",
#                 ),
#             )

#         if tool_name in {
#             "get_top_change",
#             "get_bottom_change",
#             "get_top_volume",
#             "get_bottom_volume",
#         }:

#             return format_top_bottom(
#                 raw_data,
#                 tool_name,
#             )

#         return json.dumps(
#             raw_data,
#             ensure_ascii=False,
#             default=str,
#         )

#     # =====================================================
#     # ALL STOCKS
#     # =====================================================

#     async def _get_all_stocks(
#         self,
#         session,
#     ) -> tuple[str, dict]:

#         # First get the valid industry names.
#         industries_result = (
#             await self._call_tool(
#                 session,
#                 "get_industries",
#                 {},
#             )
#         )

#         industries_data = (
#             self._extract_tool_result(
#                 industries_result
#             )
#         )

#         industries = (
#             self._extract_industry_names(
#                 industries_data
#             )
#         )

#         if not industries:

#             raise RuntimeError(
#                 "MCP returned no industries, "
#                 "so all stocks could not be loaded."
#             )

#         all_rows = []

#         for industry in industries:

#             result = await self._call_tool(
#                 session,
#                 "get_stocks",
#                 {
#                     "industry": industry,
#                 },
#             )

#             data = self._extract_tool_result(
#                 result
#             )

#             rows = self._data_rows(
#                 data
#             )

#             for row in rows:

#                 if isinstance(row, dict):

#                     item = dict(row)

#                     if not item.get(
#                         "industry"
#                     ):

#                         item["industry"] = industry

#                     all_rows.append(item)

#         # Deduplicate by symbol.
#         unique_rows = []

#         seen_symbols = set()

#         for row in all_rows:

#             symbol = (
#                 row.get("symbol")
#                 or row.get("Symbol")
#                 or row.get("ticker")
#                 or row.get("Ticker")
#             )

#             if symbol:

#                 key = str(
#                     symbol
#                 ).strip().upper()

#             else:

#                 key = json.dumps(
#                     row,
#                     sort_keys=True,
#                     default=str,
#                 )

#             if key in seen_symbols:

#                 continue

#             seen_symbols.add(key)

#             unique_rows.append(row)

#         self.last_tool = "get_stocks"

#         self.last_arguments = {
#             "industry": "ALL",
#             "industries_requested": len(
#                 industries
#             ),
#         }

#         return (
#             format_stock_data(
#                 unique_rows
#             ),
#             self.last_arguments,
#         )

#     # =====================================================
#     # EXTRACT ROWS
#     # =====================================================

#     def _data_rows(
#         self,
#         data,
#     ) -> list:

#         if isinstance(
#             data,
#             list,
#         ):

#             return data

#         if isinstance(
#             data,
#             dict,
#         ):

#             for key in (
#                 "data",
#                 "results",
#                 "result",
#                 "items",
#                 "stocks",
#                 "records",
#             ):

#                 value = data.get(key)

#                 if isinstance(
#                     value,
#                     list,
#                 ):

#                     return value

#                 if isinstance(
#                     value,
#                     dict,
#                 ):

#                     nested = self._data_rows(
#                         value
#                     )

#                     if nested:

#                         return nested

#             # Single stock object.
#             if any(
#                 key in data
#                 for key in (
#                     "symbol",
#                     "Symbol",
#                     "ticker",
#                     "Ticker",
#                 )
#             ):

#                 return [data]

#         return []

#     # =====================================================
#     # SYSTEM PROMPT
#     # =====================================================

#     def _system_prompt(self):

#         return """
# You are the PSX Chatbot.

# You answer Pakistan Stock Exchange questions
# using MCP tools.

# IMPORTANT:

# - Never invent PSX data.
# - MCP results are the source of truth.
# - Always use an MCP tool for PSX market data.
# - Do not answer PSX market-data questions from memory.

# Tool rules:

# get_symbols:
# Use for symbols and tickers.

# get_industries:
# Use for industries and sectors.

# get_stocks:
# Use for stock listings.
# The industry argument is REQUIRED.
# If an industry is specified, pass the exact
# industry name returned by get_industries.

# get_top_change:
# Use for top gainers/change percentage.

# get_bottom_change:
# Use for bottom/lowest change percentage.

# get_top_volume:
# Use for highest trading volume.

# get_bottom_volume:
# Use for lowest trading volume.

# Do not provide investment guarantees.
# Do not provide personalized financial advice.

# Keep answers concise and preserve numerical values.
# """

#     # =====================================================
#     # LLM CALL
#     # =====================================================

#     async def _ask_llm(
#         self,
#         client,
#         messages,
#     ):

#         return await client.chat.completions.create(

#             model=LLM_MODEL,

#             messages=messages,

#             tools=self._openai_tools(),

#             tool_choice="auto",

#             temperature=0,
#         )

#     # =====================================================
#     # CHAT
#     # =====================================================

#     async def _chat_async(
#         self,
#         user_message: str,
#     ):

#         callback_server = None
#         http_client = None

#         try:

#             (
#                 callback_server,
#                 http_client,
#             ) = await self._connect_mcp()

#             async with http_client:

#                 async with streamable_http_client(
#                     MCP_SERVER_URL,
#                     http_client=http_client,
#                 ) as (
#                     read_stream,
#                     write_stream,
#                 ):

#                     async with ClientSession(
#                         read_stream,
#                         write_stream,
#                     ) as session:

#                         await session.initialize()

#                         await self._load_tools(
#                             session
#                         )

#                         # ---------------------------------
#                         # DIRECT ROUTING
#                         # ---------------------------------

#                         direct_tool = (
#                             await self._detect_direct_tool(
#                                 user_message,
#                                 session,
#                             )
#                         )

#                         if direct_tool:

#                             (
#                                 tool_name,
#                                 arguments,
#                             ) = direct_tool

#                             # ALL STOCKS
#                             if tool_name == "__all_stocks__":

#                                 answer, arguments = (
#                                     await self._get_all_stocks(
#                                         session
#                                     )
#                                 )

#                                 self.conversation_history.append(
#                                     {
#                                         "role": "user",
#                                         "content": user_message,
#                                     }
#                                 )

#                                 self.conversation_history.append(
#                                     {
#                                         "role": "assistant",
#                                         "content": answer,
#                                     }
#                                 )

#                                 return {
#                                     "answer": answer,
#                                     "tool": self.last_tool,
#                                     "arguments": arguments,
#                                 }

#                             if (
#                                 tool_name
#                                 not in self.tool_map
#                             ):

#                                 raise RuntimeError(
#                                     f"MCP tool "
#                                     f"'{tool_name}' "
#                                     f"was not found."
#                                 )

#                             result = (
#                                 await self._call_tool(
#                                     session,
#                                     tool_name,
#                                     arguments,
#                                 )
#                             )

#                             answer = (
#                                 self._format_tool_result(
#                                     tool_name,
#                                     result,
#                                     arguments,
#                                 )
#                             )

#                             self.conversation_history.append(
#                                 {
#                                     "role": "user",
#                                     "content": user_message,
#                                 }
#                             )

#                             self.conversation_history.append(
#                                 {
#                                     "role": "assistant",
#                                     "content": answer,
#                                 }
#                             )

#                             return {
#                                 "answer": answer,
#                                 "tool": self.last_tool,
#                                 "arguments": self.last_arguments,
#                             }

#                         # ---------------------------------
#                         # LLM FALLBACK
#                         # ---------------------------------

#                         llm_client = (
#                             create_llm_client()
#                         )

#                         messages = [
#                             {
#                                 "role": "system",
#                                 "content": (
#                                     self._system_prompt()
#                                 ),
#                             }
#                         ]

#                         messages.extend(
#                             self.conversation_history
#                         )

#                         messages.append(
#                             {
#                                 "role": "user",
#                                 "content": user_message,
#                             }
#                         )

#                         # ---------------------------------
#                         # TOOL-CALLING LOOP
#                         # ---------------------------------

#                         for _ in range(6):

#                             response = (
#                                 await self._ask_llm(
#                                     llm_client,
#                                     messages,
#                                 )
#                             )

#                             message = (
#                                 response.choices[
#                                     0
#                                 ].message
#                             )

#                             tool_calls = (
#                                 message.tool_calls
#                             )

#                             # ---------------------------------
#                             # FINAL ANSWER
#                             # ---------------------------------

#                             if not tool_calls:

#                                 final_answer = (
#                                     message.content
#                                     or "I could not generate a response."
#                                 )

#                                 self.conversation_history.append(
#                                     {
#                                         "role": "user",
#                                         "content": user_message,
#                                     }
#                                 )

#                                 self.conversation_history.append(
#                                     {
#                                         "role": "assistant",
#                                         "content": final_answer,
#                                     }
#                                 )

#                                 return {
#                                     "answer": final_answer,
#                                     "tool": self.last_tool,
#                                     "arguments": self.last_arguments,
#                                 }

#                             # ---------------------------------
#                             # ASSISTANT TOOL CALLS
#                             # ---------------------------------

#                             assistant_tool_calls = []

#                             for call in tool_calls:

#                                 assistant_tool_calls.append(
#                                     {
#                                         "id": call.id,
#                                         "type": "function",
#                                         "function": {
#                                             "name": (
#                                                 call.function.name
#                                             ),
#                                             "arguments": (
#                                                 call.function.arguments
#                                             ),
#                                         },
#                                     }
#                                 )

#                             messages.append(
#                                 {
#                                     "role": "assistant",
#                                     "content": (
#                                         message.content
#                                         or None
#                                     ),
#                                     "tool_calls": (
#                                         assistant_tool_calls
#                                     ),
#                                 }
#                             )

#                             # ---------------------------------
#                             # EXECUTE TOOLS
#                             # ---------------------------------

#                             for call in tool_calls:

#                                 tool_name = (
#                                     call.function.name
#                                 )

#                                 try:

#                                     arguments = json.loads(
#                                         call.function.arguments
#                                     )

#                                 except (
#                                     json.JSONDecodeError,
#                                 ):

#                                     arguments = {}

#                                 # ---------------------------------
#                                 # SAFETY: get_stocks REQUIRES
#                                 # industry.
#                                 # ---------------------------------

#                                 if (
#                                     tool_name == "get_stocks"
#                                     and not arguments.get(
#                                         "industry"
#                                     )
#                                 ):

#                                     tool_output = (
#                                         "The get_stocks MCP tool "
#                                         "requires an industry."
#                                     )

#                                 elif (
#                                     tool_name
#                                     not in self.tool_map
#                                 ):

#                                     tool_output = (
#                                         f"Unknown MCP tool: "
#                                         f"{tool_name}"
#                                     )

#                                 else:

#                                     result = (
#                                         await self._call_tool(
#                                             session,
#                                             tool_name,
#                                             arguments,
#                                         )
#                                     )

#                                     tool_output = (
#                                         self._format_tool_result(
#                                             tool_name,
#                                             result,
#                                             arguments,
#                                         )
#                                     )

#                                 messages.append(
#                                     {
#                                         "role": "tool",
#                                         "tool_call_id": call.id,
#                                         "content": str(
#                                             tool_output
#                                         ),
#                                     }
#                                 )

#                         return {
#                             "answer": (
#                                 "I could not complete "
#                                 "the PSX request."
#                             ),
#                             "tool": self.last_tool,
#                             "arguments": self.last_arguments,
#                         }

#         except Exception as exc:

#             root = exc

#             while (
#                 hasattr(root, "exceptions")
#                 and root.exceptions
#             ):

#                 root = root.exceptions[0]

#             raise RuntimeError(
#                 "MCP chatbot error: "
#                 f"{type(root).__name__}: {root}"
#             ) from exc

#         finally:

#             if callback_server is not None:

#                 callback_server.stop()

#     # =====================================================
#     # PUBLIC CHAT
#     # =====================================================

#     def chat(
#         self,
#         user_message: str,
#     ):

#         return asyncio.run(
#             self._chat_async(
#                 user_message
#             )
#         )


# # =========================================================
# # GLOBAL CHATBOT INSTANCE
# # =========================================================

# _CHATBOT = PSXChatbot()


# # =========================================================
# # STREAMLIT ENTRY POINT
# # =========================================================

# def ask_chatbot(
#     user_message: str,
#     history=None,
# ) -> dict:

#     if history is not None:

#         _CHATBOT.conversation_history = []

#         for item in history:

#             if not isinstance(
#                 item,
#                 dict,
#             ):

#                 continue

#             role = item.get(
#                 "role"
#             )

#             content = item.get(
#                 "content"
#             )

#             if (
#                 role in {
#                     "user",
#                     "assistant",
#                 }
#                 and content
#             ):

#                 _CHATBOT.conversation_history.append(
#                     {
#                         "role": role,
#                         "content": str(content),
#                     }
#                 )

#     return _CHATBOT.chat(
#         user_message
#     )



# from __future__ import annotations

# import asyncio
# import difflib
# import json
# import os
# import re

# import httpx
# from dotenv import load_dotenv
# from mcp import ClientSession
# from mcp.client.streamable_http import streamable_http_client

# from chatbot.formatters import (
#     format_industries,
#     format_stock_data,
#     format_symbols,
#     format_top_bottom,
# )

# from chatbot.llm import create_llm_client


# load_dotenv()


# # ============================================================
# # CONFIGURATION
# # ============================================================

# MCP_SERVER_URL = os.getenv(
#     "MCP_SERVER_URL",
#     "https://fluttering-blue-ox.fastmcp.app/mcp",
# )

# LLM_PROVIDER = os.getenv(
#     "LLM_PROVIDER",
#     "groq",
# ).lower()

# LLM_MODEL = os.getenv(
#     "LLM_MODEL",
#     "openai/gpt-oss-120b",
# )


# # ============================================================
# # PSX CHATBOT
# # ============================================================

# class PSXChatbot:

#     def __init__(self):
#         self.tools = []
#         self.tool_map = {}

#         self.last_tool = None
#         self.last_arguments = {}

#         self.conversation_history = []

#     # ========================================================
#     # TEXT HELPERS
#     # ========================================================

#     @staticmethod
#     def _normalize_text(text: str) -> str:
#         text = text.lower().strip()
#         text = re.sub(r"\s+", " ", text)
#         return text

#     # ========================================================
#     # INDUSTRY DETECTION
#     # ========================================================

#     def _find_industry_in_question(self, question: str) -> str | None:
#         question_normalized = self._normalize_text(question)

#         if not self.tools:
#             return None

#         industry_tool = self.tool_map.get("get_industries")

#         if not industry_tool:
#             return None

#         try:
#             result = self._call_tool_sync(
#                 "get_industries",
#                 {},
#             )

#             industries = self._extract_tool_result(result)

#             if isinstance(industries, dict):
#                 possible_industries = (
#                     industries.get("industries")
#                     or industries.get("data")
#                     or []
#                 )
#             elif isinstance(industries, list):
#                 possible_industries = industries
#             else:
#                 possible_industries = []

#             normalized_map = {}

#             for item in possible_industries:

#                 if isinstance(item, dict):
#                     name = (
#                         item.get("industry")
#                         or item.get("name")
#                         or item.get("sector")
#                     )
#                 else:
#                     name = str(item)

#                 if name:
#                     normalized_map[
#                         self._normalize_text(name)
#                     ] = name

#             # Exact match
#             for normalized_name, original_name in normalized_map.items():

#                 if normalized_name in question_normalized:
#                     return original_name

#             # Fuzzy matching
#             words = question_normalized.split()

#             for normalized_name, original_name in normalized_map.items():

#                 ratio = difflib.SequenceMatcher(
#                     None,
#                     normalized_name,
#                     question_normalized,
#                 ).ratio()

#                 if ratio >= 0.70:
#                     return original_name

#                 if len(words) > 1:

#                     for word in words:

#                         if len(word) < 4:
#                             continue

#                         ratio = difflib.SequenceMatcher(
#                             None,
#                             normalized_name,
#                             word,
#                         ).ratio()

#                         if ratio >= 0.85:
#                             return original_name

#         except Exception:
#             return None

#         return None

#     # ========================================================
#     # DIRECT TOOL DETECTION
#     # ========================================================

#     def _detect_direct_tool(
#         self,
#         question: str,
#     ) -> tuple[str | None, dict]:

#         q = self._normalize_text(question)

#         # Symbols
#         if (
#             "list symbols" in q
#             or "all symbols" in q
#             or "stock symbols" in q
#             or q in {"symbols", "symbol"}
#         ):
#             return "get_symbols", {}

#         # Industries
#         if (
#             "list industries" in q
#             or "all industries" in q
#             or "industries" in q
#             or q == "industry"
#         ):
#             return "get_industries", {}

#         # Top change
#         if (
#             "top change" in q
#             or "top 10 change" in q
#             or "highest change" in q
#             or "top gainers" in q
#             or "top gainer" in q
#         ):
#             industry = self._find_industry_in_question(question)

#             arguments = {}

#             if industry:
#                 arguments["industry"] = industry

#             return "get_top_change", arguments

#         # Bottom change
#         if (
#             "bottom change" in q
#             or "bottom 10 change" in q
#             or "lowest change" in q
#             or "top losers" in q
#             or "losers" in q
#         ):
#             industry = self._find_industry_in_question(question)

#             arguments = {}

#             if industry:
#                 arguments["industry"] = industry

#             return "get_bottom_change", arguments

#         # Top volume
#         if (
#             "top volume" in q
#             or "highest volume" in q
#             or "most volume" in q
#         ):
#             industry = self._find_industry_in_question(question)

#             arguments = {}

#             if industry:
#                 arguments["industry"] = industry

#             return "get_top_volume", arguments

#         # Bottom volume
#         if (
#             "bottom volume" in q
#             or "lowest volume" in q
#             or "least volume" in q
#         ):
#             industry = self._find_industry_in_question(question)

#             arguments = {}

#             if industry:
#                 arguments["industry"] = industry

#             return "get_bottom_volume", arguments

#         return None, {}

#     # ========================================================
#     # INDUSTRY EXTRACTION
#     # ========================================================

#     def _extract_industry_names(
#         self,
#         question: str,
#     ) -> list[str]:

#         industry = self._find_industry_in_question(question)

#         if industry:
#             return [industry]

#         return []

#     # ========================================================
#     # MCP CONNECTION
#     # ========================================================

#     async def _connect_mcp(self):

#         return httpx.AsyncClient(
#             timeout=httpx.Timeout(
#                 30.0,
#                 read=300.0,
#             ),
#         )

#     # ========================================================
#     # LOAD MCP TOOLS
#     # ========================================================

#     async def _load_tools(
#         self,
#         session: ClientSession,
#     ):

#         response = await session.list_tools()

#         self.tools = response.tools

#         self.tool_map = {
#             tool.name: tool
#             for tool in self.tools
#         }

#         return self.tools

#     # ========================================================
#     # OPENAI TOOL FORMAT
#     # ========================================================

#     def _openai_tools(self):

#         openai_tools = []

#         for tool in self.tools:

#             input_schema = getattr(
#                 tool,
#                 "inputSchema",
#                 None,
#             )

#             if input_schema is None:
#                 input_schema = {}

#             openai_tools.append(
#                 {
#                     "type": "function",
#                     "function": {
#                         "name": tool.name,
#                         "description": (
#                             getattr(
#                                 tool,
#                                 "description",
#                                 None,
#                             )
#                             or ""
#                         ),
#                         "parameters": input_schema,
#                     },
#                 }
#             )

#         return openai_tools

#     # ========================================================
#     # MCP TOOL CALL
#     # ========================================================

#     async def _call_tool(
#         self,
#         session: ClientSession,
#         tool_name: str,
#         arguments: dict | None = None,
#     ):

#         if arguments is None:
#             arguments = {}

#         self.last_tool = tool_name
#         self.last_arguments = arguments

#         result = await session.call_tool(
#             tool_name,
#             arguments=arguments,
#         )

#         return result

#     # ========================================================
#     # SYNC TOOL HELPER
#     # ========================================================

#     def _call_tool_sync(
#         self,
#         tool_name: str,
#         arguments: dict,
#     ):

#         async def runner():

#             http_client = await self._connect_mcp()

#             try:

#                 async with streamable_http_client(
#                     MCP_SERVER_URL,
#                     http_client=http_client,
#                 ) as (
#                     read_stream,
#                     write_stream,
#                 ):

#                     async with ClientSession(
#                         read_stream,
#                         write_stream,
#                     ) as session:

#                         await session.initialize()

#                         return await self._call_tool(
#                             session,
#                             tool_name,
#                             arguments,
#                         )

#             finally:

#                 await http_client.aclose()

#         return asyncio.run(runner())

#     # ========================================================
#     # EXTRACT MCP RESULT
#     # ========================================================

#     def _extract_tool_result(self, result):

#         if result is None:
#             return None

#         # MCP result usually contains content
#         content = getattr(
#             result,
#             "content",
#             None,
#         )

#         if content is None:
#             return result

#         extracted = []

#         for item in content:

#             text = getattr(
#                 item,
#                 "text",
#                 None,
#             )

#             if text is not None:
#                 extracted.append(text)
#                 continue

#             extracted.append(item)

#         if len(extracted) == 1:

#             value = extracted[0]

#             if isinstance(value, str):

#                 try:
#                     return json.loads(value)
#                 except Exception:
#                     return value

#             return value

#         return extracted

#     # ========================================================
#     # FORMAT TOOL RESULT
#     # ========================================================

#     def _format_tool_result(
#         self,
#         tool_name: str,
#         result,
#     ):

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

#             pass

#         if isinstance(data, str):
#             return data

#         try:
#             return json.dumps(
#                 data,
#                 indent=2,
#                 default=str,
#             )
#         except Exception:
#             return str(data)

#     # ========================================================
#     # GET ALL STOCKS
#     # ========================================================

#     async def _get_all_stocks(
#         self,
#         session: ClientSession,
#     ):

#         industries_result = await self._call_tool(
#             session,
#             "get_industries",
#             {},
#         )

#         industries_data = self._extract_tool_result(
#             industries_result
#         )

#         if isinstance(industries_data, dict):

#             industries = (
#                 industries_data.get("industries")
#                 or industries_data.get("data")
#                 or []
#             )

#         elif isinstance(industries_data, list):

#             industries = industries_data

#         else:

#             industries = []

#         all_stocks = []

#         for item in industries:

#             if isinstance(item, dict):

#                 industry = (
#                     item.get("industry")
#                     or item.get("name")
#                     or item.get("sector")
#                 )

#             else:

#                 industry = str(item)

#             if not industry:
#                 continue

#             try:

#                 result = await self._call_tool(
#                     session,
#                     "get_stocks",
#                     {
#                         "industry": industry,
#                     },
#                 )

#                 data = self._extract_tool_result(
#                     result
#                 )

#                 if isinstance(data, list):
#                     all_stocks.extend(data)

#                 elif isinstance(data, dict):

#                     rows = (
#                         data.get("data")
#                         or data.get("stocks")
#                         or data.get("results")
#                         or []
#                     )

#                     if isinstance(rows, list):
#                         all_stocks.extend(rows)

#             except Exception:

#                 continue

#         return all_stocks

#     # ========================================================
#     # DATA ROWS
#     # ========================================================

#     def _data_rows(self, data):

#         if isinstance(data, list):
#             return data

#         if isinstance(data, dict):

#             for key in (
#                 "data",
#                 "stocks",
#                 "results",
#                 "rows",
#             ):

#                 value = data.get(key)

#                 if isinstance(value, list):
#                     return value

#         return []

#     # ========================================================
#     # SYSTEM PROMPT
#     # ========================================================

#     def _system_prompt(self):

#         return """
# You are a professional Pakistan Stock Exchange (PSX) chatbot.

# Your job is to answer user questions using live PSX data obtained
# through MCP tools.

# Important rules:

# 1. Use MCP tools whenever live PSX data is required.
# 2. Never invent stock prices, changes, volumes, symbols, industries,
#    or other financial information.
# 3. If the user asks for current/live PSX information, fetch the
#    information using the appropriate MCP tool.
# 4. For industry-specific questions, use the industry provided by
#    the user.
# 5. When comparing stocks, clearly identify the relevant metrics.
# 6. Keep answers clear and concise.
# 7. If the requested information is unavailable, clearly say so.
# 8. Do not claim that data is real-time unless the MCP/API actually
#    provides current data.
# 9. You are a chatbot, not a human financial advisor.
# 10. Do not fabricate analysis when the required data is unavailable.

# Available MCP tools can provide:

# - PSX symbols
# - PSX industries
# - Stocks by industry
# - Top stocks by Change %
# - Bottom stocks by Change %
# - Top stocks by Volume
# - Bottom stocks by Volume
# """

#     # ========================================================
#     # LLM REQUEST
#     # ========================================================

#     async def _ask_llm(
#         self,
#         client,
#         messages,
#         tools,
#     ):

#         response = await client.chat.completions.create(
#             model=LLM_MODEL,
#             messages=messages,
#             tools=tools if tools else None,
#             tool_choice="auto" if tools else None,
#         )

#         return response

#     # ========================================================
#     # MAIN ASYNC CHAT
#     # ========================================================

#     async def _chat_async(
#         self,
#         user_message: str,
#         history: list | None = None,
#     ):

#         http_client = None

#         try:

#             # ------------------------------------------------
#             # CONNECT TO MCP
#             # ------------------------------------------------

#             http_client = await self._connect_mcp()

#             async with streamable_http_client(
#                 MCP_SERVER_URL,
#                 http_client=http_client,
#             ) as (
#                 read_stream,
#                 write_stream,
#             ):

#                 async with ClientSession(
#                     read_stream,
#                     write_stream,
#                 ) as session:

#                     # ----------------------------------------
#                     # INITIALIZE MCP
#                     # ----------------------------------------

#                     await session.initialize()

#                     # ----------------------------------------
#                     # LOAD TOOLS
#                     # ----------------------------------------

#                     await self._load_tools(session)

#                     # ----------------------------------------
#                     # DIRECT TOOL ROUTING
#                     # ----------------------------------------

#                     direct_tool, direct_arguments = (
#                         self._detect_direct_tool(
#                             user_message
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

#                         except Exception as direct_error:

#                             # If direct routing fails,
#                             # continue to LLM route.

#                             direct_error_text = str(
#                                 direct_error
#                             )

#                     else:

#                         direct_error_text = None

#                     # ----------------------------------------
#                     # LLM CLIENT
#                     # ----------------------------------------

#                     llm_client = create_llm_client()

#                     # ----------------------------------------
#                     # HISTORY
#                     # ----------------------------------------

#                     messages = [
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

#                             if role in {
#                                 "user",
#                                 "assistant",
#                             } and content:

#                                 messages.append(
#                                     {
#                                         "role": role,
#                                         "content": content,
#                                     }
#                                 )

#                     messages.append(
#                         {
#                             "role": "user",
#                             "content": user_message,
#                         }
#                     )

#                     # ----------------------------------------
#                     # TOOL-CALLING LOOP
#                     # ----------------------------------------

#                     openai_tools = self._openai_tools()

#                     max_iterations = 6

#                     for _ in range(max_iterations):

#                         response = await self._ask_llm(
#                             llm_client,
#                             messages,
#                             openai_tools,
#                         )

#                         choice = response.choices[0]
#                         message = choice.message

#                         # ------------------------------------
#                         # TOOL CALLS
#                         # ------------------------------------

#                         tool_calls = getattr(
#                             message,
#                             "tool_calls",
#                             None,
#                         )

#                         if tool_calls:

#                             assistant_message = {
#                                 "role": "assistant",
#                                 "content": (
#                                     message.content
#                                     or ""
#                                 ),
#                                 "tool_calls": [],
#                             }

#                             for tool_call in tool_calls:

#                                 function = (
#                                     tool_call.function
#                                 )

#                                 tool_name = (
#                                     function.name
#                                 )

#                                 raw_arguments = (
#                                     function.arguments
#                                 )

#                                 try:

#                                     arguments = json.loads(
#                                         raw_arguments
#                                         or "{}"
#                                     )

#                                 except Exception:

#                                     arguments = {}

#                                 assistant_message[
#                                     "tool_calls"
#                                 ].append(
#                                     {
#                                         "id": tool_call.id,
#                                         "type": "function",
#                                         "function": {
#                                             "name": tool_name,
#                                             "arguments": (
#                                                 raw_arguments
#                                                 or "{}"
#                                             ),
#                                         },
#                                     }
#                                 )

#                             messages.append(
#                                 assistant_message
#                             )

#                             # Execute each requested MCP tool
#                             for tool_call in tool_calls:

#                                 function = (
#                                     tool_call.function
#                                 )

#                                 tool_name = (
#                                     function.name
#                                 )

#                                 try:

#                                     arguments = json.loads(
#                                         function.arguments
#                                         or "{}"
#                                     )

#                                 except Exception:

#                                     arguments = {}

#                                 try:

#                                     tool_result = (
#                                         await self._call_tool(
#                                             session,
#                                             tool_name,
#                                             arguments,
#                                         )
#                                     )

#                                     formatted_result = (
#                                         self._format_tool_result(
#                                             tool_name,
#                                             tool_result,
#                                         )
#                                     )

#                                 except Exception as tool_error:

#                                     formatted_result = (
#                                         "MCP tool error: "
#                                         + str(tool_error)
#                                     )

#                                 messages.append(
#                                     {
#                                         "role": "tool",
#                                         "tool_call_id": (
#                                             tool_call.id
#                                         ),
#                                         "content": (
#                                             formatted_result
#                                         ),
#                                     }
#                                 )

#                             continue

#                         # ------------------------------------
#                         # NORMAL FINAL ANSWER
#                         # ------------------------------------

#                         answer = (
#                             message.content
#                             or "I could not generate an answer."
#                         )

#                         return answer

#                     return (
#                         "I was unable to complete the request "
#                         "within the allowed tool-call steps."
#                     )

#         except Exception as error:

#             error_text = str(error)

#             return (
#                 "I couldn't connect to the PSX MCP server.\n\n"
#                 f"Error: {error_text}"
#             )

#         finally:

#             if http_client is not None:

#                 try:
#                     await http_client.aclose()
#                 except Exception:
#                     pass

#     # ========================================================
#     # PUBLIC CHAT METHOD
#     # ========================================================

#     def chat(
#         self,
#         user_message: str,
#         history: list | None = None,
#     ):

#         result = asyncio.run(
#             self._chat_async(
#                 user_message=user_message,
#                 history=history,
#             )
#         )

#         self.conversation_history.append(
#             {
#                 "role": "user",
#                 "content": user_message,
#             }
#         )

#         self.conversation_history.append(
#             {
#                 "role": "assistant",
#                 "content": result,
#             }
#         )

#         return result


# # ============================================================
# # GLOBAL CHATBOT INSTANCE
# # ============================================================

# _CHATBOT = PSXChatbot()


# # ============================================================
# # STREAMLIT / EXTERNAL ENTRY POINT
# # ============================================================

# def ask_chatbot(
#     user_message: str,
#     history: list | None = None,
# ):

#     return _CHATBOT.chat(
#         user_message=user_message,
#         history=history,
#     )





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
    "https://sore-tan-dove.fastmcp.app/mcp",
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

            normalized_map: dict[str, str] = {}

            for item in possible_industries:
                if isinstance(item, dict):
                    name = (
                        item.get("industry")
                        or item.get("name")
                        or item.get("sector")
                    )
                else:
                    name = str(item)

                if name:
                    normalized_map[
                        self._normalize_text(name)
                    ] = str(name)

            # Prefer exact phrase / substring matches.
            for normalized_name, original_name in normalized_map.items():
                if normalized_name in question_normalized:
                    return original_name

            # Fuzzy matching against individual words.
            question_words = [
                word
                for word in question_normalized.split()
                if len(word) >= 4
            ]

            for normalized_name, original_name in normalized_map.items():
                full_ratio = difflib.SequenceMatcher(
                    None,
                    normalized_name,
                    question_normalized,
                ).ratio()

                if full_ratio >= 0.80:
                    return original_name

                for word in question_words:
                    ratio = difflib.SequenceMatcher(
                        None,
                        normalized_name,
                        word,
                    ).ratio()

                    if ratio >= 0.90:
                        return original_name

        except Exception:
            # Industry detection is an optional optimisation.
            # The normal LLM tool route remains available.
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
You are a professional Pakistan Stock Exchange (PSX) data assistant.

Use MCP tools whenever the answer depends on PSX data.

Rules:
1. Never invent stock prices, percentage changes, volumes, symbols, industries, or other market data.
2. For current/latest PSX information, retrieve the data through an MCP tool.
3. Treat MCP tool output as the source of truth for market facts.
4. Do not call a tool that is not present in the supplied tool list.
5. Keep financial data clearly attributed to the retrieved data.
6. Do not describe data as real-time unless the underlying PSX API actually provides real-time data.
7. If a tool fails or returns no data, state that the requested data could not be retrieved.
8. Do not fabricate analysis from missing data.
9. You are a data assistant, not a financial advisor.
10. Keep final answers clear, concise, and useful.
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
            async with streamable_http_client(
                MCP_SERVER_URL,
            ) as (read_stream, write_stream):

                async with ClientSession(
                    read_stream,
                    write_stream,
                ) as session:

                    await session.initialize()
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
