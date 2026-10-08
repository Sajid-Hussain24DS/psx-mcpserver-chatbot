import streamlit as st

from chatbot.chatbot import ask_chatbot


st.set_page_config(
    page_title="PSX Intelligence",
    page_icon="P",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_html(html: str) -> None:
    flat = "\n".join(
        line.strip() for line in html.splitlines() if line.strip()
    )
    st.markdown(flat, unsafe_allow_html=True)


# -------------------------------------------------------------------
# UI STYLES
# -------------------------------------------------------------------

render_html(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

:root {
    --bg: #0c0d0f;
    --sidebar: #0f1012;
    --surface: #131417;
    --surface-hover: #1a1b1f;
    --border: #232429;
    --border-hover: #34363d;
    --text: #e8e9eb;
    --text-soft: #c4c6cb;
    --muted: #8a8d95;
    --faint: #5d6068;
    --accent: #5fbf8a;
    --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color-scheme: dark;
}

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--font);
}

button, textarea, input,
[data-testid="stMarkdownContainer"] {
    font-family: var(--font) !important;
}

.block-container {
    max-width: 900px !important;
    padding: 2rem 2rem 6rem !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
}

[data-testid="stDecoration"],
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],
#MainMenu,
footer {
    display: none !important;
}

::selection {
    background: rgba(95,191,138,0.28);
}

:focus-visible {
    outline: 2px solid var(--accent) !important;
    outline-offset: 2px;
}

/* ---------- Bottom bar ---------- */

[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {
    background: var(--bg) !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stBottomBlockContainer"] {
    max-width: 900px !important;
    margin: 0 auto !important;
    padding: 0.5rem 2rem 1.25rem !important;
}

/* ---------- Sidebar ---------- */

section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
    background: var(--sidebar) !important;
}

section[data-testid="stSidebar"] {
    border-right: 1px solid var(--border) !important;
}

section[data-testid="stSidebar"][aria-expanded="true"] {
    min-width: 268px !important;
    max-width: 268px !important;
}

section[data-testid="stSidebar"] .block-container,
[data-testid="stSidebarUserContent"] {
    padding: 1.25rem 0.9rem !important;
}

section[data-testid="stSidebar"] hr {
    border-color: var(--border) !important;
    opacity: 1 !important;
    margin: 1rem 0 !important;
}

.brand {
    padding: 0 0.25rem 1rem;
}

.brand-title {
    color: var(--text);
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.brand-subtitle {
    margin-top: 0.2rem;
    color: var(--muted);
    font-size: 0.76rem;
    line-height: 1.4;
}

.section-label {
    color: var(--muted);
    font-size: 0.74rem;
    font-weight: 500;
    margin: 0 0 0.5rem 0.25rem;
}

/* ---------- Sidebar buttons ---------- */

section[data-testid="stSidebar"] button {
    min-height: 36px !important;
    justify-content: flex-start !important;
    text-align: left !important;
    background: transparent !important;
    color: var(--text-soft) !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    padding: 0.4rem 0.7rem !important;
    transition:
        background 0.15s ease,
        color 0.15s ease,
        border-color 0.15s ease;
}

section[data-testid="stSidebar"] button p {
    font-size: 0.85rem !important;
    font-weight: 400;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

section[data-testid="stSidebar"] button:hover {
    background: var(--surface-hover) !important;
    color: var(--text) !important;
}

/* New chat */

section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}

section[data-testid="stSidebar"] button[kind="primary"]:hover,
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
    border-color: var(--border-hover) !important;
}

/* ---------- System info ---------- */

.system-info {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
}

.sidebar-note {
    color: var(--muted);
    font-size: 0.76rem;
    line-height: 1.7;
    padding: 0 0.25rem;
}

/* ---------- Page header ---------- */

.page-header {
    margin-bottom: 1.5rem;
}

