"""云端 LLM 调用器（仅用于 Schema 合成等系统级任务）。

为什么和本机的 llm_client.py 分开：
  - 用户语料始终在本机；云端的 LLM 调用仅消耗结构化输入（goal、objects 字符串），
    不会接触用户文档。隔离两条调用路径，避免误把用户数据送到云端 key。
  - 凭据走云端独立 env 变量 MJQ_CLOUD_LLM_*，admin 可在不分发用户 LLM key 的
    情况下统一计费/审计 schema 合成调用。

环境变量：
  MJQ_CLOUD_LLM_API_KEY    必填；不填则 schema synth 进入 mock 模式
  MJQ_CLOUD_LLM_BASE_URL   兼容 OpenAI 协议的 base URL（默认 https://api.openai.com/v1）
  MJQ_CLOUD_LLM_MODEL      默认 gpt-4o-mini
  MJQ_CLOUD_LLM_TIMEOUT    秒，默认 30
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import requests


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def is_configured() -> bool:
    return bool(_env("MJQ_CLOUD_LLM_API_KEY"))


def chat_completion(messages: List[Dict], *, max_tokens: int = 4000,
                    temperature: float = 0.2, response_format_json: bool = False) -> Optional[str]:
    """OpenAI 兼容的 chat 请求。失败返回 None（caller 可走 fallback）。"""
    api_key = _env("MJQ_CLOUD_LLM_API_KEY")
    if not api_key:
        return None
    base = _env("MJQ_CLOUD_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = _env("MJQ_CLOUD_LLM_MODEL", "gpt-4o-mini")
    timeout = float(_env("MJQ_CLOUD_LLM_TIMEOUT", "30") or "30")
    payload: Dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format_json:
        payload["response_format"] = {"type": "json_object"}
    try:
        r = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        return (data.get("choices") or [{}])[0].get("message", {}).get("content") or None
    except (requests.RequestException, ValueError):
        return None
