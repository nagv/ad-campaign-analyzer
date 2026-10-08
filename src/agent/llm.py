"""OpenRouter chat model, same setup as the LangChain fundamentals notebook."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "google/gemini-2.5-flash"


def has_api_key() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def get_llm(model: str | None = None, temperature: float = 0, max_tokens: int = 1000):
    # max_tokens matters: without it OpenRouter reserves the model's full output
    # budget and can return 402 on low-credit accounts.
    from langchain.chat_models import init_chat_model

    return init_chat_model(
        model=model or os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        model_provider="openai",
        base_url=OPENROUTER_BASE_URL,
        api_key=os.environ["OPENROUTER_API_KEY"],
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=3,
    )
