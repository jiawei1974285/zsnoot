#!/usr/bin/env python3
"""Persist lightweight agent status for the UI."""

import json
import os
import tempfile
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional


_io_lock = threading.Lock()
ACTIVE_STATES = {"archiving", "processing", "analyzing", "generating", "parsing", "linking"}
ACTIVE_STATE_TTL = timedelta(minutes=30)


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
            payload = json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        return set_status(project_dir, "idle", "空闲")
    if _is_stale_active_status(payload):
        return set_status(
            project_dir,
            "idle",
            "空闲",
            {"expired_state": payload.get("state"), "expired_at": payload.get("updated_at")},
        )
    return payload


def _is_stale_active_status(payload: Dict) -> bool:
    state = payload.get("state")
    if state not in ACTIVE_STATES:
        return False
    try:
        updated_at = datetime.fromisoformat(str(payload.get("updated_at", "")))
    except ValueError:
        return True
    return datetime.now() - updated_at > ACTIVE_STATE_TTL
