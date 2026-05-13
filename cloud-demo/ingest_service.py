#!/usr/bin/env python3
"""File ingest service: archive, wiki generation, vector indexing, rollback.

并发处理（参考《工程控制论》原则 17 多级分散控制）：批次内多文件用
ThreadPoolExecutor 并发执行，max_workers 由 config.yaml ingest.max_workers 控制
（默认 3，避免触发 LLM provider 限速）。
单文件场景退化为顺序执行，无开销。
"""
import os
import re
import shutil
import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ingest_batches import IngestBatchStore, default_store
from mjq_logging import get_logger

logger = get_logger(__name__)


WIKI_PREFIX = "wiki/"


class RawIntegrityError(RuntimeError):
    """Raised when an archived raw source is missing or has changed."""

ENTITY_TYPE_ALIASES = {
    "organizations": "organization",
    "events": "event",
    "case_summaries": "case_summary",
    "crime_patterns": "crime_pattern",
    "conclusions": "conclusion",
}


def safe_filename(filename: str) -> str:
    name = os.path.basename(filename or "upload")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name)
    name = re.sub(r"-+", "-", name).strip(" .-")
    return name or "upload"


def _rel_path(path: Path, project_dir: Path) -> str:
    return os.path.relpath(path, project_dir).replace("\\", "/")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_archived_path(item: Dict, project_dir: Path) -> Path:
    raw_path = Path(str(item.get("path") or ""))
    return raw_path if raw_path.is_absolute() else project_dir / raw_path


def _raw_metadata(path: Path) -> Dict:
    stat = path.stat()
    return {
        "sha256": file_sha256(path),
        "size": stat.st_size,
        "archived_at": datetime.now().isoformat(timespec="seconds"),
    }


def verify_archived_files(archived: Iterable[Dict], project_dir: str) -> None:
    root = Path(project_dir)
    for item in archived:
        path = _resolve_archived_path(item, root)
        if not path.exists() or not path.is_file():
            raise RawIntegrityError(f"Raw source missing: {item.get('path')}")
        expected_hash = item.get("sha256")
        expected_size = item.get("size")
        if expected_hash and file_sha256(path) != expected_hash:
            raise RawIntegrityError(f"Raw source changed: {item.get('path')}")
        if expected_size is not None and path.stat().st_size != expected_size:
            raise RawIntegrityError(f"Raw source size changed: {item.get('path')}")


def archive_uploads(files: Iterable, batch_id: str, project_dir: str) -> List[Dict]:
    from config_store import get_raw_dir

    root = Path(project_dir)
    raw_root = Path(get_raw_dir(project_dir))
    batch_dir = raw_root / "sources" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    archived = []

    for file_obj in files:
        filename = safe_filename(getattr(file_obj, "filename", "upload"))
        target = batch_dir / filename
        counter = 1
        while target.exists():
            stem, suffix = target.stem, target.suffix
            target = batch_dir / f"{stem}-{counter}{suffix}"
            counter += 1
        file_obj.save(str(target))
        metadata = _raw_metadata(target)
        # 若 raw 在项目外,path 用绝对路径;否则用相对路径以便和老批次记录兼容
        try:
            rel = _rel_path(target, root)
            archived.append({"name": filename, "path": rel, **metadata})
        except ValueError:
            archived.append({"name": filename, "path": str(target), **metadata})

    return archived


def extract_entities_from_analysis(analysis: Dict) -> List[Dict]:
    entities = analysis.get("entities", []) if isinstance(analysis, dict) else []
    if not isinstance(entities, list):
        return []
    normalized = []
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        item = dict(entity)
        entity_type = str(item.get("type") or "").strip().lower()
        item["type"] = ENTITY_TYPE_ALIASES.get(entity_type, entity_type)
        normalized.append(item)
    return normalized


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text or "")
    text = re.sub(r"-+", "-", text)
    return text.strip("-").lower() or "untitled"


