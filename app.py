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

    return title or "New Chat"


# ---------------------------------------------------------
# Create Unique Chat Name
# ---------------------------------------------------------

def create_new_chat_name() -> str:

    if (
        "New Chat" not in st.session_state.chats
        or not st.session_state.chats["New Chat"]
    ):
        return "New Chat"

    counter = 1

    while (
        f"New Chat {counter}"
        in st.session_state.chats
    ):
        counter += 1

    return f"New Chat {counter}"


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:

    if st.button(
        "✚  New chat",
        use_container_width=True,
    ):

        new_chat_name = create_new_chat_name()

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


    # -----------------------------------------------------
    # MCP Debug
    # -----------------------------------------------------

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

messages = st.session_state.chats.get(
    current_chat,
    [],
)


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


# ---------------------------------------------------------
# Process User Question
# ---------------------------------------------------------

if question:

    # ---------------------------------------------
    # Display User Message Immediately
    # ---------------------------------------------

    with st.chat_message("user"):

        st.markdown(question)


    # ---------------------------------------------
    # Copy Previous Conversation
    # ---------------------------------------------

    previous_messages = messages.copy()


    # ---------------------------------------------
    # Call Chatbot
    # ---------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "Fetching PSX data..."
        ):

            try:

                result = ask_chatbot(
                    question,
                    previous_messages,
                )


                # ---------------------------------
                # Validate Chatbot Response
                # ---------------------------------

                if isinstance(result, dict):

                    answer = result.get(
                        "answer",
                        "I couldn't generate a response.",
                    )

                    tool = result.get(
                        "tool"
                    )

                    arguments = result.get(
                        "arguments"
                    )

                else:

                    answer = str(result)

                    tool = None

                    arguments = None


                # ---------------------------------
                # Display Answer
                # ---------------------------------

                st.markdown(answer)


                # ---------------------------------
                # Save MCP Debug Information
                # ---------------------------------

                st.session_state.last_tool = tool

                st.session_state.last_arguments = (
                    arguments
                )


            except Exception as e:

                answer = (
                    f"Error: {str(e)}"
                )

                st.error(answer)

                st.session_state.last_tool = None

                st.session_state.last_arguments = None


    # -------------------------------------------------
    # Rename First Chat
    # -------------------------------------------------

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

            # Prevent accidental duplicate title
            final_title = new_title

            counter = 1

            while (
                final_title in st.session_state.chats
            ):

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


    # -------------------------------------------------
    # Save User Message
    # -------------------------------------------------

    st.session_state.chats[
        current_chat
    ].append(
        {
            "role": "user",
            "content": question,
        }
    )


    # -------------------------------------------------
    # Save Assistant Message
    # -------------------------------------------------

    st.session_state.chats[
        current_chat
    ].append(
        {
            "role": "assistant",
            "content": answer,
        }
    )


    # -------------------------------------------------
    # Refresh UI
    # -------------------------------------------------

    st.rerun()