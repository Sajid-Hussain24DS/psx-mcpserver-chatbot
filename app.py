# import streamlit as st

# from chatbot.chatbot import ask_chatbot


# # ---------------------------------------------------------
# # Page Configuration
# # ---------------------------------------------------------

# st.set_page_config(
#     page_title="PSX Chatbot",
#     page_icon="📈",
#     layout="centered",
# )


# # ---------------------------------------------------------
# # Custom UI Styling
# # ---------------------------------------------------------

# st.markdown(
#     """
#     <style>

#     section[data-testid="stSidebar"] {
#         width: 280px !important;
#     }

#     section[data-testid="stSidebar"] button {
#         text-align: left;
#         border: none;
#         padding: 8px 10px;
#     }

#     .block-container {
#         padding-top: 2rem;
#     }

#     </style>
#     """,
#     unsafe_allow_html=True,
# )


# # ---------------------------------------------------------
# # Header
# # ---------------------------------------------------------

# st.title("📈 PSX Chatbot")

# st.caption(
#     "PSX data powered by MCP + Groq"
# )


# # ---------------------------------------------------------
# # Session State
# # ---------------------------------------------------------

# if "chats" not in st.session_state:
#     st.session_state.chats = {
#         "New Chat": []
#     }


# if "active_chat" not in st.session_state:
#     st.session_state.active_chat = "New Chat"


# if "last_tool" not in st.session_state:
#     st.session_state.last_tool = None


# if "last_arguments" not in st.session_state:
#     st.session_state.last_arguments = None


# # ---------------------------------------------------------
# # Generate Chat Title
# # ---------------------------------------------------------

# def generate_chat_title(question: str) -> str:

#     title = question.strip()

#     title = " ".join(
#         title.split()
#     )

#     max_length = 42

#     if len(title) > max_length:
#         title = (
#             title[:max_length].rstrip()
#             + "..."
#         )

#     return title or "New Chat"


# # ---------------------------------------------------------
# # Create Unique Chat Name
# # ---------------------------------------------------------

# def create_new_chat_name() -> str:

#     if (
#         "New Chat" not in st.session_state.chats
#         or not st.session_state.chats["New Chat"]
#     ):
#         return "New Chat"

#     counter = 1

#     while (
#         f"New Chat {counter}"
#         in st.session_state.chats
#     ):
#         counter += 1

#     return f"New Chat {counter}"


# # ---------------------------------------------------------
# # Sidebar
# # ---------------------------------------------------------

# with st.sidebar:

#     if st.button(
#         "✚  New chat",
#         use_container_width=True,
#     ):

#         new_chat_name = create_new_chat_name()

#         st.session_state.chats[
#             new_chat_name
#         ] = []

#         st.session_state.active_chat = (
#             new_chat_name
#         )

#         st.session_state.last_tool = None
#         st.session_state.last_arguments = None

#         st.rerun()


#     st.divider()

#     st.caption("RECENT CHATS")


#     for chat_name in list(
#         st.session_state.chats.keys()
#     ):

#         if st.button(
#             chat_name,
#             key=f"chat_{chat_name}",
#             use_container_width=True,
#         ):

#             st.session_state.active_chat = (
#                 chat_name
#             )

#             st.session_state.last_tool = None
#             st.session_state.last_arguments = None

#             st.rerun()


#     st.divider()


#     # -----------------------------------------------------
#     # MCP Debug
#     # -----------------------------------------------------

#     with st.expander("MCP Debug"):

#         if st.session_state.last_tool:

#             st.write("**Last Tool**")

#             st.code(
#                 st.session_state.last_tool
#             )

#             st.write("**Arguments**")

#             st.json(
#                 st.session_state.last_arguments
#             )

#         else:

#             st.info(
#                 "No MCP tool called yet."
#             )


# # ---------------------------------------------------------
# # Current Chat
# # ---------------------------------------------------------

# current_chat = st.session_state.active_chat

# messages = st.session_state.chats.get(
#     current_chat,
#     [],
# )


# # ---------------------------------------------------------
# # Display Chat History
# # ---------------------------------------------------------

# for message in messages:

#     with st.chat_message(
#         message["role"]
#     ):

