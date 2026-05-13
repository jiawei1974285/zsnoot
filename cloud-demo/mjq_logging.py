#!/usr/bin/env python3
"""集中 logging 配置。

设计原则（参考《工程控制论》原则 8 能观察性）：
  - 所有模块统一通过 get_logger(__name__) 拿到 logger
  - 写入 mjq.log（RotatingFileHandler，单文件 5MB，保留 5 个备份）
  - 同时输出到 stderr，便于开发期 tail
  - LLM 调用单独走 data/llm_calls.jsonl（结构化、便于离线分析耗时与失败模式）
"""
import json
import logging
import os
import sys
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


_PROJECT_DIR = Path(__file__).parent
_LOG_PATH = _PROJECT_DIR / "mjq.log"
_LLM_CALLS_PATH = _PROJECT_DIR / "data" / "llm_calls.jsonl"

_setup_done = False
_setup_lock = threading.Lock()
_llm_log_lock = threading.Lock()


def setup_logging(level: int = logging.INFO) -> None:
    """在进程启动时调用一次。重复调用安全（幂等）。"""
    global _setup_done
    with _setup_lock:
        if _setup_done:
            return

        root = logging.getLogger()
        root.setLevel(level)

        # 清掉 Flask/Werkzeug 默认 handler 避免重复输出
        for h in list(root.handlers):
            root.removeHandler(h)

        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = RotatingFileHandler(
            _LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(level)
        root.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(fmt)
        stream_handler.setLevel(logging.WARNING)  # 终端只显示 WARNING 以上
        root.addHandler(stream_handler)

        # Werkzeug 访问日志降到 WARNING（避免每个 GET /api/agent/status 都 INFO）
        logging.getLogger("werkzeug").setLevel(logging.WARNING)

        _setup_done = True
        logging.getLogger(__name__).info("logging 已初始化 → %s", _LOG_PATH)


def get_logger(name: str) -> logging.Logger:
    """获取命名 logger。如果尚未 setup，自动初始化（懒加载防御）。"""
    if not _setup_done:
        setup_logging()
    return logging.getLogger(name)


def log_llm_call(
    role: str,
    model: str,
    base_url: str,
    latency_ms: int,
    status: str,
    prompt_chars: int = 0,
    response_chars: int = 0,
    error: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """把单次 LLM 调用记录追加到 data/llm_calls.jsonl。

    用于离线分析：哪个 model 慢/快、哪种 role 失败率高、prompt 大小与延迟关系。
    线程安全（并发文件处理时多个 worker 会同时写）。
    """
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "role": role,
        "model": model,
        "base_url": base_url,
        "latency_ms": int(latency_ms),
        "status": status,  # ok | error | timeout
        "prompt_chars": int(prompt_chars),
        "response_chars": int(response_chars),
    }
    if error:
        record["error"] = str(error)[:500]
    if extra:
        record["extra"] = extra

    try:
        _LLM_CALLS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _llm_log_lock:
            with open(_LLM_CALLS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        # 日志写失败不能拖垮主流程，但要让运维知道
        get_logger(__name__).warning("写 llm_calls.jsonl 失败: %s", exc)