def fallback_generate_wiki_page(project_dir: str, original: Dict, file_content: str, reason: str = "") -> Dict:
    """Create a basic source note when full ingest is unavailable."""
    root = Path(project_dir)
    title = Path(original.get("name", "未命名材料")).stem
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(f"{today}-{title}")[:90]
    target_dir = root / "wiki" / "notes"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{slug}.md"

    preview = (file_content or "").strip()
    if len(preview) > 4000:
        preview = preview[:4000] + "\n\n……（内容较长，已截取前 4000 字，原文见归档材料）"

    status_text = reason or "LLM 分析不可用，已生成基础知识页并写入本地检索。"
    body = f"""---
type: note
title: {title}
tags:
  - 自动入库
  - 待精炼
related: []
created: {today}
updated: {today}
source_file: {original.get("path", "")}
status: 待精炼
---
# {title}

## 入库状态
{status_text}

## 原始材料

{original.get("path", "")}

## 正文摘录

{preview or "未能解析出文本内容，请检查原始文件或补充解析依赖。"}
"""
    target.write_text(body, encoding="utf-8")
    return {
        "path": os.path.relpath(target, root).replace("\\", "/"),
        "title": title,
        "entity": {"name": title, "type": "source", "role": "原始材料"},
    }


def extract_links_from_generated(project_dir: str, generated_files: List[str]) -> List[Dict]:
    from graph import extract_wikilinks

    root = Path(project_dir)
    links = []
    for rel in generated_files:
        path = root / rel
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        source = path.stem
        for target in extract_wikilinks(content):
            links.append({"from": source, "to": target})
    return links


def _ingest_runtime_config(project_dir: str) -> Dict:
    """读取 ingest 段配置，给默认值。"""
    try:
        from config_store import load_config

        section = load_config(os.path.join(project_dir, "config", "config.yaml")).get("ingest") or {}
    except Exception:
        section = {}
    return {
        "max_workers": max(1, int(section.get("max_workers", 5))),
    }


def _process_one_file(
    project_dir: str,
    original: Dict,
    *,
    mode: str = "batch",
    reparse_context: str = "",
) -> Dict:
    """处理单个归档文件 → wiki 页面。返回标准化的结果字典。

    所有异常都在这里捕获并降级成 fallback 页面（保持原则 14 容错路径完整）。
    返回字段：file_name, generated_files[], entities[], error?, log_message, elapsed_ms
    """
    import auto_ingest as auto_ingest_module
    from file_parser import FileParseError, get_file_info, parse_file

    abs_path = Path(project_dir) / original["path"]
    file_name = original["name"]
    t0 = time.time()
    try:
        file_content = parse_file(str(abs_path))
        file_info = get_file_info(str(abs_path))
        previous_project_dir = getattr(auto_ingest_module, "PROJECT_DIR", None)
        previous_wiki_dir = getattr(auto_ingest_module, "WIKI_DIR", None)
        auto_ingest_module.PROJECT_DIR = project_dir
        auto_ingest_module.WIKI_DIR = str(Path(project_dir) / "wiki")
        try:
            result = auto_ingest_module.auto_ingest(
                str(abs_path),
                file_content,
                file_info["ext"],
                mode=mode,
                reparse_context=reparse_context,
            )
        finally:
            if previous_project_dir is not None:
                auto_ingest_module.PROJECT_DIR = previous_project_dir
            if previous_wiki_dir is not None:
                auto_ingest_module.WIKI_DIR = previous_wiki_dir

        if result.get("status") == "success" and result.get("generated_files"):
            elapsed_ms = int((time.time() - t0) * 1000)
            logger.info("file ok name=%s blocks=%d elapsed=%dms",
                        file_name, len(result["generated_files"]), elapsed_ms)
            return {
                "file_name": file_name,
                "generated_files": list(result.get("generated_files", [])),
                "entities": extract_entities_from_analysis(result.get("analysis", {})),
                "error": None,
                "log_message": f"{file_name} 已生成知识页面",
                "elapsed_ms": elapsed_ms,
            }

        message = result.get("message", "LLM 分析失败，已生成基础知识页")
        fallback = fallback_generate_wiki_page(project_dir, original, file_content, reason=message)
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.warning("file fallback name=%s reason=%s elapsed=%dms",
                       file_name, message, elapsed_ms)
        return {
            "file_name": file_name,
            "generated_files": [fallback["path"]],
            "entities": [fallback["entity"]],
            "error": message,
            "log_message": f"{file_name} 已生成基础知识页，等待精炼",
            "elapsed_ms": elapsed_ms,
        }
    except FileParseError as exc:
        fallback = fallback_generate_wiki_page(project_dir, original, "", reason=f"文档解析失败：{exc}")
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.warning("file parse_failed name=%s err=%s elapsed=%dms",
                       file_name, exc, elapsed_ms)
        return {
            "file_name": file_name,
            "generated_files": [fallback["path"]],
            "entities": [fallback["entity"]],
            "error": f"解析失败：{exc}",
            "log_message": f"{file_name} 解析失败：{exc}",
            "elapsed_ms": elapsed_ms,
        }
    except Exception as exc:
        fallback = fallback_generate_wiki_page(project_dir, original, f"[处理异常] {exc}", reason=f"处理异常：{exc}")
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.exception("file exception name=%s elapsed=%dms", file_name, elapsed_ms)
        return {
            "file_name": file_name,
            "generated_files": [fallback["path"]],
            "entities": [fallback["entity"]],
            "error": f"{exc}；已生成基础知识页",
            "log_message": f"{file_name} 处理异常，已保留基础知识页",
            "elapsed_ms": elapsed_ms,
        }


