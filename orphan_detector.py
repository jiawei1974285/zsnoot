#!/usr/bin/env python3
"""孤立实体 / 孤立页面检测与自动补齐（P3）。

两类问题：
  1. dangling link  —— `[[some-slug]]` 引用的页不存在 → 自动建占位页（含反向引用）
  2. orphan page    —— 页存在但没有任何反向链接 → 标记 `orphan: true`，
                       入 wiki/index.md 的「待整理」区块；可选触发 LLM 推荐归类

设计要点（《工程控制论》原则 8 能观察 + 原则 9 反馈环 + 原则 14 兜底）：
  - 检测 read-only，与生成解耦；caller 决定是否真的写文件
  - 占位页用 frontmatter `placeholder: true` 标记，便于后续清理 / 替换
  - LLM 调用失败时退化为模板化占位（不阻塞），只是内容简陋

外部依赖：
  - wiki_links.list_wiki_files / extract_wikilinks / parse_frontmatter
  - llm_client.chat_completion（生成占位页摘要；可选）
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

from mjq_logging import get_logger
from wiki_links import (
    build_slug_map,
    collect_backlinks,
    extract_wikilinks,
    list_wiki_files,
    parse_frontmatter,
)

logger = get_logger(__name__)


# ─── 扫描 ─────────────────────────────────────────────────
def scan_links(project_dir: str) -> Dict[str, List[Dict]]:
    """一次扫描产出 dangling + orphan + 全量正向链接图（供 graph 统计复用）。

    Returns:
      {
        "dangling": [{source, target_slug, source_path}],
        "orphans":  [{slug, type, title, path}],
        "stats":    {total_pages, total_links, dangling_count, orphan_count},
      }
    """
    files = list(list_wiki_files(project_dir))
    slug_map = build_slug_map(project_dir)            # slug.lower() -> Path
    inbound: Dict[str, Set[str]] = {}                  # target_slug.lower() -> {source_slug.lower()}
    dangling: List[Dict] = []

    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = parse_frontmatter(content)
        if meta.get("placeholder"):
            # placeholder 自身被引用算 inbound 的目标，但它产出 outbound 不算
            inbound.setdefault(path.stem.lower(), set())
            continue
        source_slug = path.stem
        for target in extract_wikilinks(body):
            target_slug = target.strip().lower()
            if not target_slug:
                continue
            inbound.setdefault(target_slug, set()).add(source_slug.lower())
            if target_slug not in slug_map:
                dangling.append({
                    "source": source_slug,
                    "source_path": str(path.relative_to(Path(project_dir))).replace("\\", "/"),
                    "target_slug": target_slug,
                })

    orphans: List[Dict] = []
    for path in files:
        slug = path.stem.lower()
        if inbound.get(slug):
            continue  # 有人引用，不是孤页
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, _ = parse_frontmatter(content)
        if meta.get("placeholder"):
            continue
        orphans.append({
            "slug": path.stem,
            "type": path.parent.name,
            "title": meta.get("title", path.stem),
            "path": str(path.relative_to(Path(project_dir))).replace("\\", "/"),
        })

    return {
        "dangling": dangling,
        "orphans": orphans,
        "stats": {
            "total_pages": len(files),
            "total_links": sum(len(v) for v in inbound.values()),
            "dangling_count": len(dangling),
            "orphan_count": len(orphans),
        },
    }


# ─── 自动补齐：占位页 ──────────────────────────────────────
def _guess_type_for_slug(project_dir: str, slug: str) -> str:
    """从当前 schema 选一个目录放占位页：默认 notes（schema_runtime 兜底）。"""
    try:
        from schema_runtime import get_runtime
        wiki_dirs = get_runtime(project_dir).wiki_dirs
        if "notes" in wiki_dirs:
            return "notes"
        return wiki_dirs[0] if wiki_dirs else "notes"
    except Exception:
        return "notes"


def _llm_summary(project_dir: str, slug: str, sources: List[str]) -> Optional[str]:
    """让 LLM 给占位页写一段「这个实体可能是什么」的草稿摘要；失败 None。"""
    if not sources:
        return None
    try:
        from llm_client import chat_completion
    except Exception:
        return None
    try:
        # 收集引用上下文：每个 source 的标题 + 提及该 slug 的那一行
        context_lines = []
        for src_slug in sources[:5]:
            src_path = build_slug_map(project_dir).get(src_slug)
            if not src_path:
                continue
            try:
                src_text = src_path.read_text(encoding="utf-8")
            except OSError:
                continue
            for line in src_text.splitlines():
                if f"[[{slug}]]" in line.lower():
                    context_lines.append(f"- 来自 [[{src_slug}]]：{line.strip()[:200]}")
                    break
        if not context_lines:
            return None
        prompt = (
            f"你正在为 wiki 实体 `{slug}` 创建占位页面。\n"
            f"以下是现有页面对它的提及上下文：\n\n"
            + "\n".join(context_lines)
            + "\n\n请写一段 ≤80 字的中文草稿摘要，描述这个实体最可能是什么"
            "（人/组织/事件/地点/概念等），便于后续补全。仅输出摘要正文，不要标题。"
        )
        resp = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
        )
        if isinstance(resp, dict):
            return (resp.get("content") or "").strip() or None
        if isinstance(resp, str):
            return resp.strip() or None
    except Exception as exc:
        logger.warning(f"[orphan] LLM summary failed for {slug}: {exc}")
    return None


def create_placeholder_for_dangling(project_dir: str, target_slug: str,
                                    sources: List[str], use_llm: bool = True) -> Optional[str]:
    """为一个 dangling slug 生成占位页。返回新建文件的相对路径或 None。"""
    target_slug = (target_slug or "").strip().lower()
    if not target_slug:
        return None
    page_type = _guess_type_for_slug(project_dir, target_slug)
    page_dir = os.path.join(project_dir, "wiki", page_type)
    os.makedirs(page_dir, exist_ok=True)
    file_path = os.path.join(page_dir, f"{target_slug}.md")
    if os.path.exists(file_path):
        return None  # 已经被别的流程补上了

    title = target_slug.replace("-", " ").replace("_", " ")
    summary = _llm_summary(project_dir, target_slug, sources) if use_llm else None
    today = datetime.now().strftime("%Y-%m-%d")
    meta = {
        "type": page_type[:-1] if page_type.endswith("s") else page_type,
        "title": title,
        "placeholder": True,
        "created": today,
        "updated": today,
        "tags": ["待补充"],
    }
    body_lines = []
    if summary:
        body_lines.append(summary)
        body_lines.append("")
    body_lines.append("> **占位页**：此条目由 orphan_detector 自动生成。请补充事实信息后删除 frontmatter 的 `placeholder` 字段。")
    body_lines.append("")
    if sources:
        body_lines.append("## 反向引用")
        body_lines.append("")
        for s in sources:
            body_lines.append(f"- [[{s}]]")
        body_lines.append("")

    content = "---\n" + yaml.dump(meta, allow_unicode=True, sort_keys=False) + "---\n\n" + "\n".join(body_lines)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    rel = os.path.relpath(file_path, project_dir).replace("\\", "/")
    logger.info(f"[orphan] placeholder created: {rel}")
    return rel


def auto_fill_dangling(project_dir: str, *, use_llm: bool = True,
                       limit: Optional[int] = None) -> Dict:
    """扫一遍并补齐所有 dangling links。返回汇总。"""
    scan = scan_links(project_dir)
    by_target: Dict[str, List[str]] = {}
    for d in scan["dangling"]:
        by_target.setdefault(d["target_slug"], []).append(d["source"])

    targets = list(by_target.items())
    if limit:
        targets = targets[:int(limit)]

    created: List[str] = []
    skipped: List[str] = []
    for slug, sources in targets:
        try:
            rel = create_placeholder_for_dangling(project_dir, slug, sources, use_llm=use_llm)
            if rel:
                created.append(rel)
            else:
                skipped.append(slug)
        except Exception as exc:
            logger.warning(f"[orphan] create placeholder for {slug} failed: {exc}")
            skipped.append(slug)
    return {
        "created": created,
        "skipped": skipped,
        "remaining_dangling": max(0, len(by_target) - len(created)),
    }


# ─── 孤页：标记进 index ─────────────────────────────────────
_INDEX_ORPHANS_HEADER = "## 待整理（孤立页面）"


def mark_orphans_in_index(project_dir: str) -> Dict:
    """把当前所有 orphan 页面写入 wiki/index.md 的「待整理」区块。

    幂等：每次重写区块（先匹配 header，整段替换）。
    """
    scan = scan_links(project_dir)
    orphans = scan["orphans"]
    index_path = os.path.join(project_dir, "wiki", "index.md")
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    if not os.path.exists(index_path):
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("# 知识库索引\n\n")
    with open(index_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 构建新区块
    if orphans:
        block_lines = [_INDEX_ORPHANS_HEADER, ""]
        for o in orphans:
            block_lines.append(f"- [[{o['slug']}]] — {o.get('title') or o['slug']} (`{o['type']}`)")
        new_block = "\n".join(block_lines) + "\n"
    else:
        new_block = _INDEX_ORPHANS_HEADER + "\n\n（无孤立页面）\n"

    # 替换或追加
    pattern = re.compile(
        r"(?ms)^## 待整理（孤立页面）.*?(?=^## |\Z)"
    )
    if pattern.search(text):
        new_text = pattern.sub(new_block + "\n", text).rstrip() + "\n"
    else:
        new_text = text.rstrip() + "\n\n" + new_block

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    return {"orphan_count": len(orphans), "index_path": index_path}