#         st.markdown(
#             message["content"]
#         )


# # ---------------------------------------------------------
# # User Input
# # ---------------------------------------------------------

# question = st.chat_input(
#     "Ask about PSX stocks, industries, change or volume..."
# )


# # ---------------------------------------------------------
# # Process User Question
# # ---------------------------------------------------------

# if question:

#     # ---------------------------------------------
#     # Display User Message Immediately
#     # ---------------------------------------------

#     with st.chat_message("user"):

#         st.markdown(question)


#     # ---------------------------------------------
#     # Copy Previous Conversation
#     # ---------------------------------------------

#     previous_messages = messages.copy()


#     # ---------------------------------------------
#     # Call Chatbot
#     # ---------------------------------------------

#     with st.chat_message("assistant"):

#         with st.spinner(
#             "Fetching PSX data..."
#         ):

#             try:

#                 result = ask_chatbot(
#                     question,
#                     previous_messages,
#                 )


#                 # ---------------------------------
#                 # Validate Chatbot Response
#                 # ---------------------------------

#                 if isinstance(result, dict):

#                     answer = result.get(
#                         "answer",
#                         "I couldn't generate a response.",
#                     )

#                     tool = result.get(
#                         "tool"
#                     )

#                     arguments = result.get(
#                         "arguments"
#                     )

#                 else:

#                     answer = str(result)

#                     tool = None

#                     arguments = None


#                 # ---------------------------------
#                 # Display Answer
#                 # ---------------------------------

#                 st.markdown(answer)


#                 # ---------------------------------
#                 # Save MCP Debug Information
#                 # ---------------------------------

#                 st.session_state.last_tool = tool

#                 st.session_state.last_arguments = (
#                     arguments
#                 )


#             except Exception as e:

#                 answer = (
#                     f"Error: {str(e)}"
#                 )

#                 st.error(answer)

#                 st.session_state.last_tool = None

#                 st.session_state.last_arguments = None


#     # -------------------------------------------------
#     # Rename First Chat
#     # -------------------------------------------------

#     if not messages:

#         new_title = generate_chat_title(
#             question
#         )

#         if new_title != current_chat:

#             original_messages = (
#                 st.session_state.chats.pop(
#                     current_chat,
#                     [],
#                 )
#             )

#             # Prevent accidental duplicate title
#             final_title = new_title

#             counter = 1

#             while (
#                 final_title in st.session_state.chats
#             ):

#                 final_title = (
#                     f"{new_title} {counter}"
#                 )

#                 counter += 1


#             st.session_state.chats[
#                 final_title
#             ] = original_messages

#             st.session_state.active_chat = (
#                 final_title
#             )

#             current_chat = final_title


#     # -------------------------------------------------
#     # Save User Message
#     # -------------------------------------------------

#     st.session_state.chats[
#         current_chat
#     ].append(
#         {
#             "role": "user",
#             "content": question,
#         }
#     )


#     # -------------------------------------------------
#     # Save Assistant Message
#     # -------------------------------------------------

#     st.session_state.chats[
#         current_chat
#     ].append(
#         {
#             "role": "assistant",
#             "content": answer,
#         }
#     )


#     # -------------------------------------------------
#     # Refresh UI
#     # -------------------------------------------------

#     st.rerun()
import streamlit as st

from chatbot.chatbot import ask_chatbot


