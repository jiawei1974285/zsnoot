#!/usr/bin/env python3
"""本机 agent → 云端 心跳上报（P5）。

每 5 分钟后台线程 POST 一次到 cloud `/api/cloud/agent/heartbeat`：
  {
    username:        当前绑定用户（绑定才上报，未绑定不发）
    agent_version:   字符串（写死 P5 = "0.5.0"）
    schema_key:      schema_runtime 当前 key
    pages_total:     wiki/*.md 数量（粗略）
    last_ingest_at:  最近一次 ingest 时间（从 ingest_batches.json 取）
    scheduled_tasks: 启用中的调度任务数
    sent_at:         本地时间 ISO
  }

设计要点（《工程控制论》原则 8 能观察 + 原则 14 兜底）：
  - 失败仅记日志，不影响本机功能（云端挂了本机仍能用）
  - 心跳只发计数和时间戳，**绝不发用户语料**（与"用户数据在本地"原则一致）
  - 单飞：模块级单例，重复 start() 是 no-op
  - 进程退出 atexit 清理
"""
from __future__ import annotations

import atexit
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from mjq_logging import get_logger

logger = get_logger(__name__)

AGENT_VERSION = "1.0.0"          # web 版 V1.0 —— P1-P5 全阶段完成的首个发布
HEARTBEAT_INTERVAL_SEC = 300     # 5 min


_thread: Optional[threading.Thread] = None
_stop_event: Optional[threading.Event] = None


def _cloud_url() -> str:
    return os.environ.get("MJQ_CLOUD_URL", "http://127.0.0.1:5005").rstrip("/")


def _verify_tls() -> bool:
    return os.environ.get("MJQ_CLOUD_VERIFY_TLS", "1").lower() not in {"0", "false", "no"}


def _read_token_for_heartbeat() -> Optional[str]:
    """心跳本身需要 JWT，但 heartbeat 是后台线程，没法用浏览器的 token。

    P5 简化方案：从 schema_binding.json 推断用户名，再用本机持有的"agent token"
    （由 cloud 在 bind 时下发）。当前实现：复用上一次成功 schema sync 留下的
    token？不行——access 30 min 过期。

    所以心跳用一个长期"agent_key"——P5 暂未实现 agent_key 颁发流程，
    退而求其次：尝试从环境变量 MJQ_AGENT_TOKEN 读。没有就跳过心跳。
    """
    return os.environ.get("MJQ_AGENT_TOKEN", "").strip() or None


def collect_stats(project_dir: str) -> dict:
    """收集纯计数型心跳载荷。所有字段可观察，不含用户语料。"""
    stats = {
        "agent_version": AGENT_VERSION,
        "sent_at": datetime.now().isoformat(timespec="seconds"),
        "schema_key": "unknown",
        "pages_total": 0,
        "last_ingest_at": None,
        "scheduled_tasks_active": 0,
    }
    try:
        from schema_runtime import get_runtime
        stats["schema_key"] = get_runtime(project_dir).key
    except Exception:
        pass
    try:
        from wiki_links import list_wiki_files
        stats["pages_total"] = len(list_wiki_files(project_dir))
    except Exception:
        pass
    try:
        import json
        bp = Path(project_dir) / "data" / "ingest_batches.json"
        if bp.exists():
            with open(bp, "r", encoding="utf-8") as f:
                batches = json.load(f) or []
            if batches:
                # 最新一条 created_at
                stats["last_ingest_at"] = max(
                    (b.get("created_at") or "" for b in batches),
                    default=None,
                ) or None
    except Exception:
        pass
    try:
        import scheduler as sched
        stats["scheduled_tasks_active"] = sum(
            1 for t in sched.list_tasks(project_dir) if t.get("enabled", True)
        )
    except Exception:
        pass
    return stats


def send_once(project_dir: str, username: str, token: str) -> bool:
    payload = {"username": username, **collect_stats(project_dir)}
    try:
        r = requests.post(
            _cloud_url() + "/api/cloud/agent/heartbeat",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
            verify=_verify_tls(),
        )
        if r.status_code == 200:
            return True
        logger.warning(f"[heartbeat] HTTP {r.status_code}: {r.text[:200]}")
    except requests.RequestException as exc:
        logger.warning(f"[heartbeat] network error: {exc}")
    return False


def _loop(project_dir: str, stop_event: threading.Event) -> None:
    # 启动稍延迟，避免在 app boot 阻塞期间打云端
    stop_event.wait(timeout=10)
    while not stop_event.is_set():
        try:
            from user_data import current_bound_user
            user = current_bound_user()
            token = _read_token_for_heartbeat()
            if user and token:
                send_once(project_dir, user, token)
            else:
                logger.debug("[heartbeat] skip: bound_user=%s token=%s",
                             user, "yes" if token else "no")
        except Exception as exc:
            logger.warning(f"[heartbeat] loop error: {exc}")
        # 间隔；可被 stop_event 提前唤醒
        stop_event.wait(timeout=HEARTBEAT_INTERVAL_SEC)


def start(project_dir: str) -> None:
    """进程启动时调用一次。无绑定用户也启动线程，运行时再判断要不要发。"""
    global _thread, _stop_event
    if _thread is not None:
        return
    _stop_event = threading.Event()
    _thread = threading.Thread(
        target=_loop, args=(project_dir, _stop_event), daemon=True, name="mjq-heartbeat"
    )
    _thread.start()
    atexit.register(stop)
    logger.info(f"[heartbeat] started (interval {HEARTBEAT_INTERVAL_SEC}s)")


def stop() -> None:
    global _thread, _stop_event
    if _stop_event:
        _stop_event.set()
    _thread = None
    _stop_event = None
