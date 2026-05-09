"""云端 schema 模板加载与列表 —— P2。

模板 YAML 文件位于 cloud/templates/<key>.yaml，文件名即 key。
template_key 与 user 记录关联，本机 agent 拿到后可独立解析。
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

import yaml


_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def list_template_keys() -> List[str]:
    if not os.path.isdir(_TEMPLATES_DIR):
        return []
    return sorted(
        os.path.splitext(name)[0]
        for name in os.listdir(_TEMPLATES_DIR)
        if name.endswith(".yaml") and not name.startswith("_")
    )


def load_template(key: str) -> Optional[Dict]:
    if not key or "/" in key or "\\" in key or ".." in key:
        return None
    path = os.path.join(_TEMPLATES_DIR, f"{key}.yaml")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("key", key)
    return data


def template_summary(data: Dict) -> Dict:
    """裁剪模板，给前端做卡片展示用：去掉大字段，只留概览。"""
    if not data:
        return {}
    return {
        "key": data.get("key"),
        "label": data.get("label") or data.get("key"),
        "description": data.get("description") or "",
        "wiki_dirs": list(data.get("wiki_dirs") or [])[:8],   # 最多前 8 个，UI 展示用
        "category_count": len(data.get("wiki_dirs") or []),
        "type_count": len(data.get("type_directory_map") or {}),
    }


def list_template_summaries() -> List[Dict]:
    out = []
    for key in list_template_keys():
        data = load_template(key)
        if not data:
            continue
        out.append(template_summary(data))
    return out


DEFAULT_TEMPLATE_KEY = "police"


def is_known_key(key: str) -> bool:
    return bool(key) and load_template(key) is not None