st.set_page_config(
    page_title="PSX Intelligence",
    page_icon="P",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------------------------------------------------
# UI
# -------------------------------------------------------------------

st.markdown(
    """
    <style>
        /* =========================================================
           PSX INTELLIGENCE — MONOCHROME BLACK UI
           ========================================================= */

        :root {
            --bg: #000000;
            --sidebar: #050505;
            --surface: #0b0b0b;
            --surface-2: #111111;
            --surface-3: #151515;
            --border: #242424;
            --border-light: #303030;

            --text: #f2f2f2;
            --text-soft: #d4d4d4;
            --muted: #8a8a8a;
            --muted-dark: #666666;

            --hover: #171717;
            --active: #1c1c1c;
            --input: #0d0d0d;
        }

        /* ---------------------------------------------------------
           GLOBAL
           --------------------------------------------------------- */

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        html,
        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main {
            background: var(--bg) !important;
        }

        .block-container {
            max-width: 980px;
            padding-top: 1.8rem;
            padding-bottom: 2rem;
        }

        /* Remove Streamlit default decorative spacing */
        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        /* ---------------------------------------------------------
           SIDEBAR
           --------------------------------------------------------- */

        section[data-testid="stSidebar"] {
            width: 260px !important;
            background: var(--sidebar) !important;
            border-right: 1px solid var(--border);
        }

        section[data-testid="stSidebar"] > div {
            background: var(--sidebar) !important;
        }

        section[data-testid="stSidebar"] .block-container {
            padding: 1.2rem 0.9rem;
        }

        /* ---------------------------------------------------------
           BRAND
           --------------------------------------------------------- */

        .brand {
            padding: 0.15rem 0.15rem 1.2rem;
        }

        .brand-title {
            color: #ffffff;
            font-size: 1.02rem;
            font-weight: 700;
            letter-spacing: -0.01em;
        }

        .brand-subtitle {
            margin-top: 0.28rem;
            color: var(--muted);
            font-size: 0.74rem;
            line-height: 1.45;
        }

        /* ---------------------------------------------------------
           HERO
           --------------------------------------------------------- */

        .hero {
            background: linear-gradient(
                180deg,
                #0c0c0c 0%,
                #090909 100%
            );
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem 1.3rem;
            margin-bottom: 1.15rem;
        }

        .hero h1 {
            color: #ffffff;
            margin: 0;
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: -0.025em;
        }

        .hero p {
            color: var(--muted);
            margin: 0.4rem 0 0;
            font-size: 0.8rem;
            line-height: 1.5;
        }

        /* ---------------------------------------------------------
           STATUS
           --------------------------------------------------------- */

        .status {
            display: inline-flex;
            align-items: center;
            margin-top: 0.75rem;
            padding: 0.28rem 0.55rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: #080808;
            color: #999999;
            font-size: 0.68rem;
        }

        .status-dot {
            display: inline-block;
            width: 5px;
            height: 5px;
            margin-right: 0.38rem;
            border-radius: 50%;
            background: #8a8a8a;
        }

        /* ---------------------------------------------------------
           SECTION LABELS
           --------------------------------------------------------- */

        .section-label {
            color: #bdbdbd;
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin: 0.35rem 0 0.55rem;
        }

        .sidebar-note {
            color: var(--muted);
            font-size: 0.72rem;
            line-height: 1.6;
        }

        /* ---------------------------------------------------------
           SIDEBAR BUTTONS
           --------------------------------------------------------- */

        section[data-testid="stSidebar"] button {
            background: transparent !important;
            color: #cfcfcf !important;
            border: 1px solid transparent !important;
            border-radius: 7px !important;
            box-shadow: none !important;
            transition: background 0.15s ease,
                        border-color 0.15s ease;
        }

        section[data-testid="stSidebar"] button:hover {
            background: var(--hover) !important;
            border-color: var(--border) !important;
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] button[kind="primary"] {
            background: #151515 !important;
            color: #ffffff !important;
            border: 1px solid var(--border-light) !important;
        }

        section[data-testid="stSidebar"] button[kind="primary"]:hover {
            background: #1b1b1b !important;
            border-color: #3a3a3a !important;
        }

        /* ---------------------------------------------------------
           DIVIDERS
           --------------------------------------------------------- */

        hr {
            border-color: var(--border) !important;
            opacity: 1 !important;
        }

        /* ---------------------------------------------------------
           DEBUG CARD
           --------------------------------------------------------- */

        .debug-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.75rem;
            margin-top: 0.55rem;
        }

        /* ---------------------------------------------------------
           SUGGESTION CARD
           --------------------------------------------------------- */

        .suggestion {
            color: var(--text-soft);
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 9px;
            padding: 0.75rem 0.85rem;
            font-size: 0.8rem;
            line-height: 1.55;
        }

        /* ---------------------------------------------------------
           CHAT MESSAGES
           --------------------------------------------------------- */

        [data-testid="stChatMessage"] {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            padding: 0.2rem 0.75rem !important;
            margin-bottom: 0.55rem !important;
        }

        [data-testid="stChatMessage"]:hover {
            border-color: #2d2d2d !important;
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] td,
        [data-testid="stChatMessage"] th {
            color: var(--text) !important;
        }

        [data-testid="stChatMessage"] strong {
            color: #ffffff !important;
        }

        /* ---------------------------------------------------------
           CHAT TABLES
           --------------------------------------------------------- */

        [data-testid="stChatMessage"] table {
            width: 100%;
            border-collapse: collapse;
            color: var(--text) !important;
            background: var(--surface) !important;
        }

        [data-testid="stChatMessage"] thead tr {
            background: var(--surface-2) !important;
        }

        [data-testid="stChatMessage"] th,
        [data-testid="stChatMessage"] td {
            border-color: var(--border) !important;
            color: var(--text) !important;
        }

        [data-testid="stChatMessage"] th {
            color: #d6d6d6 !important;
            font-weight: 600;
        }

        [data-testid="stChatMessage"] tr:nth-child(even) {
            background: #0d0d0d !important;
        }

        [data-testid="stChatMessage"] tr:hover {
            background: #141414 !important;
        }

        /* ---------------------------------------------------------
           CHAT INPUT
           --------------------------------------------------------- */

        [data-testid="stChatInput"] {
            margin-top: 0.9rem;
        }

        [data-testid="stChatInput"] > div {
            background: var(--input) !important;
            border: 1px solid #2a2a2a !important;
            border-radius: 10px !important;
            box-shadow: none !important;
        }

        [data-testid="stChatInput"] > div:focus-within {
            border-color: #444444 !important;
            box-shadow: none !important;
        }

        [data-testid="stChatInput"] textarea {
            color: #f5f5f5 !important;
            -webkit-text-fill-color: #f5f5f5 !important;
            caret-color: #ffffff !important;
        }

        [data-testid="stChatInput"] textarea::placeholder {
            color: #707070 !important;
            opacity: 1 !important;
        }

        /* ---------------------------------------------------------
           EXPANDER
           --------------------------------------------------------- */

        [data-testid="stExpander"] {
            background: transparent !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
        }

        [data-testid="stExpander"] summary {
            color: #cfcfcf !important;
        }

        [data-testid="stExpander"] summary:hover {
            color: #ffffff !important;
        }

        /* ---------------------------------------------------------
           STREAMLIT TEXT
           --------------------------------------------------------- */

        .stMarkdown,
        .stCaption {
            color: var(--text);
        }

        .stCaption {
            color: var(--muted) !important;
        }

        /* ---------------------------------------------------------
           GENERAL INPUT / SELECT ELEMENTS
           --------------------------------------------------------- */

        input,
        textarea,
        select {
            background-color: var(--input) !important;
            color: var(--text) !important;
            border-color: var(--border) !important;
        }

        /* ---------------------------------------------------------
           SCROLLBAR
           --------------------------------------------------------- */

        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #000000;
        }

        ::-webkit-scrollbar-thumb {
            background: #252525;
            border-radius: 10px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #383838;
        }

        /* ---------------------------------------------------------
           FOOTER
           --------------------------------------------------------- */

        .footer-note {
            color: #5f5f5f;
            text-align: center;
            font-size: 0.65rem;
            margin-top: 1.15rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Session state
# -------------------------------------------------------------------

if "chats" not in st.session_state:
    st.session_state.chats = {"New Chat": []}

if "active_chat" not in st.session_state:
    st.session_state.active_chat = "New Chat"

if "last_debug" not in st.session_state:
    st.session_state.last_debug = None


def generate_chat_title(question: str) -> str:
    title = " ".join(question.strip().split())
    if len(title) > 42:
        title = title[:42].rstrip() + "..."
    return title or "New Chat"


def create_new_chat_name() -> str:
    if "New Chat" not in st.session_state.chats or not st.session_state.chats["New Chat"]:
        return "New Chat"

    counter = 1
    while f"New Chat {counter}" in st.session_state.chats:
        counter += 1

    return f"New Chat {counter}"


def select_chat(chat_name: str) -> None:
    st.session_state.active_chat = chat_name
    st.session_state.last_debug = None


# -------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <div class="brand-title">PSX Intelligence</div>
            <div class="brand-subtitle">MCP-powered Pakistan Stock Exchange assistant</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    st.markdown('<div class="section-label">Recent chats</div>', unsafe_allow_html=True)

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

    st.divider()

    with st.expander("MCP Debug", expanded=False):
        debug = st.session_state.last_debug

        if not debug:
            st.caption("No MCP request has been captured yet.")
        else:
            status = debug.get("status", "unknown")
            tool = debug.get("tool") or "No tool"
            arguments = debug.get("arguments") or {}
            duration = debug.get("duration_ms")
            error = debug.get("error")

            st.markdown(f"**Tool**  \n`{tool}`")
            st.markdown(f"**Status**  \n`{status}`")

            if duration is not None:
                st.markdown(f"**Duration**  \n`{duration} ms`")

            result_received = debug.get("result_received")
            if result_received is not None:
                result_label = "received" if result_received else "not received"
                st.markdown(f"**Result**  \n`{result_label}`")

            st.markdown("**Arguments**")
            st.json(arguments)

            if error:
                st.markdown("**Error**")
                st.code(str(error))

    st.markdown(
        """
        <div class="debug-card">
            <div class="section-label">System</div>
            <div class="sidebar-note">
                LLM: Groq<br>
                Tool layer: MCP<br>
                Data source: PSX API
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------
# Main content
# -------------------------------------------------------------------

current_chat = st.session_state.active_chat
messages = st.session_state.chats.get(current_chat, [])

st.markdown(
    """
    <div class="hero">
        <h1>Pakistan Stock Exchange Intelligence</h1>
        <p>Ask about symbols, industries, stock rankings, percentage change, or trading volume.</p>
        <div class="status">
            <span class="status-dot"></span>
            MCP connection available on demand
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


if not messages:
    st.markdown("### Start with a market query")
    st.markdown(
        '<div class="suggestion">Examples: “List industries”, “Show top 10 stocks by volume”, '
        '“Show top gainers in cement”, or “List PSX symbols”.</div>',
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------
# Render conversation
# -------------------------------------------------------------------

for message in messages:
    role = message.get("role")
    content = message.get("content", "")

    if role not in {"user", "assistant"}:
        continue

    with st.chat_message(role):
        st.markdown(content)


question = st.chat_input(
    "Ask about PSX stocks, industries, change, or volume..."
)


# -------------------------------------------------------------------
# Process request
# -------------------------------------------------------------------

if question:
    previous_messages = list(messages)

    with st.chat_message("user"):
        st.markdown(question)

    answer = "I could not generate a response."

    with st.chat_message("assistant"):
        with st.spinner("Retrieving PSX data..."):
            try:
                result = ask_chatbot(
                    user_message=question,
                    history=previous_messages,
                )

                if isinstance(result, dict):
                    answer = result.get(
                        "answer",
                        "I could not generate a response.",
                    )
                    st.session_state.last_debug = result.get("debug")
                else:
                    answer = str(result)
                    st.session_state.last_debug = None

                st.markdown(answer)

            except Exception as exc:
                answer = "The request could not be completed. Please try again."
                st.session_state.last_debug = {
                    "status": "error",
                    "tool": None,
                    "arguments": {},
                    "error": str(exc),
                }
                st.error(answer)

    # Rename the initial chat after the first user request.
    if not messages:
        new_title = generate_chat_title(question)

        if new_title != current_chat:
            original_messages = st.session_state.chats.pop(
                current_chat,
                [],
            )

            final_title = new_title
            counter = 1

            while final_title in st.session_state.chats:
                final_title = f"{new_title} {counter}"
                counter += 1

            st.session_state.chats[final_title] = original_messages
            st.session_state.active_chat = final_title
            current_chat = final_title

    st.session_state.chats[current_chat].append(
        {
            "role": "user",
            "content": question,
        }
    )

    st.session_state.chats[current_chat].append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    st.rerun()


st.markdown(
    '<div class="footer-note">Market information is retrieved from connected PSX data tools. '
    'This application is not financial advice.</div>',
    unsafe_allow_html=True,
)
