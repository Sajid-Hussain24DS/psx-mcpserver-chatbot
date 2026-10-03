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