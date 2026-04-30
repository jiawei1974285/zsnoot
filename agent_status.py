#!/usr/bin/env python3
"""Persist lightweight agent status for the UI.

线程安全：当 ingest_service 用 ThreadPoolExecutor 并发处理多文件时，多个 worker
会同时调用 set_status；用 _io_lock 串行化文件写，并通过 os.replace 实现原子替换，
避免读端读到半截 JSON。
"""
import json
import os
import tempfile
import threading
from datetime import datetime
from typing import Dict, Optional


_io_lock = threading.Lock()


def _status_path(project_dir: str) -> str:
    return os.path.join(project_dir, "data", "agent_status.json")


def set_status(project_dir: str, state: str, message: str = "", detail: Optional[Dict] = None) -> Dict:
    payload = {
        "state": state,
        "message": message,
        "detail": detail or {},
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    path = _status_path(project_dir)
    dir_name = os.path.dirname(path)
    os.makedirs(dir_name, exist_ok=True)
    with _io_lock:
        # 写到临时文件再原子替换，避免读端读到 truncate 中的空文件
        fd, tmp_path = tempfile.mkstemp(prefix="agent_status.", suffix=".tmp", dir=dir_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    return payload


def get_status(project_dir: str) -> Dict:
    path = _status_path(project_dir)
    if not os.path.exists(path):
        return set_status(project_dir, "idle", "空闲")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        return set_status(project_dir, "idle", "空闲")
