import os

from openai import AsyncOpenAI


def create_llm_client(
    api_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> AsyncOpenAI:

    # -----------------------------------------------------
    # CUSTOM LLM FROM UI
    # -----------------------------------------------------

    if api_url and api_key:

        return AsyncOpenAI(
            api_key=api_key,
            base_url=api_url.rstrip("/"),
        )

    # -----------------------------------------------------
    # DEFAULT GROQ
    # -----------------------------------------------------

    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    return AsyncOpenAI(
        api_key=groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )