"""One-shot live check that the DeepSeek API key works.

Usage (WSL, from backend/): uv run python scripts/smoke_llm.py
Prints only the model reply — never the API key.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.llm.client import build_llm_client, model_name  # noqa: E402


async def main() -> int:
    try:
        client = build_llm_client()
        resp = await client.chat.completions.create(
            model=model_name(),
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=16,
        )
    except Exception as exc:  # surface any upstream failure clearly
        print(f"SMOKE FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("SMOKE OK")
    print(resp.choices[0].message.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
