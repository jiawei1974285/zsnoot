#!/usr/bin/env python3
"""
系统配置读写工具。

分工：
  config/config.yaml —— 存放非敏感配置（模型名、base_url、端口等）
  .env               —— 存放敏感凭据（api_key 等环境变量）
"""
import os
from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional

import yaml


# ── .env 文件读写 ─────────────────────────────────────────────

MODEL_ENV_FIELDS = {
    "llm": {
        "api_key": "LLM_API_KEY",
        "base_url": "LLM_BASE_URL",
        "model": "LLM_MODEL",
        "provider": "LLM_PROVIDER",
    },
    "vision_model": {
        "api_key": "VISION_MODEL_API_KEY",
        "base_url": "VISION_MODEL_BASE_URL",
        "model": "VISION_MODEL_MODEL",
        "provider": "VISION_MODEL_PROVIDER",
    },
    "ocr_model": {
        "api_key": "OCR_MODEL_API_KEY",
        "base_url": "OCR_MODEL_BASE_URL",
        "model": "OCR_MODEL_MODEL",
        "provider": "OCR_MODEL_PROVIDER",
    },
}

ENV_KEYS_LLM = {key for mapping in MODEL_ENV_FIELDS.values() for key in mapping.values()}


def dotenv_path(project_dir: str) -> str:
    return os.path.join(project_dir, ".env")


def load_dotenv(project_dir: str) -> Dict[str, str]:
    """Load .env file -> dict (only LLM_ keys)."""
    path = dotenv_path(project_dir)
    if not os.path.exists(path):
        return {}
    result = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k in ENV_KEYS_LLM:
                result[k] = v
    return result


def save_dotenv(project_dir: str, overrides: Dict[str, str]) -> Dict[str, str]:
    """Merge overrides into .env (only LLM_ keys) and write back."""
    path = dotenv_path(project_dir)
    current = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    current[k.strip()] = v.strip()

    # apply overrides (only whitelisted keys)
    for k, v in (overrides or {}).items():
        if k in ENV_KEYS_LLM:
            current[k] = v

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    lines = []
    for k in sorted(current):
        lines.append(f"{k}={current[k]}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return {k: current[k] for k in ENV_KEYS_LLM if k in current}


# ── YAML 配置读写 ──────────────────────────────────────────────


def load_config(config_path: str) -> Dict:
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: Dict, updates: Dict) -> Dict:
    result = deepcopy(base)
    for key, value in (updates or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def save_config(config_path: str, config: Dict) -> Dict:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return config


def update_config(config_path: str, updates: Dict) -> Dict:
    config = load_config(config_path)
    merged = deep_merge(config, updates or {})
    return save_config(config_path, merged)


def get_raw_dir(project_dir: str) -> str:
    """返回 raw 目录路径。

    优先级:
      1. config.yaml 中 raw_dir 字段(非空,且为合法绝对路径)
      2. fallback 到 <project_dir>/raw
    """
    config_path = os.path.join(project_dir, "config", "config.yaml")
    config = load_config(config_path)
    custom = (config.get("raw_dir") or "").strip()
    if custom:
        return os.path.abspath(custom)
    return os.path.join(project_dir, "raw")
