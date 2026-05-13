#!/usr/bin/env python3
"""LLM 连接测试。"""
import os
import re
from typing import Callable, Dict, Optional

import requests


def load_env_file(path: str) -> Dict[str, str]:
    """加载 .env 文件为 dict。"""
    env_vars = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


# 加载项目 .env 并合并到 os.environ
_project_root = os.path.dirname(os.path.abspath(__file__))
_dotenv = load_env_file(os.path.join(_project_root, ".env"))
for k, v in _dotenv.items():
    os.environ.setdefault(k, v)


def resolve_env_value(value: str) -> str:
    """Resolve strings like ${LLM_API_KEY} from environment."""
    if not isinstance(value, str):
        return ""
    match = re.fullmatch(r"\$\{([^}]+)\}", value.strip())
    if match:
        return os.environ.get(match.group(1), "")
    return value


def test_llm_connection(llm_config: Dict, post_func: Optional[Callable] = None) -> Dict:
    """Send a tiny OpenAI-compatible chat completion request."""
    post = post_func or requests.post
    get = requests.get
    provider = (llm_config.get("provider") or "").lower()
    base_url = (llm_config.get("base_url") or "").rstrip("/")
    is_ollama = provider == "ollama" or base_url.endswith(":11434") or "localhost:11434" in base_url or "127.0.0.1:11434" in base_url
    if base_url and not base_url.endswith("/v1") and ("deepseek" in base_url or "dashscope" in base_url or is_ollama):
        base_url = f"{base_url}/v1"
    model = llm_config.get("model") or ""
    api_key = resolve_env_value(llm_config.get("api_key") or "")

    if not base_url:
        return {"ok": False, "message": "接口地址不能为空"}
    if not model:
        return {"ok": False, "message": "模型名称不能为空"}

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if is_ollama:
        raw_base = base_url[:-3] if base_url.endswith("/v1") else base_url
        try:
            tags_response = get(f"{raw_base}/api/tags", timeout=10)
            tags_response.raise_for_status()
            tags_data = tags_response.json()
            installed = {item.get("name") for item in tags_data.get("models", [])}
            if model not in installed:
                return {
                    "ok": False,
                    "message": f"Ollama 已连接，但本地未找到模型：{model}",
                    "model": model,
                    "available_models": sorted(installed),
                }
            return {
                "ok": True,
                "message": "Ollama 连接正常，模型已就绪",
                "model": model,
            }
        except Exception as exc:
            return {
                "ok": False,
                "message": f"Ollama 连接失败：{exc}",
                "model": model,
            }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是模型连通性测试助手。"},
            {"role": "user", "content": "请只回复 OK"},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }

    try:
        response = post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "ok": True,
            "message": "模型连接正常",
            "model": model,
            "response": content[:100],
        }
    except Exception as exc:
        return {
            "ok": False,
            "message": f"模型连接失败：{exc}",
            "model": model,
        }
