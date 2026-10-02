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




from __future__ import annotations

import asyncio
import difflib
import json
import os
import re

import httpx2
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import (
    streamable_http_client,
)

from chatbot.auth import (
    OAuthCallbackServer,
    create_oauth_provider,
)

from chatbot.formatters import (
    format_industries,
    format_stock_data,
    format_symbols,
    format_top_bottom,
)

from chatbot.llm import create_llm_client


load_dotenv()


# =========================================================
# CONFIG
# =========================================================

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "https://fluttering-blue-ox.fastmcp.app/mcp",
)

LLM_PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "groq",
).lower()

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "openai/gpt-oss-120b",
)


# =========================================================
# CHATBOT
# =========================================================

class PSXChatbot:

    def __init__(self) -> None:

        self.tools = []
        self.tool_map = {}

        self.last_tool = None
        self.last_arguments = {}

        self.conversation_history = []

    # =====================================================
    # NORMALIZE TEXT
    # =====================================================

    @staticmethod
    def _normalize_text(value: str) -> str:

        value = value.lower().strip()

        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value,
        )

        return " ".join(
            value.split()
        )

    # =====================================================
    # EXTRACT INDUSTRY FROM QUESTION
    # =====================================================

    def _find_industry_in_question(
        self,
        user_message: str,
        industries: list[str],
    ) -> str | None:

        question = self._normalize_text(
            user_message
        )

        normalized_industries = []

        for industry in industries:

            normalized = self._normalize_text(
                industry
            )

            if normalized:

                normalized_industries.append(
                    (
                        normalized,
                        industry,
                    )
                )

        # Exact/substring match first.

        for normalized, original in normalized_industries:

            if normalized in question:

                return original

        # Extract text after common phrases.

        patterns = (
            r"\bstocks?\s+(?:in|of|from)\s+(.+)$",
            r"\bshares?\s+(?:in|of|from)\s+(.+)$",
            r"\bcompanies\s+(?:in|of|from)\s+(.+)$",
            r"\b(?:industry|sector)\s*[:\-]?\s*(.+)$",
        )

        candidate = None

        for pattern in patterns:

            match = re.search(
                pattern,
                question,
            )

            if match:

                candidate = match.group(1).strip()

                break

        if not candidate:

            return None

        # Exact candidate match.

        for normalized, original in normalized_industries:

            if candidate == normalized:

                return original

        # Conservative fuzzy matching.

        matches = difflib.get_close_matches(
            candidate,
            [
                normalized
                for normalized, _ in normalized_industries
            ],
            n=1,
            cutoff=0.90,
        )

        if matches:

            matched = matches[0]

            for normalized, original in normalized_industries:

                if normalized == matched:

                    return original

        return None

    # =====================================================
    # DIRECT TOOL ROUTING
    # =====================================================

    async def _detect_direct_tool(
        self,
        user_message: str,
        session,
    ):

        q = " ".join(
            user_message.lower().split()
        )

        # -------------------------------------------------
        # SYMBOLS
        # -------------------------------------------------

        if any(
            word in q
            for word in (
                "symbol",
                "symbols",
                "ticker",
                "tickers",
            )
        ):

            return (
                "get_symbols",
                {},
            )

        # -------------------------------------------------
        # RANKINGS FIRST
        # -------------------------------------------------

        if (
            (
                "top" in q
                or "highest" in q
                or "gainer" in q
                or "gainers" in q
            )
            and "volume" in q
        ):

            return (
                "get_top_volume",
                {},
            )

        if (
            (
                "bottom" in q
                or "lowest" in q
                or "loser" in q
                or "losers" in q
            )
            and "volume" in q
        ):

            return (
                "get_bottom_volume",
                {},
            )

        if (
            (
                "top" in q
                or "highest" in q
                or "gainer" in q
                or "gainers" in q
            )
            and (
                "change" in q
                or "percent" in q
                or "%" in q
            )
        ):

            return (
                "get_top_change",
                {},
            )

        if (
            (
                "bottom" in q
                or "lowest" in q
                or "loser" in q
                or "losers" in q
            )
            and (
                "change" in q
                or "percent" in q
                or "%" in q
            )
        ):

            return (
                "get_bottom_change",
                {},
            )

        # -------------------------------------------------
        # STOCK WORDS
        # -------------------------------------------------

        has_stock_word = any(
            word in q
            for word in (
                "stock",
                "stocks",
                "share",
                "shares",
                "security",
                "securities",
                "company",
                "companies",
            )
        )

        has_all_word = any(
            word in q
            for word in (
                "all",
                "every",
                "list",
                "show",
            )
        )

        # -------------------------------------------------
        # STOCK REQUESTS
        # -------------------------------------------------

        if has_stock_word:

            # Ask for a specific industry.

            if any(
                phrase in q
                for phrase in (
                    " in ",
                    " of ",
                    " from ",
                    "industry",
                    "sector",
                )
            ):

                industries_result = (
                    await self._call_tool(
                        session,
                        "get_industries",
                        {},
                    )
                )

                industries_data = (
                    self._extract_tool_result(
                        industries_result
                    )
                )

                industries = (
                    self._extract_industry_names(
                        industries_data
                    )
                )

                industry = (
                    self._find_industry_in_question(
                        user_message,
                        industries,
                    )
                )

                if industry:

                    return (
                        "get_stocks",
                        {
                            "industry": industry,
                        },
                    )

            # All stocks.

            if has_all_word:

                return (
                    "__all_stocks__",
                    {},
                )

        # -------------------------------------------------
        # INDUSTRIES
        # -------------------------------------------------

        if any(
            phrase in q
            for phrase in (
                "list industries",
                "list industry",
                "all industries",
                "all industry",
                "available industries",
                "available sectors",
                "industry list",
                "sector list",
                "list sectors",
            )
        ):

            return (
                "get_industries",
                {},
            )

        return None

    # =====================================================
    # EXTRACT INDUSTRY NAMES
    # =====================================================

    def _extract_industry_names(
        self,
        data,
    ) -> list[str]:

        if isinstance(data, list):

            rows = data

        elif isinstance(data, dict):

            rows = []

            for key in (
                "data",
                "results",
                "result",
                "items",
                "industries",
            ):

                value = data.get(key)

                if isinstance(value, list):

                    rows = value

                    break

        else:

            rows = []

        industries = []

        for item in rows:

            if isinstance(item, str):

                value = item.strip()

                if value:

                    industries.append(value)

            elif isinstance(item, dict):

                for key in (
                    "industry",
                    "Industry",
                    "name",
                    "Name",
                ):

                    value = item.get(key)

                    if value:

                        industries.append(
                            str(value).strip()
                        )

                        break

        # Remove duplicates while preserving order.

        unique = []

        seen = set()

        for industry in industries:

            normalized = self._normalize_text(
                industry
            )

            if (
                normalized
                and normalized not in seen
            ):

                seen.add(normalized)

                unique.append(industry)

        return unique

    # =====================================================
    # MCP CONNECTION
    # =====================================================

    async def _connect_mcp(self):

        callback_server = (
            OAuthCallbackServer()
        )

        callback_server.start()

        oauth = create_oauth_provider(
            callback_server
        )

        http_client = httpx2.AsyncClient(

            auth=oauth,

            timeout=httpx2.Timeout(
                30.0,
                read=300.0,
            ),
        )

        return (
            callback_server,
            http_client,
        )

    # =====================================================
    # LOAD MCP TOOLS
    # =====================================================

    async def _load_tools(
        self,
        session,
    ):

        result = await session.list_tools()

        self.tools = result.tools

        self.tool_map = {
            tool.name: tool
            for tool in self.tools
        }

    # =====================================================
    # OPENAI TOOL FORMAT
    # =====================================================

    def _openai_tools(self):

        openai_tools = []

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

            if input_schema is None:

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
                            tool.description
                            or f"MCP tool {tool.name}"
                        ),
                        "parameters": input_schema,
                    },
                }
            )

        return openai_tools

    # =====================================================
    # CALL MCP TOOL
    # =====================================================

    async def _call_tool(
        self,
        session,
        tool_name: str,
        arguments: dict,
    ):

        self.last_tool = tool_name

        self.last_arguments = arguments

        result = await session.call_tool(
            tool_name,
            arguments,
        )

        # MCP tool-level error.

        if getattr(
            result,
            "is_error",
            False,
        ):

            content = getattr(
                result,
                "content",
                [],
            )

            error_text = []

            for item in content:

                text_value = getattr(
                    item,
                    "text",
                    None,
                )

                if text_value:

                    error_text.append(
                        str(text_value)
                    )

            message = (
                "\n".join(error_text).strip()
                or "Unknown MCP tool error."
            )

            raise RuntimeError(
                f"{tool_name} failed: {message}"
            )

        return result

    # =====================================================
    # EXTRACT MCP RESULT
    # =====================================================

    def _extract_tool_result(
        self,
        result,
    ):

        if isinstance(
            result,
            (list, dict),
        ):

            return result

        # Preferred application data.

        structured = getattr(
            result,
            "structured_content",
            None,
        )

        if structured is not None:

            return structured

        structured = getattr(
            result,
            "structuredContent",
            None,
        )

        if structured is not None:

            return structured

        # Model/content representation.

        content = getattr(
            result,
            "content",
            None,
        )

        if content:

            collected_text = []

            for item in content:

                text_value = getattr(
                    item,
                    "text",
                    None,
                )

                if text_value:

                    collected_text.append(
                        str(text_value)
                    )

            if collected_text:

                combined_text = "\n".join(
                    collected_text
                ).strip()

                try:

                    return json.loads(
                        combined_text
                    )

                except json.JSONDecodeError:

                    return combined_text

        model_dump = getattr(
            result,
            "model_dump",
            None,
        )

        if callable(model_dump):

            try:

                dumped = model_dump()

                if isinstance(
                    dumped,
                    (dict, list),
                ):

                    return dumped

            except Exception:

                pass

        return result

    # =====================================================
    # FORMAT MCP RESULT
    # =====================================================

    def _format_tool_result(
        self,
        tool_name: str,
        result,
        arguments: dict,
    ):

        raw_data = self._extract_tool_result(
            result
        )

        if tool_name == "get_symbols":

            return format_symbols(
                raw_data
            )

        if tool_name == "get_industries":

            return format_industries(
                raw_data
            )

        if tool_name == "get_stocks":

            return format_stock_data(
                raw_data,
                arguments.get(
                    "industry",
                    "",
                ),
            )

        if tool_name in {
            "get_top_change",
            "get_bottom_change",
            "get_top_volume",
            "get_bottom_volume",
        }:

            return format_top_bottom(
                raw_data,
                tool_name,
            )

        return json.dumps(
            raw_data,
            ensure_ascii=False,
            default=str,
        )

    # =====================================================
    # ALL STOCKS
    # =====================================================

    async def _get_all_stocks(
        self,
        session,
    ) -> tuple[str, dict]:

        # First get the valid industry names.

        industries_result = (
            await self._call_tool(
                session,
                "get_industries",
                {},
            )
        )

        industries_data = (
            self._extract_tool_result(
                industries_result
            )
        )

        industries = (
            self._extract_industry_names(
                industries_data
            )
        )

        if not industries:

            raise RuntimeError(
                "MCP returned no industries, "
                "so all stocks could not be loaded."
            )

        all_rows = []

        for industry in industries:

            result = await self._call_tool(
                session,
                "get_stocks",
                {
                    "industry": industry,
                },
            )

            data = self._extract_tool_result(
                result
            )

            rows = self._data_rows(
                data
            )

            for row in rows:

                if isinstance(row, dict):

                    item = dict(row)

                    if not item.get(
                        "industry"
                    ):

                        item["industry"] = industry

                    all_rows.append(item)

        # Deduplicate by symbol.

        unique_rows = []

        seen_symbols = set()

        for row in all_rows:

            symbol = (
                row.get("symbol")
                or row.get("Symbol")
                or row.get("ticker")
                or row.get("Ticker")
            )

            if symbol:

                key = str(
                    symbol
                ).strip().upper()

            else:

                key = json.dumps(
                    row,
                    sort_keys=True,
                    default=str,
                )

            if key in seen_symbols:

                continue

            seen_symbols.add(key)

            unique_rows.append(row)

        self.last_tool = "get_stocks"

        self.last_arguments = {
            "industry": "ALL",
            "industries_requested": len(
                industries
            ),
        }

        return (
            format_stock_data(
                unique_rows
            ),
            self.last_arguments,
        )

    # =====================================================
    # EXTRACT ROWS
    # =====================================================

    def _data_rows(
        self,
        data,
    ) -> list:

        if isinstance(
            data,
            list,
        ):

            return data

        if isinstance(
            data,
            dict,
        ):

            for key in (
                "data",
                "results",
                "result",
                "items",
                "stocks",
                "records",
            ):

                value = data.get(key)

                if isinstance(
                    value,
                    list,
                ):

                    return value

                if isinstance(
                    value,
                    dict,
                ):

                    nested = self._data_rows(
                        value
                    )

                    if nested:

                        return nested

            # Single stock object.

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

    # =====================================================
    # SYSTEM PROMPT
    # =====================================================

    def _system_prompt(self):

        return """
You are the PSX Chatbot.

You answer Pakistan Stock Exchange questions
using MCP tools.

IMPORTANT:

- Never invent PSX data.
- MCP results are the source of truth.
- Always use an MCP tool for PSX market data.
- Do not answer PSX market-data questions from memory.

Tool rules:

get_symbols:
Use for symbols and tickers.

get_industries:
Use for industries and sectors.

get_stocks:
Use for stock listings.
The industry argument is REQUIRED.
If an industry is specified, pass the exact
industry name returned by get_industries.

get_top_change:
Use for top gainers/change percentage.

get_bottom_change:
Use for bottom/lowest change percentage.

get_top_volume:
Use for highest trading volume.

get_bottom_volume:
Use for lowest trading volume.

Do not provide investment guarantees.
Do not provide personalized financial advice.

Keep answers concise and preserve numerical values.
"""

    # =====================================================
    # LLM CALL
    # =====================================================

    async def _ask_llm(
        self,
        client,
        messages,
    ):

        return await client.chat.completions.create(

            model=LLM_MODEL,

            messages=messages,

            tools=self._openai_tools(),

            tool_choice="auto",

            temperature=0,
        )

    # =====================================================
    # CHAT
    # =====================================================

    async def _chat_async(
        self,
        user_message: str,
    ):

        callback_server = None
        http_client = None

        try:

            (
                callback_server,
                http_client,
            ) = await self._connect_mcp()

            async with http_client:

                async with streamable_http_client(
                    MCP_SERVER_URL,
                    http_client=http_client,
                ) as (
                    read_stream,
                    write_stream,
                ):

                    async with ClientSession(
                        read_stream,
                        write_stream,
                    ) as session:

                        await session.initialize()

                        await self._load_tools(
                            session
                        )

                        # ---------------------------------
                        # DIRECT ROUTING
                        # ---------------------------------

                        direct_tool = (
                            await self._detect_direct_tool(
                                user_message,
                                session,
                            )
                        )

                        if direct_tool:

                            (
                                tool_name,
                                arguments,
                            ) = direct_tool

                            # ALL STOCKS

                            if tool_name == "__all_stocks__":

                                answer, arguments = (
                                    await self._get_all_stocks(
                                        session
                                    )
                                )

                                self.conversation_history.append(
                                    {
                                        "role": "user",
                                        "content": user_message,
                                    }
                                )

                                self.conversation_history.append(
                                    {
                                        "role": "assistant",
                                        "content": answer,
                                    }
                                )

                                return {
                                    "answer": answer,
                                    "tool": self.last_tool,
                                    "arguments": arguments,
                                }

                            if (
                                tool_name
                                not in self.tool_map
                            ):

                                raise RuntimeError(
                                    f"MCP tool "
                                    f"'{tool_name}' "
                                    f"was not found."
                                )

                            result = (
                                await self._call_tool(
                                    session,
                                    tool_name,
                                    arguments,
                                )
                            )

                            answer = (
                                self._format_tool_result(
                                    tool_name,
                                    result,
                                    arguments,
                                )
                            )

                            self.conversation_history.append(
                                {
                                    "role": "user",
                                    "content": user_message,
                                }
                            )

                            self.conversation_history.append(
                                {
                                    "role": "assistant",
                                    "content": answer,
                                }
                            )

                            return {
                                "answer": answer,
                                "tool": self.last_tool,
                                "arguments": self.last_arguments,
                            }

                        # ---------------------------------
                        # LLM FALLBACK
                        # ---------------------------------

                        llm_client = (
                            create_llm_client()
                        )

                        messages = [
                            {
                                "role": "system",
                                "content": (
                                    self._system_prompt()
                                ),
                            }
                        ]

                        messages.extend(
                            self.conversation_history
                        )

                        messages.append(
                            {
                                "role": "user",
                                "content": user_message,
                            }
                        )

                        # ---------------------------------
                        # TOOL-CALLING LOOP
                        # ---------------------------------

                        for _ in range(6):

                            response = (
                                await self._ask_llm(
                                    llm_client,
                                    messages,
                                )
                            )

                            message = (
                                response.choices[
                                    0
                                ].message
                            )

                            tool_calls = (
                                message.tool_calls
                            )

                            # ---------------------------------
                            # FINAL ANSWER
                            # ---------------------------------

                            if not tool_calls:

                                final_answer = (
                                    message.content
                                    or "I could not generate a response."
                                )

                                self.conversation_history.append(
                                    {
                                        "role": "user",
                                        "content": user_message,
                                    }
                                )

                                self.conversation_history.append(
                                    {
                                        "role": "assistant",
                                        "content": final_answer,
                                    }
                                )

                                return {
                                    "answer": final_answer,
                                    "tool": self.last_tool,
                                    "arguments": self.last_arguments,
                                }

                            # ---------------------------------
                            # ASSISTANT TOOL CALLS
                            # ---------------------------------

                            assistant_tool_calls = []

                            for call in tool_calls:

                                assistant_tool_calls.append(
                                    {
                                        "id": call.id,
                                        "type": "function",
                                        "function": {
                                            "name": (
                                                call.function.name
                                            ),
                                            "arguments": (
                                                call.function.arguments
                                            ),
                                        },
                                    }
                                )

                            messages.append(
                                {
                                    "role": "assistant",
                                    "content": (
                                        message.content
                                        or None
                                    ),
                                    "tool_calls": (
                                        assistant_tool_calls
                                    ),
                                }
                            )

                            # ---------------------------------
                            # EXECUTE TOOLS
                            # ---------------------------------

                            for call in tool_calls:

                                tool_name = (
                                    call.function.name
                                )

                                try:

                                    arguments = json.loads(
                                        call.function.arguments
                                    )

                                except (
                                    json.JSONDecodeError,
                                ):

                                    arguments = {}

                                # ---------------------------------
                                # SAFETY: get_stocks REQUIRES
                                # industry.
                                # ---------------------------------

                                if (
                                    tool_name == "get_stocks"
                                    and not arguments.get(
                                        "industry"
                                    )
                                ):

                                    tool_output = (
                                        "The get_stocks MCP tool "
                                        "requires an industry."
                                    )

                                elif (
                                    tool_name
                                    not in self.tool_map
                                ):

                                    tool_output = (
                                        f"Unknown MCP tool: "
                                        f"{tool_name}"
                                    )

                                else:

                                    result = (
                                        await self._call_tool(
                                            session,
                                            tool_name,
                                            arguments,
                                        )
                                    )

                                    tool_output = (
                                        self._format_tool_result(
                                            tool_name,
                                            result,
                                            arguments,
                                        )
                                    )

                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": call.id,
                                        "content": str(
                                            tool_output
                                        ),
                                    }
                                )

                        return {
                            "answer": (
                                "I could not complete "
                                "the PSX request."
                            ),
                            "tool": self.last_tool,
                            "arguments": self.last_arguments,
                        }

        except Exception as exc:

            root = exc

            while (
                hasattr(root, "exceptions")
                and root.exceptions
            ):

                root = root.exceptions[0]

            raise RuntimeError(
                "MCP chatbot error: "
                f"{type(root).__name__}: {root}"
            ) from exc

        finally:

            if callback_server is not None:

                callback_server.stop()

    # =====================================================
    # PUBLIC CHAT
    # =====================================================

    def chat(
        self,
        user_message: str,
    ):

        return asyncio.run(
            self._chat_async(
                user_message
            )
        )


# =========================================================
# GLOBAL CHATBOT INSTANCE
# =========================================================

_CHATBOT = PSXChatbot()


# =========================================================
# STREAMLIT ENTRY POINT
# =========================================================

def ask_chatbot(
    user_message: str,
    history=None,
) -> dict:

    if history is not None:

        _CHATBOT.conversation_history = []

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
                role in {
                    "user",
                    "assistant",
                }
                and content
            ):

                _CHATBOT.conversation_history.append(
                    {
                        "role": role,
                        "content": str(content),
                    }
                )

    return _CHATBOT.chat(
        user_message
    )