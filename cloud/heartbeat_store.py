"""云端心跳记录持久化（P5）。

存储：cloud/data/heartbeats.json —— { username: latest_record_dict }
仅保留每用户最新一次（够 admin 控制台用；要历史趋势可换 SQLite）。

线程安全：单写锁（云端 Flask 是多线程 dev server，并发写需要保护）。
"""
from __future__ import annotations

import json
import os
import threading
from typing import Dict, Optional


_lock = threading.Lock()


def _path(cloud_dir: str) -> str:
    return os.path.join(cloud_dir, "data", "heartbeats.json")


def read_all(cloud_dir: str) -> Dict[str, Dict]:
    p = _path(cloud_dir)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get(cloud_dir: str, username: str) -> Optional[Dict]:
    return read_all(cloud_dir).get(username)


def write(cloud_dir: str, username: str, record: Dict) -> None:
    if not username:
        return
    with _lock:
        all_records = read_all(cloud_dir)
        all_records[username] = record
        p = _path(cloud_dir)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(all_records, f, ensure_ascii=False, indent=2)
