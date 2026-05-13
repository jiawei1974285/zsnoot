#!/usr/bin/env python3
"""Activity log for UI metrics and the human-readable wiki audit trail."""
import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional


MAX_ENTRIES = 1000
TRIM_TO = 500


def _log_path(project_dir: str) -> str:
    return os.path.join(project_dir, "data", "activity_log.json")


def _wiki_log_path(project_dir: str) -> str:
    return os.path.join(project_dir, "wiki", "log.md")


def _read(project_dir: str) -> List[Dict]:
    path = _log_path(project_dir)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except (json.JSONDecodeError, OSError):
        return []


def _write(project_dir: str, entries: List[Dict]) -> None:
    path = _log_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _append_wiki_log(project_dir: str, entry: Dict) -> None:
    path = _wiki_log_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# 知识库日志\n\n")

    details = json.dumps(entry.get("details") or {}, ensure_ascii=False, sort_keys=True)
    line = (
        f"- {entry.get('timestamp')} | `{entry.get('action')}`"
        f" | target: `{entry.get('target') or '-'}`"
        f" | details: `{details}`\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def record(project_dir: str, action: str, target: Optional[str] = None, details: Optional[Dict] = None) -> Dict:
    """Append one operation log.

    The JSON log is retained for fast UI statistics; wiki/log.md is the
    append-only human audit trail. Logging errors must not break core flows.
    """
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action": action,
        "target": target,
        "details": details or {},
    }
    try:
        entries = _read(project_dir)
        entries.insert(0, entry)
        if len(entries) > MAX_ENTRIES:
            entries = entries[:TRIM_TO]
        _write(project_dir, entries)
        _append_wiki_log(project_dir, entry)
        return entry
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] activity_log.record failed: {exc}")
        return {}


def recent(project_dir: str, limit: int = 20) -> List[Dict]:
    entries = _read(project_dir)
    return entries[:max(1, min(limit, MAX_ENTRIES))]


def count_since(project_dir: str, days: int) -> Dict[str, int]:
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    counts: Dict[str, int] = {}
    for entry in _read(project_dir):
        if entry.get("timestamp", "") < cutoff:
            break
        action = entry.get("action", "unknown")
        counts[action] = counts.get(action, 0) + 1
    return counts


def count_between(project_dir: str, days_ago_start: int, days_ago_end: int) -> Dict[str, int]:
    if days_ago_start >= days_ago_end:
        return {}
    end_ts = (datetime.now() - timedelta(days=days_ago_start)).isoformat(timespec="seconds")
    start_ts = (datetime.now() - timedelta(days=days_ago_end)).isoformat(timespec="seconds")
    counts: Dict[str, int] = {}
    for entry in _read(project_dir):
        ts = entry.get("timestamp", "")
        if ts >= end_ts:
            continue
        if ts < start_ts:
            break
        action = entry.get("action", "unknown")
        counts[action] = counts.get(action, 0) + 1
    return counts


def count_by_day(project_dir: str, days: int = 14, actions: Optional[List[str]] = None) -> List[Dict]:
    if actions is None:
        actions = ["ingest", "chat", "create_page", "edit_page"]

    today = date.today()
    buckets: Dict[str, Dict[str, int]] = {}
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        key = d.isoformat()
        buckets[key] = {a: 0 for a in actions}

    cutoff_ts = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    for entry in _read(project_dir):
        ts = entry.get("timestamp", "")
        if ts < cutoff_ts:
            break
        action = entry.get("action", "")
        if action not in actions:
            continue
        day_key = ts[:10]
        if day_key in buckets:
            buckets[day_key][action] += 1

    return [{"date": k, **buckets[k]} for k in sorted(buckets.keys())]
