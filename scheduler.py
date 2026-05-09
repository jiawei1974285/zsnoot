#!/usr/bin/env python3
"""本机定时任务调度（P4）。

任务类型（白名单，不接受任意 Python 调用以防注入）：
  inbox_scan          扫描 raw/inbox 触发 auto_ingest
  orphan_auto_fill    扫描 dangling links 自动建占位页（use_llm=False 默认）
  orphan_index_refresh 把孤页列表写入 wiki/index.md
  wiki_lint           运行 lint 体检（断链/孤页/过期统计）

调度类型：
  cron     标准 cron 表达式（5 段 min hour day month dow，可选秒）
  interval 间隔分钟数

存储：
  <USER_DATA_DIR>/data/scheduled_tasks.json
  字段: id, name, kind, schedule {type, value}, enabled, last_run_at, last_status, last_error

设计要点（《工程控制论》原则 8 能观察 + 原则 14 兜底）：
  - last_run_at / last_status 入库 → 前端能看到执行历史
  - 任务 callable 异常被吞掉但记录 last_error，不让一个失败任务杀掉整个 scheduler
  - 进程退出钩子 atexit 关 scheduler，避免线程泄漏
  - APScheduler 重复启动幂等：start() 会拒绝二次调用，模块级 _scheduler 单例
"""
from __future__ import annotations

import atexit
import json
import os
import threading
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from mjq_logging import get_logger

logger = get_logger(__name__)


# ─── 任务实现注册表 ──────────────────────────────────────
def _task_inbox_scan(project_dir: str) -> Dict:
    """扫 raw/inbox，把还没入库的文件交给 auto_ingest（按现有路径走）。"""
    from config_store import get_raw_dir
    inbox = os.path.join(get_raw_dir(project_dir), 'inbox')
    if not os.path.isdir(inbox):
        return {'skipped': True, 'reason': 'no inbox dir'}
    # 现有 ingest 流程通过文件 watcher 触发；这里只做"汇报有几个文件等着"
    files = [f for f in os.listdir(inbox) if os.path.isfile(os.path.join(inbox, f))]
    # 实际触发：写一个标记，由 file_watcher 的 fallback poll 在下一周期处理
    # 简单实现：直接调 ingest_uploaded_files 风格不合适（需要 FileStorage 对象）
    # P4 阶段先返回计数，让运维有节奏感；下一阶段把 ingest_inbox_pass 显式抽出来。
    return {'inbox_count': len(files), 'inbox': inbox}


def _task_orphan_auto_fill(project_dir: str) -> Dict:
    from orphan_detector import auto_fill_dangling
    return auto_fill_dangling(project_dir, use_llm=False, limit=50)


def _task_orphan_index_refresh(project_dir: str) -> Dict:
    from orphan_detector import mark_orphans_in_index
    return mark_orphans_in_index(project_dir)


def _task_wiki_lint(project_dir: str) -> Dict:
    from orphan_detector import scan_links
    return scan_links(project_dir)


TASK_KINDS: Dict[str, Callable[[str], Dict]] = {
    'inbox_scan': _task_inbox_scan,
    'orphan_auto_fill': _task_orphan_auto_fill,
    'orphan_index_refresh': _task_orphan_index_refresh,
    'wiki_lint': _task_wiki_lint,
}


# ─── 持久化 ──────────────────────────────────────────────
_lock = threading.Lock()


def _store_path(project_dir: str) -> str:
    return os.path.join(project_dir, 'data', 'scheduled_tasks.json')


def load_tasks(project_dir: str) -> List[Dict]:
    p = _store_path(project_dir)
    if not os.path.exists(p):
        return []
    try:
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f) or []
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_tasks(project_dir: str, tasks: List[Dict]) -> None:
    p = _store_path(project_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


# ─── Scheduler 单例 ──────────────────────────────────────
_scheduler = None
_scheduler_project_dir: Optional[str] = None


def _build_trigger(schedule: Dict):
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    schedule_type = (schedule or {}).get('type')
    value = (schedule or {}).get('value')
    if schedule_type == 'cron':
        # 期望 5 段 cron 表达式: 'min hour day month dow'
        parts = (value or '').split()
        if len(parts) != 5:
            raise ValueError("cron 表达式需 5 段（分 时 日 月 周）")
        return CronTrigger(
            minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4],
        )
    if schedule_type == 'interval':
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            raise ValueError("interval 需要正整数分钟数")
        if minutes < 1:
            raise ValueError("interval 至少 1 分钟")
        return IntervalTrigger(minutes=minutes)
    raise ValueError(f"未知的调度类型：{schedule_type}")


