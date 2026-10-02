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
        :root {
            --bg: #0b0f14;
            --sidebar: #10151c;
            --surface: #151b23;
            --surface-2: #1a212b;
            --border: #293340;
            --text: #f5f7fa;
            --muted: #9aa6b2;
            --accent: #ff4d4f;
            --accent-hover: #ff5f61;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        .block-container {
            max-width: 1000px;
            padding-top: 1.5rem;
            padding-bottom: 1.5rem;
        }

        section[data-testid="stSidebar"] {
            width: 260px !important;
            background: var(--sidebar);
            border-right: 1px solid var(--border);
        }

        section[data-testid="stSidebar"] .block-container {
            padding: 1rem 0.9rem;
        }

        .brand {
            padding: 0.2rem 0.1rem 1rem;
        }

        .brand-title {
            color: var(--text);
            font-size: 1.05rem;
            font-weight: 700;
        }

        .brand-subtitle {
            margin-top: 0.2rem;
            color: var(--muted);
            font-size: 0.76rem;
            line-height: 1.4;
        }

        .hero {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }

        .hero h1 {
            color: var(--text);
            margin: 0;
            font-size: 1.35rem;
            font-weight: 700;
        }

        .hero p {
            color: var(--muted);
            margin: 0.35rem 0 0;
            font-size: 0.82rem;
        }

        .status {
            display: inline-block;
            margin-top: 0.65rem;
            padding: 0.25rem 0.5rem;
            border: 1px solid #334155;
            border-radius: 6px;
            background: #111821;
            color: #b8c4d1;
            font-size: 0.7rem;
        }

        .status-dot {
            display: inline-block;
            width: 6px;
            height: 6px;
            margin-right: 0.35rem;
            border-radius: 50%;
            background: #22c55e;
        }

        .section-label {
            color: #d6dce3;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin: 0.3rem 0 0.5rem;
        }

        .sidebar-note {
            color: var(--muted);
            font-size: 0.74rem;
            line-height: 1.55;
        }

        .debug-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.7rem;
            margin-top: 0.5rem;
        }

        .suggestion {
            color: #c7d0da;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.7rem 0.8rem;
            font-size: 0.82rem;
            line-height: 1.5;
        }

        [data-testid="stChatMessage"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 9px;
            padding: 0.15rem 0.7rem;
            margin-bottom: 0.5rem;
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] td,
        [data-testid="stChatMessage"] th {
            color: var(--text) !important;
        }

        [data-testid="stChatMessage"] table {
            width: 100%;
            color: var(--text);
        }

        [data-testid="stChatMessage"] thead tr {
            background: var(--surface-2);
        }

        [data-testid="stChatMessage"] th,
        [data-testid="stChatMessage"] td {
            border-color: var(--border) !important;
        }

        [data-testid="stChatInput"] {
            margin-top: 0.75rem;
        }

        [data-testid="stChatInput"] > div {
            background: #11161d;
            border: 1px solid #3a4654;
            border-radius: 9px;
        }

        [data-testid="stChatInput"] textarea {
            color: var(--text) !important;
            -webkit-text-fill-color: var(--text) !important;
        }

        [data-testid="stChatInput"] textarea::placeholder {
            color: #7f8b98 !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] button {
            background: transparent;
            color: #dce2e8;
            border: 1px solid transparent;
            border-radius: 7px;
        }

        section[data-testid="stSidebar"] button:hover {
            background: #171e27;
            border-color: var(--border);
        }

        section[data-testid="stSidebar"] button[kind="primary"] {
            background: var(--accent);
            color: #ffffff;
            border-color: var(--accent);
        }

        section[data-testid="stSidebar"] button[kind="primary"]:hover {
            background: var(--accent-hover);
            border-color: var(--accent-hover);
        }

        [data-testid="stExpander"] {
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 8px;
        }

        .stMarkdown, .stCaption {
            color: var(--text);
        }

        .footer-note {
            color: #6f7b88;
            text-align: center;
            font-size: 0.67rem;
            margin-top: 1rem;
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