def _run_pipeline_on_archived(
    archived: List[Dict],
    batch_id: str,
    project_dir: str,
    store: IngestBatchStore,
    *,
    on_each_done: Optional[callable] = None,
    label: str = "batch",
    merge_existing: bool = False,
) -> Dict:
    """对已经在磁盘上的归档文件列表运行 ingest pipeline 核心。

    upload 流程: 先 archive_uploads → 调用本函数
    retry 流程: 直接复用现有 raw 文件 → 调用本函数

    Args:
        archived: [{name, path}, ...] path 是相对 project_dir 的 raw 文件路径
        batch_id: 已创建的 batch id
        store: IngestBatchStore
        on_each_done: 可选回调 (file_result) -> None，每个文件完成时调用
                      （用于 retry 时删除对应的 stale 页面）
        label: 仅日志用，"batch" / "retry"

    Returns: 批次 detail
    """
    from agent_status import set_status

    verify_archived_files(archived, project_dir)
    runtime = _ingest_runtime_config(project_dir)
    max_workers = min(runtime["max_workers"], max(1, len(archived)))
    total = len(archived)
    t_batch = time.time()

    existing_batch = store.get_batch(batch_id) if merge_existing else None
    generated_files: List[str] = list(existing_batch.get("generated_files") or []) if existing_batch else []
    entities: List[Dict] = list(existing_batch.get("entities") or []) if existing_batch else []
    errors: List[Dict] = []
    agg_lock = threading.Lock()
    done_counter = {"n": 0}

    def _on_done(fr: Dict) -> None:
        with agg_lock:
            done_counter["n"] += 1
            done = done_counter["n"]
            generated_files[:] = _dedupe_items(generated_files + fr["generated_files"])
            entities[:] = _dedupe_items(entities + fr["entities"])
            if fr["error"]:
                errors.append({"file": fr["file_name"], "error": fr["error"]})
            store.append_log(batch_id, fr["log_message"])
            set_status(project_dir, "processing",
                       f"已完成 {done}/{total}：{fr['file_name']}",
                       {
                           "batch_id": batch_id,
                           "done": done,
                           "total": total,
                           "elapsed_ms": fr["elapsed_ms"],
                       })
        # on_each_done 在锁外调用（可能涉及文件 IO），但因每个 future 只触发一次
        # 不会有并发竞争同一个文件
        if on_each_done is not None:
            try:
                on_each_done(fr)
            except Exception as exc:
                logger.warning("on_each_done 回调失败 file=%s: %s",
                               fr.get("file_name"), exc)

    logger.info("%s start id=%s files=%d workers=%d",
                label, batch_id, total, max_workers)

    if total == 1:
        set_status(project_dir, "processing", f"正在处理 {archived[0]['name']}",
                   {"batch_id": batch_id, "done": 0, "total": 1})
        _on_done(_process_one_file(project_dir, archived[0], mode=label, reparse_context=_reparse_context(existing_batch)))
    else:
        set_status(project_dir, "processing",
                   f"并发处理中 (0/{total}, 并发数 {max_workers})",
                   {"batch_id": batch_id, "done": 0, "total": total,
                    "max_workers": max_workers})
        with ThreadPoolExecutor(max_workers=max_workers,
                                thread_name_prefix=label) as pool:
            context = _reparse_context(existing_batch)
            futures = [pool.submit(_process_one_file, project_dir, original, mode=label, reparse_context=context)
                       for original in archived]
            for fut in as_completed(futures):
                try:
                    _on_done(fut.result())
                except Exception as exc:
                    logger.exception("%s worker 失败", label)
                    with agg_lock:
                        errors.append({"file": "?", "error": str(exc)})

    try:
        from wiki_links import ensure_bidirectional_links

        set_status(project_dir, "linking", "正在建立双向关联", {"batch_id": batch_id})
        backlink_result = ensure_bidirectional_links(project_dir, generated_files)
        if backlink_result.get("added"):
            store.append_log(batch_id, f"已补充 {backlink_result['added']} 条双向关联")
    except Exception as exc:
        logger.warning("双向链接补全失败: %s", exc)

    links = extract_links_from_generated(project_dir, generated_files)

    final_status = "completed" if not errors else "completed_with_warnings"
    detail = store.update_batch(
        batch_id,
        status=final_status,
        generated_files=generated_files,
        entities=entities,
        links=links,
        errors=errors,
    )
    elapsed_s = time.time() - t_batch
    store.append_log(batch_id, f"{label} 完成 (总耗时 {elapsed_s:.1f}s)")
    set_status(project_dir, "idle", f"{label}完成",
               {"batch_id": batch_id, "status": final_status,
                "elapsed_s": round(elapsed_s, 1),
                "total": total, "errors": len(errors)})
    logger.info("%s done id=%s status=%s elapsed=%.1fs files=%d errors=%d",
                label, batch_id, final_status, elapsed_s, total, len(errors))
    return detail


