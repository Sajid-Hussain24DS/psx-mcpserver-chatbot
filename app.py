import streamlit as st

from chatbot.chatbot import ask_chatbot


# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="PSX Chatbot",
    page_icon="📈",
    layout="centered",
)


# ---------------------------------------------------------
# Custom UI Styling
# ---------------------------------------------------------

st.markdown(
    """
    <style>

    section[data-testid="stSidebar"] {
        width: 280px !important;
    }

    section[data-testid="stSidebar"] button {
        text-align: left;
        border: none;
        padding: 8px 10px;
    }

    .block-container {
        padding-top: 2rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.title("📈 PSX Chatbot")

st.caption(
    "PSX data powered by MCP + Groq"
)


# ---------------------------------------------------------
# Session State
# ---------------------------------------------------------

if "chats" not in st.session_state:

    st.session_state.chats = {
        "New Chat": []
    }


if "active_chat" not in st.session_state:

    st.session_state.active_chat = "New Chat"


if "last_tool" not in st.session_state:

    st.session_state.last_tool = None


if "last_arguments" not in st.session_state:

    st.session_state.last_arguments = None


# ---------------------------------------------------------
# Generate Chat Title
# ---------------------------------------------------------

def generate_chat_title(question: str) -> str:

    title = question.strip()

    title = " ".join(
        title.split()
    )

    max_length = 42

    if len(title) > max_length:

        title = (
            title[:max_length].rstrip()
            + "..."
        )

    return title


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:

    if st.button(
        "✚  New chat",
        use_container_width=True,
    ):

        new_chat_name = "New Chat"

        if (
            new_chat_name in st.session_state.chats
            and not st.session_state.chats[new_chat_name]
        ):

            st.session_state.active_chat = (
                new_chat_name
            )

        else:

            counter = 1

            while (
                f"New Chat {counter}"
                in st.session_state.chats
            ):

                counter += 1

            new_chat_name = (
                f"New Chat {counter}"
            )

            st.session_state.chats[
                new_chat_name
            ] = []

            st.session_state.active_chat = (
                new_chat_name
            )

        st.session_state.last_tool = None

        st.session_state.last_arguments = None

        st.rerun()


    st.divider()

    st.caption("RECENT CHATS")


    for chat_name in list(
        st.session_state.chats.keys()
    ):

        if st.button(
            chat_name,
            key=f"chat_{chat_name}",
            use_container_width=True,
        ):

            st.session_state.active_chat = (
                chat_name
            )

            st.session_state.last_tool = None

            st.session_state.last_arguments = None

            st.rerun()


    st.divider()


    with st.expander("MCP Debug"):

        if st.session_state.last_tool:

            st.write("**Last Tool**")

            st.code(
                st.session_state.last_tool
            )

            st.write("**Arguments**")

            st.json(
                st.session_state.last_arguments
            )

        else:

            st.info(
                "No MCP tool called yet."
            )


# ---------------------------------------------------------
# Current Chat
# ---------------------------------------------------------

current_chat = st.session_state.active_chat

messages = st.session_state.chats[
    current_chat
]


# ---------------------------------------------------------
# Display Chat History
# ---------------------------------------------------------

for message in messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# ---------------------------------------------------------
# User Input
# ---------------------------------------------------------

question = st.chat_input(
    "Ask about PSX stocks, industries, change or volume..."
)


if question:

    with st.chat_message("user"):

        st.markdown(question)


    previous_messages = messages.copy()


    with st.chat_message("assistant"):

        with st.spinner(
            "Fetching PSX data..."
        ):

            try:

                result = ask_chatbot(
                    question,
                    previous_messages,
                )

                answer = result["answer"]

                st.markdown(answer)

                st.session_state.last_tool = (
                    result["tool"]
                )

                st.session_state.last_arguments = (
                    result["arguments"]
                )

            except Exception as e:

                answer = f"Error: {str(e)}"

                st.error(answer)



    if not messages:

        new_title = generate_chat_title(
            question
        )

        if new_title != current_chat:

            original_messages = (
                st.session_state.chats.pop(
                    current_chat
                )
            )

            st.session_state.chats[
                new_title
            ] = original_messages

            st.session_state.active_chat = (
                new_title
            )

            current_chat = new_title


    # -----------------------------------------------------
    # Save messages
    # -----------------------------------------------------

    st.session_state.chats[
        current_chat
    ].append(
        {
            "role": "user",
            "content": question,
        }
    )


    st.session_state.chats[
        current_chat
    ].append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    st.rerun()