.page-header h1 {
    margin: 0;
    padding: 0;
    color: var(--text);
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.page-header p {
    margin: 0.45rem 0 0;
    max-width: 620px;
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.55;
}

.status {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    margin-top: 0.9rem;
    color: var(--muted);
    font-size: 0.78rem;
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
}

/* ---------- Empty state ---------- */

[data-testid="stMarkdownContainer"] h3 {
    color: var(--text);
    font-size: 0.95rem !important;
    font-weight: 500;
    padding: 1.5rem 0 0 !important;
}

.suggestion {
    margin-top: 0.5rem;
    padding: 0.8rem 0;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    color: var(--text-soft);
    font-size: 0.87rem;
    line-height: 1.6;
}

/* ---------- Chat messages ---------- */

[data-testid="stChatMessage"] {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 12px !important;
    padding: 0.85rem 1rem !important;
    margin-bottom: 0.4rem !important;
    box-shadow: none !important;
}

[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageAvatarUser"]
) {
    background: var(--surface) !important;
    border-color: var(--border) !important;
}

[data-testid^="stChatMessageAvatar"] {
    background: var(--surface-hover) !important;
    color: var(--text-soft) !important;
    border: 1px solid var(--border) !important;
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    color: var(--text-soft) !important;
    font-size: 0.92rem !important;
    line-height: 1.65 !important;
}

[data-testid="stChatMessage"] strong {
    color: var(--text) !important;
    font-weight: 600;
}

[data-testid="stChatMessage"] code {
    background: var(--surface-hover) !important;
    border: 1px solid var(--border) !important;
    border-radius: 5px !important;
    color: var(--text) !important;
    font-size: 0.82rem !important;
}

/* ---------- Tables ---------- */

[data-testid="stChatMessage"] table {
    display: block;
    width: 100%;
    overflow-x: auto;
    border-collapse: collapse !important;
    border: 1px solid var(--border) !important;
    background: transparent !important;
    font-variant-numeric: tabular-nums;
}

[data-testid="stChatMessage"] thead tr {
    background: var(--surface) !important;
}

[data-testid="stChatMessage"] th,
[data-testid="stChatMessage"] td {
    padding: 0.55rem 0.8rem !important;
    border: none !important;
    border-bottom: 1px solid var(--border) !important;
    color: var(--text-soft) !important;
    font-size: 0.85rem !important;
    white-space: nowrap;
}

[data-testid="stChatMessage"] th {
    color: var(--muted) !important;
    font-weight: 500 !important;
}

[data-testid="stChatMessage"] tbody tr:last-child td {
    border-bottom: none !important;
}

[data-testid="stChatMessage"] tbody tr {
    background: transparent !important;
}

[data-testid="stChatMessage"] tbody tr:hover {
    background: var(--surface) !important;
}

/* ---------- Chat input ---------- */

[data-testid="stBottom"] [data-testid="stChatInput"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    transition: border-color 0.15s ease;
}

[data-testid="stBottom"] [data-testid="stChatInput"]:hover {
    border-color: var(--border-hover) !important;
}

[data-testid="stBottom"] [data-testid="stChatInput"]:focus-within {
    border-color: var(--accent) !important;
}

[data-testid="stBottom"] [data-testid="stChatInput"] div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    caret-color: var(--text) !important;
    font-size: 0.92rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--faint) !important;
    -webkit-text-fill-color: var(--faint) !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"] button {
    background: transparent !important;
    color: var(--muted) !important;
    border-radius: 8px !important;
}

[data-testid="stChatInput"] button:hover:not(:disabled) {
    background: var(--surface-hover) !important;
    color: var(--text) !important;
}

[data-testid="stChatInput"] button:disabled {
    color: var(--faint) !important;
}

/* ---------- Expander ---------- */

[data-testid="stExpander"],
[data-testid="stExpander"] details {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}

[data-testid="stExpander"] summary {
    color: var(--text-soft) !important;
}

[data-testid="stExpander"] summary p {
    font-size: 0.85rem !important;
}

[data-testid="stExpander"] summary:hover {
    color: var(--text) !important;
}

[data-testid="stExpander"]
[data-testid="stMarkdownContainer"] p {
    font-size: 0.8rem;
    color: var(--text-soft);
}

/* ---------- JSON / Alerts ---------- */

[data-testid="stJson"] {
    background: var(--surface) !important;
    border-radius: 8px;
}

section[data-testid="stSidebar"] pre {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

[data-testid="stAlert"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-soft) !important;
}

.stCaption,
[data-testid="stCaptionContainer"] {
    color: var(--muted) !important;
}

[data-testid="stSpinner"] {
    color: var(--muted) !important;
}

hr {
    border-color: var(--border) !important;
    opacity: 1 !important;
}

/* ---------- Scrollbar ---------- */

::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: #26282d;
    border-radius: 8px;
}

::-webkit-scrollbar-thumb:hover {
    background: #34363d;
}

/* ---------- Footer ---------- */

.footer-note {
    margin: 2rem 0 1rem;
    color: var(--faint);
    text-align: center;
    font-size: 0.74rem;
}