def _dedupe_items(items: List) -> List:
    seen = set()
    result = []
    for item in items:
        key = repr(sorted(item.items())) if isinstance(item, dict) else str(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _reparse_context(batch: Optional[Dict]) -> str:
    if not batch:
        return ""
    context = {
        "existing_generated_files": list(batch.get("generated_files") or [])[:80],
        "existing_entities": list(batch.get("entities") or [])[:120],
        "existing_links": list(batch.get("links") or [])[:120],
    }
    try:
        import json

        return json.dumps(context, ensure_ascii=False, indent=2)
    except Exception:
        return str(context)


def ingest_uploaded_files(
    files: Iterable,
    project_dir: str,
    store: Optional[IngestBatchStore] = None,
) -> Dict:
    """Upload → archive → (并发) wiki → backlinks → 索引 batch flow."""
    from agent_status import set_status

    files = list(files)
    store = store or default_store(project_dir)
    batch = store.create_batch([getattr(f, "filename", "upload") for f in files])
    batch_id = batch["id"]

    try:
        set_status(project_dir, "archiving", "正在保存原始材料",
                   {"batch_id": batch_id, "file_count": len(files)})
        archived = archive_uploads(files, batch_id, project_dir)
        store.update_batch(batch_id, original_files=archived)
        store.append_log(batch_id, f"已保存 {len(archived)} 个原始材料")
        return _run_pipeline_on_archived(archived, batch_id, project_dir, store, label="batch")
    except Exception as exc:
        store.update_batch(batch_id, status="failed", errors=[{"error": str(exc)}])
        set_status(project_dir, "error", f"入库失败: {exc}", {"batch_id": batch_id})
        logger.exception("batch failed id=%s", batch_id)
        raise


def reparse_batch(batch_id: str, project_dir: str, store: Optional[IngestBatchStore] = None) -> Dict:
    """Re-run ingest on a batch's archived raw files and merge with existing results."""
    store = store or default_store(project_dir)
    batch = store.get_batch(batch_id)
    if not batch:
        raise KeyError(f"Batch not found: {batch_id}")
    archived = batch.get("original_files") or []
    if not archived:
        raise ValueError("Batch has no archived raw files")
    store.update_batch(batch_id, status="running")
    store.append_log(batch_id, "开始再次解析原始材料")
    return _run_pipeline_on_archived(
        archived,
        batch_id,
        project_dir,
        store,
        label="reparse",
        merge_existing=True,
    )


# ════════════════════════════════════════════════════════════════
# Stale notes 重试：扫 wiki/notes/ 下 status: 待精炼 的 fallback 页面，
# 重新跑 auto_ingest 把它们替换成正常生成的 wiki 页面。
# ════════════════════════════════════════════════════════════════

def _read_frontmatter(text: str) -> Dict:
    """提取 YAML frontmatter 字典；失败返回 {}。"""
    import yaml as _yaml
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        return _yaml.safe_load(text[3:end]) or {}
    except _yaml.YAMLError:
        return {}


def find_stale_notes(project_dir: str) -> List[Dict]:
    """扫 wiki/notes/ 找 status: 待精炼 的 fallback 页面。

    Returns: [
      {
        "stale_path": "wiki/notes/<slug>.md",   # 相对项目根
        "source_file": "raw/sources/<batch>/<file>", # frontmatter 里的源材料
        "title": "...",
        "source_exists": True/False,
      }, ...
    ]
    """
    root = Path(project_dir)
    notes_dir = root / "wiki" / "notes"
    results: List[Dict] = []
    if not notes_dir.exists():
        return results

    for md in notes_dir.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        meta = _read_frontmatter(text)
        if str(meta.get("status") or "").strip() != "待精炼":
            continue
        source_file = str(meta.get("source_file") or "").strip()
        title = str(meta.get("title") or md.stem)
        rel = md.relative_to(root).as_posix()
        # source_file 可能是相对路径或 Windows 绝对路径
        if source_file:
            cand = Path(source_file)
            if not cand.is_absolute():
                cand = root / source_file
            source_exists = cand.exists()
        else:
            source_exists = False
        results.append({
            "stale_path": rel,
            "source_file": source_file,
            "title": title,
            "source_exists": source_exists,
        })
    return results


def retry_stale_notes(
    project_dir: str,
    *,
    stale_paths: Optional[List[str]] = None,
    delete_on_success: bool = True,
    store: Optional[IngestBatchStore] = None,
) -> Dict:
    """对 stale 页面重新跑 auto_ingest，成功后（可选地）删除 stale 页。

    Args:
        stale_paths: 指定要重试的 stale 页面路径（相对项目根，wiki/notes/...）
                     None 时重试所有 find_stale_notes() 找到的页面
        delete_on_success: 重试成功（生成 ≥1 个非 fallback 页面）后是否删除 stale 页

    Returns:
        {
          "batch_id": str,
          "total": int,
          "succeeded": int,         # 真正生成 wiki 页的（不是又一次 fallback）
          "still_stale": int,       # 重试后仍是 fallback 状态
          "deleted_stale": [...],   # 已删除的 stale 页路径
          "skipped_no_source": [...],  # 源材料丢失跳过的
          "batch_detail": {...},
        }
    """
    root = Path(project_dir)
    store = store or default_store(project_dir)

    all_stale = find_stale_notes(project_dir)
    if stale_paths is not None:
        wanted = set(stale_paths)
        candidates = [s for s in all_stale if s["stale_path"] in wanted]
    else:
        candidates = all_stale

    skipped_no_source = []
    archived: List[Dict] = []
    # path 映射：archived[i].path → 对应的 stale_path（重试成功后用于定位删除）
    archived_to_stale: Dict[str, str] = {}

    for s in candidates:
        if not s["source_exists"]:
            skipped_no_source.append(s["stale_path"])
            continue
        # archived 项的 path 是相对项目根；与 _process_one_file 的预期一致
        src = s["source_file"]
        src_path = Path(src)
        if src_path.is_absolute():
            try:
                rel_src = src_path.relative_to(root).as_posix()
            except ValueError:
                # 源在项目外（罕见），用绝对路径 _process_one_file 也能识别
                rel_src = str(src_path)
        else:
            rel_src = src_path.as_posix()
        name = src_path.name
        abs_src = src_path if src_path.is_absolute() else root / rel_src
        metadata = _raw_metadata(abs_src)
        archived.append({"name": name, "path": rel_src, **metadata})
        archived_to_stale[rel_src] = s["stale_path"]

    if not archived:
        logger.info("retry_stale_notes: 无可重试项 (candidates=%d, no_source=%d)",
                    len(candidates), len(skipped_no_source))
        return {
            "batch_id": None,
            "total": 0,
            "succeeded": 0,
            "still_stale": 0,
            "deleted_stale": [],
            "skipped_no_source": skipped_no_source,
            "batch_detail": None,
        }

    batch = store.create_batch([a["name"] for a in archived])
    batch_id = batch["id"]
    store.update_batch(batch_id, original_files=archived, kind="retry")
    store.append_log(batch_id,
                     f"重试 {len(archived)} 个 stale 页面 "
                     f"(跳过 {len(skipped_no_source)} 个源材料丢失)")
    logger.info("retry start batch_id=%s files=%d skipped=%d",
                batch_id, len(archived), len(skipped_no_source))

    deleted_stale: List[str] = []
    succeeded_count = {"n": 0}
    still_stale_count = {"n": 0}

    def _on_each(fr: Dict) -> None:
        # 判断这次重试是否真的成功（不是又一次 fallback）。
        # fallback 的 log_message 含"基础知识页"或"解析失败"或"处理异常"。
        msg = fr.get("log_message") or ""
        is_real_success = (fr.get("error") is None) and ("已生成知识页面" in msg)
        if not is_real_success:
            still_stale_count["n"] += 1
            return
        succeeded_count["n"] += 1
        if not delete_on_success:
            return
        # 通过 file_name 反查源 path → stale path
        # _process_one_file 不返回 archived 项，但 file_name 与 archived[i].name 一致
        # 多个 archived 可能同名（极少见），稳妥起见用第一个匹配
        target_stale = None
        for src_rel, stale_rel in archived_to_stale.items():
            if Path(src_rel).name == fr.get("file_name"):
                target_stale = stale_rel
                break
        if not target_stale:
            return
        stale_abs = root / target_stale
        try:
            if stale_abs.exists():
                stale_abs.unlink()
                deleted_stale.append(target_stale)
                logger.info("retry: 已删除 stale 页 %s (被新生成内容替换)", target_stale)
        except Exception as exc:
            logger.warning("retry: 删除 stale 页失败 %s: %s", target_stale, exc)

    detail = _run_pipeline_on_archived(
        archived, batch_id, project_dir, store,
        on_each_done=_on_each, label="retry",
    )
    return {
        "batch_id": batch_id,
        "total": len(archived),
        "succeeded": succeeded_count["n"],
        "still_stale": still_stale_count["n"],
        "deleted_stale": deleted_stale,
        "skipped_no_source": skipped_no_source,
        "batch_detail": detail,
    }


def rollback_batch(
    batch_id: str,
    project_dir: str,
    store: Optional[IngestBatchStore] = None,
) -> Dict:
    store = store or default_store(project_dir)
    batch = store.get_batch(batch_id)
    if not batch:
        raise KeyError(f"Batch not found: {batch_id}")

    root = Path(project_dir).resolve()
    removed = []
    for rel in batch.get("generated_files", []):
        path = (root / rel).resolve()
        if root in path.parents and path.exists() and path.is_file():
            path.unlink()
            removed.append(rel)

    detail = store.update_batch(
        batch_id,
        status="rolled_back",
        removed_files=removed,
    )
    store.append_log(batch_id, f"已回滚 {len(removed)} 个知识页面，原始材料保留")
    return detail


def migrate_legacy_wiki_pages(project_dir: str) -> None:
    root = Path(project_dir)
    mappings = {
        "cases": "cases",
        "persons": "persons",
        "locations": "locations",
        "laws": "laws",
    }
    for old_dir, new_dir in mappings.items():
        source_dir = root / old_dir
        target_dir = root / "wiki" / new_dir
        if not source_dir.exists():
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in source_dir.glob("*.md"):
            target = target_dir / source.name
            if not target.exists():
                shutil.copy2(source, target)
