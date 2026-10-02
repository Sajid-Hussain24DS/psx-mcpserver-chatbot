import os

from openai import AsyncOpenAI


def create_llm_client() -> AsyncOpenAI:

    provider = os.getenv(
        "LLM_PROVIDER",
        "groq",
    ).lower()

    # -----------------------------------------------------
    # GROQ
    # -----------------------------------------------------

    if provider == "groq":

        api_key = os.getenv(
            "GROQ_API_KEY"
        )

        if not api_key:

            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        return AsyncOpenAI(
            api_key=api_key,
            base_url=(
                "https://api.groq.com/openai/v1"
            ),
        )

    # -----------------------------------------------------
    # OPENROUTER
    # -----------------------------------------------------

    if provider == "openrouter":

        api_key = os.getenv(
            "OPENROUTER_API_KEY"
        )

        if not api_key:

            raise RuntimeError(
                "OPENROUTER_API_KEY is not configured."
            )

        return AsyncOpenAI(
            api_key=api_key,
            base_url=(
                "https://openrouter.ai/api/v1"
            ),
        )

    # -----------------------------------------------------
    # DEEPSEEK
    # -----------------------------------------------------

    if provider == "deepseek":

        api_key = os.getenv(
            "DEEPSEEK_API_KEY"
        )

        if not api_key:

            raise RuntimeError(
                "DEEPSEEK_API_KEY is not configured."
            )

        return AsyncOpenAI(
            api_key=api_key,
            base_url=(
                "https://api.deepseek.com"
            ),
        )

    # -----------------------------------------------------
    # CUSTOM
    # -----------------------------------------------------

    if provider == "custom":

        api_key = os.getenv(
            "LLM_API_KEY"
        )

        base_url = os.getenv(
            "LLM_BASE_URL"
        )

        if not api_key:

            raise RuntimeError(
                "LLM_API_KEY is not configured."
            )

        if not base_url:

            raise RuntimeError(
                "LLM_BASE_URL is not configured."
            )

        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    raise RuntimeError(
        f"Unsupported LLM provider: {provider}"
    )