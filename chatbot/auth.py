from __future__ import annotations

import asyncio
import os
import sqlite3
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from pydantic import AnyUrl

from mcp.client.auth import (
    AuthorizationCodeResult,
    OAuthClientProvider,
)
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)


# =========================================================
# CONFIG
# =========================================================

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "https://fluttering-blue-ox.fastmcp.app/mcp",
)

CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 3030

CALLBACK_URL = (
    f"http://{CALLBACK_HOST}:{CALLBACK_PORT}/callback"
)

TOKEN_DB = os.getenv(
    "OAUTH_TOKEN_DB",
    "psx_oauth.db",
)


# =========================================================
# PERSISTENT OAUTH STORAGE
# =========================================================

class PersistentTokenStorage:
    """
    Stores OAuth tokens and MCP client information
    in a local SQLite database.
    """

    def __init__(self, db_path: str = TOKEN_DB):
        self.db_path = db_path
        self._lock = threading.Lock()

        self._initialize_database()

    def _connect(self):
        return sqlite3.connect(
            self.db_path,
            check_same_thread=False,
        )

    def _initialize_database(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_storage (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _get(self, key: str):
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    SELECT value
                    FROM oauth_storage
                    WHERE key = ?
                    """,
                    (key,),
                )

                row = cursor.fetchone()

                if row:
                    return row[0]

        return None

    def _set(self, key: str, value: str):
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO oauth_storage(key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key)
                    DO UPDATE SET value = excluded.value
                    """,
                    (key, value),
                )

                conn.commit()

    async def get_tokens(self):
        value = self._get("tokens")

        if not value:
            return None

        return OAuthToken.model_validate_json(value)

    async def set_tokens(
        self,
        tokens: OAuthToken,
    ) -> None:

        self._set(
            "tokens",
            tokens.model_dump_json(),
        )

    async def get_client_info(self):
        value = self._get("client_info")

        if not value:
            return None

        return OAuthClientInformationFull.model_validate_json(
            value
        )

    async def set_client_info(
        self,
        client_info: OAuthClientInformationFull,
    ) -> None:

        self._set(
            "client_info",
            client_info.model_dump_json(),
        )


_OAUTH_STORAGE = PersistentTokenStorage()


# =========================================================
# OAUTH CALLBACK SERVER
# =========================================================

class OAuthCallbackServer:

    def __init__(
        self,
        host: str = CALLBACK_HOST,
        port: int = CALLBACK_PORT,
    ):

        self.host = host
        self.port = port

        self.server = None
        self.thread = None

        self.code = None
        self.state = None
        self.iss = None
        self.error = None

        self.event = threading.Event()

    def start(self):

        callback_server = self

        class CallbackHandler(BaseHTTPRequestHandler):

            def do_GET(self):

                parsed = urlparse(self.path)

                if parsed.path != "/callback":

                    self.send_response(404)
                    self.end_headers()

                    return

                params = parse_qs(
                    parsed.query
                )

                callback_server.code = params.get(
                    "code",
                    [None],
                )[0]

                callback_server.state = params.get(
                    "state",
                    [None],
                )[0]

                callback_server.iss = params.get(
                    "iss",
                    [None],
                )[0]

                callback_server.error = params.get(
                    "error",
                    [None],
                )[0]

                callback_server.event.set()

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8",
                )

                self.end_headers()

                if callback_server.error:

                    message = (
                        "<h2>"
                        "PSX Chatbot authorization failed."
                        "</h2>"
                        f"<p>{callback_server.error}</p>"
                        "<p>You can close this tab.</p>"
                    )

                else:

                    message = (
                        "<h2>"
                        "PSX Chatbot authorized."
                        "</h2>"
                        "<p>"
                        "You can close this tab and return "
                        "to Streamlit."
                        "</p>"
                    )

                html = f"""
                <!doctype html>
                <html>
                <head>
                    <title>PSX Chatbot</title>
                </head>
                <body>
                    {message}
                </body>
                </html>
                """

                self.wfile.write(
                    html.encode("utf-8")
                )

            def log_message(
                self,
                format,
                *args,
            ):
                return

        try:

            self.server = ThreadingHTTPServer(
                (
                    self.host,
                    self.port,
                ),
                CallbackHandler,
            )

        except OSError as exc:

            raise RuntimeError(
                f"Port {self.port} is already in use. "
                "Close the old PSX chatbot/Streamlit "
                "process and start again."
            ) from exc

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )

        self.thread.start()

    def wait_for_callback(
        self,
        timeout: int = 300,
    ) -> AuthorizationCodeResult:

        received = self.event.wait(timeout)

        if not received:

            raise TimeoutError(
                "OAuth callback timed out after "
                f"{timeout} seconds."
            )

        if self.error:

            raise RuntimeError(
                "OAuth authorization failed: "
                f"{self.error}"
            )

        if not self.code:

            raise RuntimeError(
                "OAuth callback did not contain "
                "an authorization code."
            )

        return AuthorizationCodeResult(
            code=self.code,
            state=self.state,
            iss=self.iss,
        )

    def stop(self):

        if self.server is not None:

            self.server.shutdown()
            self.server.server_close()

            self.server = None


# =========================================================
# OAUTH PROVIDER
# =========================================================

def create_oauth_provider(
    callback_server: OAuthCallbackServer,
):

    async def redirect_handler(
        authorization_url: str,
    ) -> None:

        print(
            "\n========================================"
        )

        print(
            "PSX MCP authorization required."
        )

        print(
            "Opening browser..."
        )

        print(
            "========================================\n"
        )

        webbrowser.open_new_tab(
            authorization_url
        )

    async def callback_handler():

        try:

            return await asyncio.to_thread(
                callback_server.wait_for_callback,
                300,
            )

        finally:

            callback_server.stop()

    return OAuthClientProvider(

        server_url=MCP_SERVER_URL,

        client_metadata=OAuthClientMetadata(

            client_name="PSX Chatbot",

            redirect_uris=[
                AnyUrl(CALLBACK_URL)
            ],

            grant_types=[
                "authorization_code",
                "refresh_token",
            ],

            response_types=[
                "code"
            ],

            scope="user",
        ),

        storage=_OAUTH_STORAGE,

        redirect_handler=redirect_handler,

        callback_handler=callback_handler,
    )