import asyncio

import httpx
import pytest

from app.core.config import Settings
from app.services.llm import client as llm_client


def _fake_completion_body() -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1728000000,
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "OK"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


class _AsyncMockTransport(httpx.AsyncBaseTransport):
    """Async transport backed by a sync handler (httpx has no built-in
    async MockTransport; openai 3.x requires an AsyncClient)."""

    def __init__(self, handler) -> None:
        self._handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def test_client_hits_deepseek_endpoint_with_model(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["payload"] = request.content
        return httpx.Response(200, json=_fake_completion_body())

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(
        llm_client,
        "settings",
        Settings(_env_file=None, deepseek_api_key="sk-test"),
    )

    client = llm_client.build_llm_client(
        http_client=httpx.AsyncClient(transport=_AsyncMockTransport(handler))
    )

    async def _run():
        resp = await client.chat.completions.create(
            model=llm_client.model_name(),
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=16,
        )
        return resp.choices[0].message.content

    assert asyncio.run(_run()) == "OK"
    assert seen["url"].startswith("https://api.deepseek.com")
    assert b"deepseek-v4-flash" in seen["payload"]


def test_build_llm_client_raises_without_key(monkeypatch):
    monkeypatch.setattr(
        llm_client, "settings", Settings(_env_file=None, deepseek_api_key="")
    )
    with pytest.raises(llm_client.LLMConfigError):
        llm_client.build_llm_client()