def _make_runner(task_id: str, kind: str, project_dir: str) -> Callable[[], None]:
    """生成包装后的可执行函数：日志、异常吞咽、状态回写。"""
    def runner():
        impl = TASK_KINDS.get(kind)
        if not impl:
            logger.warning(f"[scheduler] task {task_id} kind {kind} 未注册，跳过")
            return
        started = datetime.now()
        status = 'ok'
        error = ''
        try:
            result = impl(project_dir)
            logger.info(f"[scheduler] task {task_id} ({kind}) ok in "
                        f"{(datetime.now()-started).total_seconds():.2f}s: {result}")
        except Exception as exc:
            status = 'error'
            error = str(exc)[:300]
            logger.exception(f"[scheduler] task {task_id} ({kind}) failed")
        # 回写 last_run
        with _lock:
            tasks = load_tasks(project_dir)
            for t in tasks:
                if t.get('id') == task_id:
                    t['last_run_at'] = started.isoformat(timespec='seconds')
                    t['last_status'] = status
                    t['last_error'] = error
                    break
            save_tasks(project_dir, tasks)
    return runner


def start(project_dir: str) -> None:
    """进程启动时调用一次（幂等）。读取所有 enabled=true 任务并加进 scheduler。"""
    global _scheduler, _scheduler_project_dir
    if _scheduler is not None:
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    _scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
    _scheduler.start()
    _scheduler_project_dir = project_dir
    atexit.register(_shutdown)
    logger.info(f"[scheduler] started, project_dir={project_dir}")
    # 注册已存在的任务
    for t in load_tasks(project_dir):
        if t.get('enabled', True):
            try:
                _add_to_scheduler(t)
            except Exception as exc:
                logger.warning(f"[scheduler] skip {t.get('id')}: {exc}")


def _shutdown() -> None:
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None


def _add_to_scheduler(task: Dict) -> None:
    if _scheduler is None or _scheduler_project_dir is None:
        return
    trigger = _build_trigger(task.get('schedule') or {})
    runner = _make_runner(task['id'], task['kind'], _scheduler_project_dir)
    _scheduler.add_job(runner, trigger, id=task['id'], replace_existing=True)


def _remove_from_scheduler(task_id: str) -> None:
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(task_id)
    except Exception:
        pass  # 不存在就不删，无所谓


# ─── CRUD（被 app.py 路由调用） ────────────────────────────
def list_tasks(project_dir: str) -> List[Dict]:
    return load_tasks(project_dir)


def create_task(project_dir: str, *, name: str, kind: str, schedule: Dict,
                enabled: bool = True) -> Dict:
    if kind not in TASK_KINDS:
        raise ValueError(f"未知任务类型：{kind}（合法：{list(TASK_KINDS.keys())}）")
    _build_trigger(schedule)  # 提前抛错
    task = {
        'id': uuid.uuid4().hex[:12],
        'name': (name or kind).strip(),
        'kind': kind,
        'schedule': schedule,
        'enabled': bool(enabled),
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'last_run_at': None,
        'last_status': None,
        'last_error': '',
    }
    with _lock:
        tasks = load_tasks(project_dir)
        tasks.append(task)
        save_tasks(project_dir, tasks)
    if task['enabled']:
        try:
            _add_to_scheduler(task)
        except Exception as exc:
            logger.warning(f"[scheduler] add {task['id']} failed: {exc}")
    return task


def update_task(project_dir: str, task_id: str, **fields) -> Optional[Dict]:
    allowed = {'name', 'enabled', 'schedule'}
    safe = {k: v for k, v in fields.items() if k in allowed}
    with _lock:
        tasks = load_tasks(project_dir)
        target = next((t for t in tasks if t.get('id') == task_id), None)
        if not target:
            return None
        if 'schedule' in safe:
            _build_trigger(safe['schedule'])  # 验证
        target.update(safe)
        save_tasks(project_dir, tasks)
    # 重新挂 scheduler
    _remove_from_scheduler(task_id)
    if target.get('enabled', True):
        try:
            _add_to_scheduler(target)
        except Exception as exc:
            logger.warning(f"[scheduler] update {task_id} re-add failed: {exc}")
    return target


def delete_task(project_dir: str, task_id: str) -> bool:
    with _lock:
        tasks = load_tasks(project_dir)
        new_tasks = [t for t in tasks if t.get('id') != task_id]
        removed = len(new_tasks) != len(tasks)
        if removed:
            save_tasks(project_dir, new_tasks)
    _remove_from_scheduler(task_id)
    return removed


def run_now(project_dir: str, task_id: str) -> Optional[Dict]:
    """同步执行一次（调试 / 手动触发）。"""
    tasks = load_tasks(project_dir)
    target = next((t for t in tasks if t.get('id') == task_id), None)
    if not target:
        return None
    runner = _make_runner(task_id, target['kind'], project_dir)
    runner()
    # 返回最新状态
    return next((t for t in load_tasks(project_dir) if t.get('id') == task_id), None)