@media (max-width: 900px) {
    .block-container {
        padding: 1.25rem 1rem 6rem !important;
    }

    [data-testid="stBottomBlockContainer"] {
        padding: 0.5rem 1rem 1rem !important;
    }

    .page-header h1 {
        font-size: 1.3rem;
    }
}
</style>
"""
)


# -------------------------------------------------------------------
# SESSION STATE
# -------------------------------------------------------------------

if "chats" not in st.session_state:
    st.session_state.chats = {"New Chat": []}

if "active_chat" not in st.session_state:
    st.session_state.active_chat = "New Chat"

if "last_debug" not in st.session_state:
    st.session_state.last_debug = None

if "llm_config" not in st.session_state:
    st.session_state.llm_config = {
        "provider": "Default Groq",
        "api_url": "",
        "api_key": "",
        "model": "",
    }

# Used to display success messages after rerun.
if "llm_message" not in st.session_state:
    st.session_state.llm_message = None


def generate_chat_title(question: str) -> str:
    title = " ".join(question.strip().split())

    if len(title) > 42:
        title = title[:42].rstrip() + "..."

    return title or "New Chat"


def create_new_chat_name() -> str:
    if (
        "New Chat" not in st.session_state.chats
        or not st.session_state.chats["New Chat"]
    ):
        return "New Chat"

    counter = 1

    while f"New Chat {counter}" in st.session_state.chats:
        counter += 1

    return f"New Chat {counter}"


def select_chat(chat_name: str) -> None:
    st.session_state.active_chat = chat_name
    st.session_state.last_debug = None


# -------------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------------

with st.sidebar:

    render_html(
        """
        <div class="brand">
            <div class="brand-title">PSX Intelligence</div>
            <div class="brand-subtitle">
                MCP-powered Pakistan Stock Exchange assistant
            </div>
        </div>
        """
    )

    # ---------------------------------------------------------------
    # New Chat
    # ---------------------------------------------------------------

    if st.button(
        "New chat",
        use_container_width=True,
        type="primary",
    ):
        new_chat_name = create_new_chat_name()

        st.session_state.chats[new_chat_name] = []
        st.session_state.active_chat = new_chat_name
        st.session_state.last_debug = None

        st.rerun()

    st.divider()

    # ---------------------------------------------------------------
    # Recent Chats
    # ---------------------------------------------------------------

    render_html('<div class="section-label">Recent chats</div>')

    chat_names = list(st.session_state.chats.keys())

    for chat_name in chat_names:

        label = chat_name

        if len(label) > 30:
            label = label[:30].rstrip() + "..."

        if st.button(
            label,
            key=f"chat_{chat_name}",
            use_container_width=True,
        ):
            select_chat(chat_name)
            st.rerun()

    # ---------------------------------------------------------------
    # LLM Configuration
    # ---------------------------------------------------------------

    with st.expander("LLM Configuration", expanded=False):

        current_provider = st.session_state.llm_config.get(
            "provider",
            "Default Groq",
        )

        provider = st.radio(
            "LLM Provider",
            options=[
                "Default Groq",
                "Custom LLM",
            ],
            index=(
                0
                if current_provider == "Default Groq"
                else 1
            ),
            key="llm_provider",
        )

        # -----------------------------------------------------------
        # DEFAULT GROQ
        # -----------------------------------------------------------
        # Keep the active LLM configuration synced with the selected provider.
        if provider != st.session_state.llm_config.get("provider"):
            if provider == "Default Groq":
                st.session_state.llm_config = {
                    "provider": "Default Groq",
                    "api_url": "",
                    "api_key": "",
                    "model": "",
                }
            else:
                st.session_state.llm_config["provider"] = "Custom LLM"
        if provider == "Default Groq":

            st.caption(
                "Use the application's default Groq LLM."
            )

            if st.button(
                "Use Default Groq",
                use_container_width=True,
                key="use_default_groq",
            ):

                st.session_state.llm_config = {
                    "provider": "Default Groq",
                    "api_url": "",
                    "api_key": "",
                    "model": "",
                }

                st.session_state.llm_message = (
                    "Default Groq is active."
                )

                st.rerun()

        # -----------------------------------------------------------
        # CUSTOM LLM
        # -----------------------------------------------------------

        else:

            st.caption(
                "Connect your own OpenAI-compatible LLM."
            )

            api_url = st.text_input(
                "API URL",
                value=st.session_state.llm_config.get(
                    "api_url",
                    "",
                ),
                placeholder="https://your-provider.com/v1",
                key="custom_llm_api_url",
            )

            api_key = st.text_input(
                "API Key",
                value=st.session_state.llm_config.get(
                    "api_key",
                    "",
                ),
                type="password",
                placeholder="Enter your API key",
                key="custom_llm_api_key",
            )

            model = st.text_input(
                "Model",
                value=st.session_state.llm_config.get(
                    "model",
                    "",
                ),
                placeholder="your-model-name",
                key="custom_llm_model",
            )

            if st.button(
                "Save Custom LLM",
                use_container_width=True,
                key="save_custom_llm",
            ):

                if not api_url.strip():
                    st.error("API URL is required.")

                elif not api_key.strip():
                    st.error("API Key is required.")

                elif not model.strip():
                    st.error("Model is required.")

                else:

                    st.session_state.llm_config = {
                        "provider": "Custom LLM",
                        "api_url": api_url.strip(),
                        "api_key": api_key.strip(),
                        "model": model.strip(),
                    }

                    st.session_state.llm_message = (
                        "Custom LLM is active. Groq is disabled."
                    )

                    st.rerun()

    # ---------------------------------------------------------------
    # LLM SUCCESS MESSAGE
    # ---------------------------------------------------------------

    if st.session_state.llm_message:

        st.success(
            st.session_state.llm_message
        )

        st.session_state.llm_message = None

    # ---------------------------------------------------------------
    # MCP Debug
    # ---------------------------------------------------------------

    with st.expander("MCP Debug", expanded=False):

        debug = st.session_state.last_debug

        if not debug:

            st.caption(
                "No MCP request has been captured yet."
            )

        else:

            if isinstance(debug, list):
                latest_debug = (
                    debug[-1]
                    if debug
                    else {}
                )
            else:
                latest_debug = debug

            status = latest_debug.get(
                "status",
                "unknown",
            )

            tool = latest_debug.get(
                "tool"
            ) or "No tool"

            model_name = latest_debug.get(
                "model"
            ) or st.session_state.llm_config.get(
                "model"
            ) or (
                "openai/gpt-oss-120b"
                if st.session_state.llm_config.get(
                    "provider"
                ) == "Default Groq"
                else "Unknown"
            )

            arguments = latest_debug.get(
                "arguments"
            ) or {}

            duration = latest_debug.get(
                "duration_ms"
            )

            error = latest_debug.get(
                "error"
            )

            result_received = latest_debug.get(
                "result_received"
            )

            st.markdown(
                f"**Tool**  \n`{tool}`"
            )

            st.markdown(
                f"**Status**  \n`{status}`"
            )

            st.markdown(
                f"**Model**  \n`{model_name}`"
            )

            if duration is not None:

                st.markdown(
                    f"**Duration**  \n`{duration} ms`"
                )

            if result_received is not None:

                result_label = (
                    "received"
                    if result_received
                    else "not received"
                )

                st.markdown(
                    f"**Result**  \n`{result_label}`"
                )

            st.markdown("**Arguments**")

            st.json(arguments)

            if error:

                st.markdown("**Error**")

                st.code(
                    str(error)
                )

    # ---------------------------------------------------------------
    # System Information
    # ---------------------------------------------------------------

    active_llm = st.session_state.llm_config.get(
        "provider",
        "Default Groq",
    )

    active_model = (
        st.session_state.llm_config.get("model")
        or "openai/gpt-oss-120b"
    )

    render_html(
        f"""
        <div class="system-info">
            <div class="section-label">System</div>

            <div class="sidebar-note">
                LLM: {active_llm}<br>
                Model: {active_model}<br>
                Tool layer: MCP<br>
                Data source: PSX API
            </div>
        </div>
        """
    )


# -------------------------------------------------------------------
# CURRENT CHAT
# -------------------------------------------------------------------

current_chat = st.session_state.active_chat

messages = st.session_state.chats.get(
    current_chat,
    [],
)


# -------------------------------------------------------------------
# PAGE HEADER
# -------------------------------------------------------------------

render_html(
    """
    <div class="page-header">
        <h1>Pakistan Stock Exchange Intelligence</h1>

        <p>
            Ask about symbols, industries, stock rankings,
            percentage change, or trading volume.
        </p>

        <div class="status">
            <span class="status-dot"></span>
            MCP connection available on demand
        </div>
    </div>
    """
)


# -------------------------------------------------------------------
# EMPTY STATE
# -------------------------------------------------------------------

if not messages:

    st.markdown(
        "### Start with a market query"
    )

    render_html(
        '<div class="suggestion">'
        'Examples: “List industries”, '
        '“Show top 10 stocks by volume”, '
        '“Show top gainers in cement”, '
        'or “List PSX symbols”.'
        '</div>'
    )


# -------------------------------------------------------------------
# RENDER CONVERSATION
# -------------------------------------------------------------------

for message in messages:

    role = message.get("role")

    content = message.get(
        "content",
        "",
    )

    if role not in {
        "user",
        "assistant",
    }:
        continue

    with st.chat_message(role):
        st.markdown(content)


# -------------------------------------------------------------------
# CHAT INPUT
# -------------------------------------------------------------------

custom_llm_selected = (
    st.session_state.get("llm_provider", "Default Groq")
    == "Custom LLM"
)

custom_llm_ready = (
    not custom_llm_selected
    or all(
        str(st.session_state.llm_config.get(field, "")).strip()
        for field in ("api_url", "api_key", "model")
    )
)

  
question = st.chat_input(
    "Ask about PSX stocks, industries, change, or volume..."
)
 
if not custom_llm_ready:
    st.markdown(
        """
        <style>
        div[data-testid="stChatInput"] {
            position: relative !important;
        }

        div[data-testid="stChatInput"]::after {
            content: "";
            position: absolute;
            inset: 0;
            z-index: 9999;
            cursor: not-allowed;
            background: transparent;
        }

        div[data-testid="stChatInput"]::before {
            content: "Please configure your Custom LLM first.";
            position: absolute;
            bottom: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background: #222;
            color: white;
            padding: 7px 12px;
            border-radius: 6px;
            font-size: 13px;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            z-index: 10000;
            transition: opacity 0.15s ease;
        }

        div[data-testid="stChatInput"]:hover::before {
            opacity: 1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Do not process chat input
    question = None


# -------------------------------------------------------------------
# PROCESS REQUEST
# -------------------------------------------------------------------

if question:

    previous_messages = list(messages)

    with st.chat_message("user"):
        st.markdown(question)

    answer = (
        "I could not generate a response."
    )

    with st.chat_message("assistant"):

        with st.spinner(
            "Retrieving PSX data..."
        ):

            try:

                result = ask_chatbot(
                    question=question,
                    history=previous_messages,
                    llm_config=st.session_state.llm_config,
                )

                if isinstance(result, dict):

                    answer = result.get(
                        "answer",
                        "I could not generate a response.",
                    )

                    st.session_state.last_debug = (
                        result.get("debug")
                    )

                else:

                    answer = str(result)

                    st.session_state.last_debug = None

                st.markdown(answer)

            except Exception as exc:

                answer = (
                    "The request could not be completed. "
                    "Please check your LLM configuration "
                    "and try again."
                )

                st.session_state.last_debug = {
                    "status": "error",
                    "tool": None,
                    "model": st.session_state.llm_config.get(
                        "model"
                    ) or "Unknown",
                    "arguments": {},
                    "error": str(exc),
                }

                st.error(answer)


    # ---------------------------------------------------------------
    # Rename initial chat
    # ---------------------------------------------------------------

    if not messages:

        new_title = generate_chat_title(
            question
        )

        if new_title != current_chat:

            original_messages = (
                st.session_state.chats.pop(
                    current_chat,
                    [],
                )
            )

            final_title = new_title

            counter = 1

            while final_title in st.session_state.chats:

                final_title = (
                    f"{new_title} {counter}"
                )

                counter += 1

            st.session_state.chats[
                final_title
            ] = original_messages

            st.session_state.active_chat = (
                final_title
            )

            current_chat = final_title


    # ---------------------------------------------------------------
    # Save user message
    # ---------------------------------------------------------------

    st.session_state.chats[
        current_chat
    ].append(
        {
            "role": "user",
            "content": question,
        }
    )


    # ---------------------------------------------------------------
    # Save assistant response
    # ---------------------------------------------------------------

    st.session_state.chats[
        current_chat
    ].append(
        {
            "role": "assistant",
            "content": answer,
        }
    )


    st.rerun()


# -------------------------------------------------------------------
# FOOTER
# -------------------------------------------------------------------

render_html(
    '<div class="footer-note">'
    'Market information is retrieved from connected PSX data tools. '
    'This application is not financial advice.'
    '</div>'
)

