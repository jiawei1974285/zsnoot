#!/usr/bin/env python3
"""本机 agent 的数据目录解析（P2-B）。

划清两类目录的边界（《工程控制论》原则 5：先把"系统"边界讲清）：

  INSTALL_DIR （代码所在）           USER_DATA_DIR （用户数据所在）
  ──────────────────────             ──────────────────────────────
  *.py / scripts/                    wiki/
  templates/ frontend/dist/          raw/
  schema.md (人读)                   data/  (含 activity_log / batches /
  config/secret.key (Flask session)         schema_binding.json)
  config/jwt.secret (云本机共享)     config/  (含 schema.yaml / config.yaml)
  cloud/templates/*.yaml             embeddings/
                                     .env  (LLM API key 等敏感凭据)

绑定文件 `<INSTALL_DIR>/data/machine_binding.json` 决定 USER_DATA_DIR：
  - 文件存在且 username 字段非空 → ~/.handynotes/<username>/
  - 文件不存在 / 为空 → 退回到 INSTALL_DIR（**单体兼容**：老部署零迁移）

绑定何时建立：
  - `python -m scripts.bind_user <username>`（推荐：先 bind 再启动 agent）
  - 或：第一次有效 JWT 到达时 agent 自动绑定为该用户（动机：演示场景零配置）

为什么进程级而非请求级：
  - 用户决策"一台机器一台用户"（plan 文件）→ 进程级最简单
  - 149 处 PROJECT_DIR 中绝大部分是模块级常量，请求级会触发大面积重构
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


INSTALL_DIR: str = os.path.dirname(os.path.abspath(__file__))


def _binding_file() -> str:
    return os.path.join(INSTALL_DIR, "data", "machine_binding.json")


def _user_dir_for(username: str) -> str:
    """返回某 cloud 用户在本机的数据目录。可被环境变量 MJQ_USER_HOME 覆盖（测试用）。"""
    if not username:
        raise ValueError("username is required")
    base = os.environ.get("MJQ_USER_HOME") or os.path.join(
        os.path.expanduser("~"), ".handynotes"
    )
    return os.path.join(base, username)


_lock = threading.Lock()
_cached_user_dir: Optional[str] = None
_cached_username: Optional[str] = None


def _resolve() -> tuple[str, Optional[str]]:
    """返回 (user_data_dir, bound_username)。无绑定 → (INSTALL_DIR, None)。"""
    bf = _binding_file()
    if not os.path.exists(bf):
        return INSTALL_DIR, None
    try:
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        return INSTALL_DIR, None
    username = (data.get("username") or "").strip()
    if not username:
        return INSTALL_DIR, None
    user_dir = _user_dir_for(username)
    return user_dir, username


def get_user_data_dir() -> str:
    """当前进程的用户数据根目录。带缓存——绑定确定后不变。"""
    global _cached_user_dir, _cached_username
    with _lock:
        if _cached_user_dir is None:
            user_dir, username = _resolve()
            _cached_user_dir = user_dir
            _cached_username = username
        return _cached_user_dir


def current_bound_user() -> Optional[str]:
    get_user_data_dir()  # 触发解析
    return _cached_username


def is_legacy_mode() -> bool:
    """无绑定时返回 True —— 老部署直接复用 INSTALL_DIR 作为数据根，行为不变。"""
    return current_bound_user() is None


def bind_machine_to(username: str) -> str:
    """把本机绑定到某 cloud 用户。

    - 创建 `~/.handynotes/<username>/{wiki,raw,data,config,embeddings}/`
    - 写 `<INSTALL_DIR>/data/machine_binding.json`
    - 失效缓存（下一次 get_user_data_dir 会重新解析）

    返回 user_data_dir。
    """
    if not username or not username.strip():
        raise ValueError("username is required")
    username = username.strip()
    user_dir = _user_dir_for(username)
    for sub in ("wiki", "raw", "data", "config", "embeddings"):
        os.makedirs(os.path.join(user_dir, sub), exist_ok=True)
    bf = _binding_file()
    os.makedirs(os.path.dirname(bf), exist_ok=True)
    payload = {
        "username": username,
        "user_data_dir": user_dir,
        "bound_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(bf, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    invalidate()
    return user_dir


def unbind_machine() -> bool:
    """删除绑定文件。返回是否真的删了一个。"""
    bf = _binding_file()
    existed = os.path.exists(bf)
    if existed:
        os.remove(bf)
    invalidate()
    return existed


def invalidate() -> None:
    global _cached_user_dir, _cached_username
    with _lock:
        _cached_user_dir = None
        _cached_username = None


# ─── 路径便捷访问器（数据） ──────────────────────────────────
def get_wiki_dir() -> str:
    return os.path.join(get_user_data_dir(), "wiki")


def get_data_dir() -> str:
    return os.path.join(get_user_data_dir(), "data")


def get_config_dir() -> str:
    return os.path.join(get_user_data_dir(), "config")


def get_embeddings_dir() -> str:
    return os.path.join(get_user_data_dir(), "embeddings")


def get_dotenv_path() -> str:
    return os.path.join(get_user_data_dir(), ".env")


def get_log_dir() -> str:
    return get_user_data_dir()  # mjq.log 直接落在用户根；与老布局一致


# ─── 路径便捷访问器（代码 / 共享） ──────────────────────────
def get_install_dir() -> str:
    return INSTALL_DIR


def get_jwt_secret_dir() -> str:
    """JWT 共享密钥放 INSTALL_DIR/config/，云端和本机进程共用。"""
    return INSTALL_DIR


def get_session_secret_path() -> str:
    """Flask session secret，与代码同寿命。"""
    return os.path.join(INSTALL_DIR, "config", "secret.key")


def get_frontend_dist() -> str:
    return os.path.join(INSTALL_DIR, "frontend", "dist")


def get_install_wiki_templates_dir() -> str:
    """种子模板目录（auto_ingest 解析 page section 用）。

    fallback：用户 wiki/templates/ 不存在时回退到 install_dir/wiki/templates/。
    """
    return os.path.join(INSTALL_DIR, "wiki", "templates")
