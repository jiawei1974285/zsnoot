#!/usr/bin/env python3
"""本机 agent 启动 / 首登 引导 —— P2。

职责（仅一项）：
  当本机 agent 收到一个云端 JWT 时，确保 <project_dir>/config/schema.yaml
  与云端为该用户保存的 template 一致。不一致或不存在 → 从云端拉取并写入。

不做：
  - 用户数据目录隔离（那是 P2-B 单独的事）
  - 模板冲突时的合并（P2-A 只支持整文件替换；现存 wiki 文件不被动）

设计要点（原则 9 反馈环最短 + 原则 14 兜底）：
  - 不强依赖：拉取失败仅记日志，本机仍可用既有 schema（fallback）
  - 幂等：用 schema_binding.json 里的 (username, template_key) 作指纹，
          若与请求的 JWT.sub 一致且 schema.yaml 存在，则跳过
  - 单飞：同一个 username 同时多个请求只触发一次拉取

环境变量：
  MJQ_CLOUD_URL   云端 baseURL，默认 http://127.0.0.1:5005
  MJQ_CLOUD_VERIFY_TLS  设为 0 关闭 TLS 校验（仅自签开发用）
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, Optional

import requests

from mjq_logging import get_logger
from schema_runtime import write_schema

logger = get_logger(__name__)


def _binding_path(project_dir: str) -> str:
    return os.path.join(project_dir, "data", "schema_binding.json")


def _read_binding(project_dir: str) -> Optional[Dict]:
    path = _binding_path(project_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _write_binding(project_dir: str, data: Dict) -> None:
    path = _binding_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _cloud_base() -> str:
    return os.environ.get("MJQ_CLOUD_URL", "http://127.0.0.1:5005").rstrip("/")


def _verify_tls() -> bool:
    return os.environ.get("MJQ_CLOUD_VERIFY_TLS", "1").lower() not in {"0", "false", "no"}


_lock = threading.Lock()
_in_flight: Dict[str, float] = {}        # username -> timestamp 锁住 30 秒


def _claim_in_flight(username: str) -> bool:
    """返回 True 表示当前线程拿到了独占执行权。"""
    now = time.time()
    with _lock:
        ts = _in_flight.get(username, 0)
        if now - ts < 30:
            return False
        _in_flight[username] = now
        return True


def _release_in_flight(username: str) -> None:
    with _lock:
        _in_flight.pop(username, None)


def fetch_schema_from_cloud(token: str) -> Optional[Dict]:
    """调云端 /api/cloud/schema/me。失败返回 None（不抛）。"""
    url = _cloud_base() + "/api/cloud/schema/me"
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
            verify=_verify_tls(),
        )
    except requests.RequestException as exc:
        logger.warning(f"[bootstrap] 拉云端 schema 失败：{exc}")
        return None
    if r.status_code != 200:
        logger.warning(f"[bootstrap] 拉云端 schema HTTP {r.status_code}: {r.text[:200]}")
        return None
    try:
        return r.json()
    except ValueError:
        logger.warning("[bootstrap] 云端 schema 响应不是 JSON")
        return None


def ensure_schema_for(project_dir: str, username: str, token: str) -> bool:
    """确保本机 schema 与云端为 username 配置的 template 一致。

    Returns:
      True  —— 本次确实拉取并写入了新 schema；
      False —— 已是最新（或失败、无需变更）。
    """
    if not username or not token:
        return False
    binding = _read_binding(project_dir) or {}
    schema_path = os.path.join(project_dir, "config", "schema.yaml")
    if (
        binding.get("username") == username
        and binding.get("template_key")
        and os.path.exists(schema_path)
    ):
        return False  # 已对齐

    if not _claim_in_flight(username):
        return False  # 另一个线程正在做
    try:
        payload = fetch_schema_from_cloud(token)
        if not payload or not isinstance(payload.get("schema"), dict):
            return False
        schema = payload["schema"]
        template_key = payload.get("template_key") or schema.get("key") or "custom"
        write_schema(project_dir, schema)
        _write_binding(project_dir, {
            "username": username,
            "template_key": template_key,
            "synced_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "cloud_url": _cloud_base(),
        })
        # 同时按新 schema 把 wiki 子目录补齐（不动已有内容）
        try:
            from schema_runtime import get_runtime
            wiki_dir = os.path.join(project_dir, "wiki")
            for sub in get_runtime(project_dir).wiki_dirs:
                os.makedirs(os.path.join(wiki_dir, sub), exist_ok=True)
        except Exception as exc:
            logger.warning(f"[bootstrap] 补 wiki 子目录失败：{exc}")
        logger.info(f"[bootstrap] schema 已同步：user={username} template={template_key}")
        return True
    finally:
        _release_in_flight(username)
