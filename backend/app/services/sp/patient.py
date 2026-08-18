"""Standardized Patient dialogue module.

Builds chat messages from prompt templates and the case script, then calls
the LLM client. The SP must never go outside the case script (ADR-0002;
CONTEXT.md SP definition).
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from openai import AsyncOpenAI

from app.services.llm.client import model_name

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def _render_script(case_script: dict) -> str:
    lines = []
    for key, value in case_script.items():
        if isinstance(value, (dict, list)):
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _render_history(history: list[dict]) -> str:
    if not history:
        return "(no questions asked yet)"
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in history)


def build_sp_messages(
    case_script: dict, history: list[dict], message: str, language: str
) -> list[dict]:
    system = load_prompt("sp_system.txt").replace("{{LANGUAGE}}", language)
    user = (
        load_prompt("sp_user.txt")
        .replace("{{SCRIPT}}", _render_script(case_script))
        .replace("{{HISTORY}}", _render_history(history))
        .replace("{{MESSAGE}}", message)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


class SPResponder:
    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    async def respond(
        self, case_script: dict, history: list[dict], message: str, language: str
    ) -> str:
        messages = build_sp_messages(case_script, history, message, language)
        resp = await self._client.chat.completions.create(
            model=model_name(), messages=messages
        )
        return resp.choices[0].message.content or ""

    async def stream_response(
        self, case_script: dict, history: list[dict], message: str, language: str
    ) -> AsyncIterator[str]:
        messages = build_sp_messages(case_script, history, message, language)
        stream = await self._client.chat.completions.create(
            model=model_name(), messages=messages, stream=True
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            if content:
                yield content
