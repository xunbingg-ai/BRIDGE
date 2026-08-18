"""DeepSeek (OpenAI-compatible) async client factory.

The API key is read from settings (DEEPSEEK_API_KEY env var / backend/.env).
Never hardcode credentials here. Never log the key.
"""
from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from app.core.config import settings


class LLMConfigError(RuntimeError):
    """Raised when the LLM is used without a configured API key."""


def build_llm_client(http_client: httpx.Client | None = None) -> AsyncOpenAI:
    if not settings.deepseek_api_key:
        raise LLMConfigError(
            "DEEPSEEK_API_KEY is not set. Copy backend/.env.example to "
            "backend/.env and fill in your key (backend/.env is git-ignored)."
        )
    return AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        http_client=http_client,
    )


def model_name() -> str:
    return settings.deepseek_model
