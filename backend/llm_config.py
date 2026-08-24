from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

from database import get_db, now_iso


def _parse_headers(value) -> dict[str, str]:
    if not value:
        return {}
    if isinstance(value, dict):
        return {str(key): str(val) for key, val in value.items() if val not in (None, "")}
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return {str(key): str(val) for key, val in parsed.items() if val not in (None, "")}
    except (TypeError, json.JSONDecodeError):
        return {}
    return {}


def _mask_api_key(key: str | None) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"


def config_to_dict(row, include_secret: bool = False) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": row["id"],
        "name": row["name"],
        "baseUrl": row["base_url"],
        "apiKey": row["api_key"] if include_secret else _mask_api_key(row["api_key"]),
        "hasApiKey": bool(row["api_key"]),
        "headers": _parse_headers(row["headers_json"]),
        "model": row["model"],
        "backupModel": row["backup_model"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def get_active_llm_config() -> dict[str, Any] | None:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM llm_configs WHERE id = 1").fetchone()
        if row is None:
            return None
        return config_to_dict(row, include_secret=True)
    finally:
        conn.close()


def get_public_llm_config() -> dict[str, Any]:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM llm_configs WHERE id = 1").fetchone()
        return config_to_dict(row, include_secret=False)
    finally:
        conn.close()


def build_headers(config: dict[str, Any]) -> dict[str, str]:
    headers = {str(key): str(value) for key, value in (config.get("headers") or {}).items()}
    api_key = config.get("apiKey") or config.get("api_key")
    if api_key and not any(key.lower() == "authorization" for key in headers):
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def fetch_model_list(base_url: str, api_key: str, headers: dict[str, Any]) -> tuple[list[str], str | None]:
    config = {"baseUrl": base_url, "apiKey": api_key, "headers": headers}
    url = f"{base_url.rstrip('/')}/models"
    try:
        response = requests.get(url, headers=build_headers(config), timeout=30)
        if response.status_code >= 400:
            return [], f"获取模型列表失败：HTTP {response.status_code} {response.text[:200]}"
        payload = response.json()
        return extract_model_list(payload), None
    except requests.RequestException as exc:
        return [], f"请求失败：{exc}"


def extract_model_list(payload: Any) -> list[str]:
    models: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, str):
                models.append(item)
            elif isinstance(item, dict):
                name = item.get("id") or item.get("name")
                if name:
                    models.append(str(name))
        return models

    if isinstance(payload, dict):
        data = payload.get("data") or payload.get("models") or []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    models.append(item)
                elif isinstance(item, dict):
                    name = item.get("id") or item.get("name")
                    if name:
                        models.append(str(name))

    return list(dict.fromkeys(models))


def test_model_speed(base_url: str, api_key: str, headers: dict[str, Any], model: str) -> tuple[dict[str, Any], str | None]:
    config = {"baseUrl": base_url, "apiKey": api_key, "headers": headers}
    url = f"{base_url.rstrip('/')}/chat/completions"
    start = time.perf_counter()
    try:
        response = requests.post(
            url,
            headers=build_headers(config),
            json={
                "model": model,
                "messages": [{"role": "user", "content": "请只回复：OK"}],
                "max_tokens": 8,
            },
            timeout=60,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        if response.status_code >= 400:
            return {"model": model, "latencyMs": latency_ms}, f"HTTP {response.status_code} {response.text[:200]}"
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return {"model": model, "latencyMs": latency_ms, "content": content}, None
    except requests.RequestException as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"model": model, "latencyMs": latency_ms}, f"请求失败：{exc}"


def save_llm_config(data: dict[str, Any]) -> dict[str, Any]:
    conn = get_db()
    try:
        existing = conn.execute("SELECT api_key FROM llm_configs WHERE id = 1").fetchone()
        base_url = (data.get("baseUrl") or "").strip()
        if not base_url:
            raise ValueError("baseUrl 不能为空")

        headers = data.get("headers")
        if isinstance(headers, str):
            headers = _parse_headers(headers)
        elif not isinstance(headers, dict):
            headers = {}
        headers_json = json.dumps(headers, ensure_ascii=False)

        api_key = (data.get("apiKey") or "").strip()
        if not api_key and existing is not None:
            api_key = existing["api_key"] or ""

        name = (data.get("name") or "").strip() or "默认模型配置"
        model = (data.get("model") or "").strip() or None
        backup_model = (data.get("backupModel") or data.get("backup_model") or "").strip() or None

        conn.execute(
            """
            INSERT INTO llm_configs (
                id, name, base_url, api_key, headers_json, model, backup_model, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                base_url = excluded.base_url,
                api_key = excluded.api_key,
                headers_json = excluded.headers_json,
                model = excluded.model,
                backup_model = excluded.backup_model,
                updated_at = excluded.updated_at
            """,
            (name, base_url, api_key, headers_json, model, backup_model, now_iso()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM llm_configs WHERE id = 1").fetchone()
        return config_to_dict(row, include_secret=False)
    finally:
        conn.close()
