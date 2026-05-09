#!/usr/bin/env python3
"""Wiki 双向链接工具。"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml


# P2 起：WIKI_DIRS 仅作为兼容默认值（警务模板）。
# 真正的子目录列表由 schema_runtime.get_runtime(project_dir).wiki_dirs 决定，
# 见 list_wiki_files 内的解析。
WIKI_DIRS = [
    "cases",
    "persons",
    "locations",
    "organizations",
    "events",
    "evidence",
    "case_summaries",
    "crime_patterns",
    "conclusions",
    "laws",
    "techniques",
    "notes",
    "summaries",
    "outputs",
]


def extract_wikilinks(content: str) -> List[str]:
    pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
    return [match.strip() for match in re.findall(pattern, content)]


def parse_frontmatter(content: str) -> tuple[Dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    try:
        return yaml.safe_load(match.group(1)) or {}, match.group(2)
    except yaml.YAMLError:
        return {}, content


def list_wiki_files(project_dir: str) -> List[Path]:
    """按当前 schema 列出 wiki 子目录内全部 .md 文件。

    P2 起：子目录列表来自 schema_runtime（从 config/schema.yaml 读取，
    无文件则用警务默认）。老调用方零迁移成本。
    """
    try:
        from schema_runtime import get_runtime
        subdirs = get_runtime(project_dir).wiki_dirs
    except Exception:
        subdirs = WIKI_DIRS
    root = Path(project_dir) / "wiki"
    files = []
    for subdir in subdirs:
        directory = root / subdir
        if directory.exists():
            files.extend(directory.glob("*.md"))
    return files


def build_slug_map(project_dir: str) -> Dict[str, Path]:
    slug_map = {}
    for path in list_wiki_files(project_dir):
        slug_map[path.stem.lower()] = path
    return slug_map


def append_backlink(path: Path, source_slug: str) -> bool:
    content = path.read_text(encoding="utf-8")
    backlink = f"[[{source_slug}]]"
    if backlink.lower() in content.lower():
        return False

    if "## 反向关联" in content:
        updated = re.sub(r"(## 反向关联\s*\n)", rf"\1- {backlink}\n", content, count=1)
    else:
        updated = content.rstrip() + f"\n\n## 反向关联\n\n- {backlink}\n"
    path.write_text(updated, encoding="utf-8")
    return True


def ensure_bidirectional_links(project_dir: str, generated_files: List[str]) -> Dict:
    """Ensure pages linked by generated files link back to the source page."""
    root = Path(project_dir)
    slug_map = build_slug_map(project_dir)
    added = 0
    touched = []

    for rel in generated_files:
        source_path = root / rel
        if not source_path.exists():
            continue
        source_slug = source_path.stem
        content = source_path.read_text(encoding="utf-8")
        for target in extract_wikilinks(content):
            target_slug = target.strip().lower()
            target_path = slug_map.get(target_slug)
            if not target_path or target_path == source_path:
                continue
            if append_backlink(target_path, source_slug):
                added += 1
                touched.append(os.path.relpath(target_path, root).replace("\\", "/"))

    if added:
        try:
            from activity_log import record
            record(project_dir, "agent_update_backlinks", None, {
                "added": added,
                "touched": touched,
                "sources": generated_files,
            })
        except Exception:
            pass

    return {"added": added, "touched": touched}


def collect_backlinks(project_dir: str, slug: str) -> List[Dict]:
    slug_lower = slug.lower()
    backlinks = []
    for path in list_wiki_files(project_dir):
        if path.stem.lower() == slug_lower:
            continue
        content = path.read_text(encoding="utf-8")
        links = [link.lower() for link in extract_wikilinks(content)]
        if slug_lower not in links:
            continue
        meta, _ = parse_frontmatter(content)
        backlinks.append(
            {
                "slug": path.stem,
                "title": meta.get("title", path.stem),
                "type": path.parent.name,
                "path": os.path.relpath(path, Path(project_dir)).replace("\\", "/"),
            }
        )
    return backlinks
