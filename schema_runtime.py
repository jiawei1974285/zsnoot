#!/usr/bin/env python3
"""Schema 运行时配置 —— P2 起替代 wiki_links.WIKI_DIRS 等硬编码常量。

加载顺序：
  1. <project_dir>/config/schema.yaml （注册时由云端模板/Schema 合成 agent 写入）
  2. 默认值（原警务硬编码 → 保留作为 fallback，老部署零回归）

热更新：基于 mtime；每次 get_runtime() 检测，文件变了自动 reload。

为什么不直接写到 config.yaml：
  - schema 是结构性配置（节点类型、目录映射），生命周期与运行参数不同
  - 单独 yaml 便于云端模板/Schema 合成 agent 整文件覆盖
  - 与 schema.md（人类阅读）解耦：schema.yaml 是机器配置，schema.md 由它派生
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml


# ─── 警务模板默认值（原有硬编码，保留为 fallback） ────────────
_DEFAULT_WIKI_DIRS: List[str] = [
    "cases", "persons", "locations", "organizations", "events", "evidence",
    "case_summaries", "crime_patterns", "conclusions",
    "laws", "techniques", "notes", "summaries", "outputs",
]
_DEFAULT_CATEGORY_LABELS: Dict[str, str] = {
    "cases": "案件", "persons": "人员", "locations": "地点", "organizations": "组织",
    "events": "事件", "evidence": "证据", "case_summaries": "案件摘要",
    "crime_patterns": "犯罪模式", "conclusions": "研判结论",
    "laws": "法规", "techniques": "技战法", "notes": "笔记",
    "summaries": "研判", "outputs": "问答记忆",
}
_DEFAULT_TYPE_DIR_MAP: Dict[str, str] = {
    "case": "cases", "person": "persons", "location": "locations",
    "law": "laws", "technique": "techniques", "note": "notes",
    "summary": "summaries", "output": "outputs", "organization": "organizations",
    "event": "events", "evidence": "evidence", "case_summary": "case_summaries",
    "crime_pattern": "crime_patterns", "conclusion": "conclusions",
}
_DEFAULT_TEMPLATE_TYPE_FILES: Dict[str, str] = {
    "person": "persons.md", "event": "events.md",
    "evidence": "evidence.md", "conclusion": "conclusions.md",
}
_DEFAULT_TEMPLATE_SECTIONS: Dict[str, List[str]] = {
    "person": ["关联案件", "关联实体", "来源与证据", "更新记录"],
    "event": ["基本事实", "关联案件", "关联实体", "来源与证据", "更新记录"],
    "evidence": ["证据概况", "证明对象", "关联实体", "来源与证据", "更新记录"],
    "conclusion": ["结论", "依据", "可信度", "建议动作", "来源与证据", "更新记录"],
}


@dataclass
class SchemaRuntime:
    """已 frozen 的 schema 视图。所有字段都已展开成具体 dict/list，调用方按需使用。"""
    key: str = "police"
    label: str = "警务办案"
    wiki_dirs: List[str] = field(default_factory=lambda: list(_DEFAULT_WIKI_DIRS))
    category_labels: Dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_CATEGORY_LABELS))
    type_directory_map: Dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_TYPE_DIR_MAP))
    template_type_files: Dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_TEMPLATE_TYPE_FILES))
    template_sections: Dict[str, List[str]] = field(
        default_factory=lambda: {k: list(v) for k, v in _DEFAULT_TEMPLATE_SECTIONS.items()}
    )
    stable_types: List[str] = field(default_factory=lambda: list(_DEFAULT_TYPE_DIR_MAP.keys()))

    def is_default(self) -> bool:
        return self.key == "police" and self.wiki_dirs == _DEFAULT_WIKI_DIRS


def schema_path(project_dir: str) -> str:
    return os.path.join(project_dir, "config", "schema.yaml")


def _default_runtime() -> SchemaRuntime:
    return SchemaRuntime()


def load_runtime(project_dir: str) -> SchemaRuntime:
    """读 <project_dir>/config/schema.yaml；不存在或解析失败 → 默认值。

    YAML 格式（与云端模板对齐）：
      key: police
      label: 警务办案
      wiki_dirs: [cases, persons, ...]
      category_labels: {cases: 案件, ...}
      type_directory_map: {case: cases, ...}
      template_type_files: {person: persons.md, ...}
      template_sections:
        person: [关联案件, ...]
      stable_types: [case, person, ...]   # auto_ingest 生成 prompt 用
    """
    path = schema_path(project_dir)
    if not os.path.exists(path):
        return _default_runtime()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return _default_runtime()
    if not isinstance(data, dict):
        return _default_runtime()

    type_dir_map = dict(data.get("type_directory_map") or _DEFAULT_TYPE_DIR_MAP)
    return SchemaRuntime(
        key=str(data.get("key") or "custom"),
        label=str(data.get("label") or data.get("key") or "自定义"),
        wiki_dirs=list(data.get("wiki_dirs") or _DEFAULT_WIKI_DIRS),
        category_labels=dict(data.get("category_labels") or _DEFAULT_CATEGORY_LABELS),
        type_directory_map=type_dir_map,
        template_type_files=dict(data.get("template_type_files") or {}),
        template_sections={k: list(v) for k, v in (data.get("template_sections") or {}).items()},
        stable_types=list(data.get("stable_types") or list(type_dir_map.keys())),
    )


# ─── 缓存 + mtime 热重载 ────────────────────────────────────
_lock = threading.Lock()
_cache: Dict[str, SchemaRuntime] = {}
_cache_mtime: Dict[str, float] = {}


def get_runtime(project_dir: str) -> SchemaRuntime:
    """带缓存 + mtime 检测的 runtime 获取。线程安全。"""
    path = schema_path(project_dir)
    mtime = os.path.getmtime(path) if os.path.exists(path) else 0.0
    with _lock:
        if path in _cache and _cache_mtime.get(path) == mtime:
            return _cache[path]
        runtime = load_runtime(project_dir)
        _cache[path] = runtime
        _cache_mtime[path] = mtime
        return runtime


def invalidate(project_dir: Optional[str] = None) -> None:
    with _lock:
        if project_dir:
            path = schema_path(project_dir)
            _cache.pop(path, None)
            _cache_mtime.pop(path, None)
        else:
            _cache.clear()
            _cache_mtime.clear()


def write_schema(project_dir: str, schema: Dict) -> str:
    """把云端模板/合成 agent 产物落盘。同时使缓存失效。"""
    path = schema_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(schema, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    invalidate(project_dir)
    return path


# ─── 便捷只读访问器（给 auto_ingest 等老模块用，避免到处传 project_dir） ──
# 注意：这些会用 PROJECT_DIR 环境变量做 fallback。在 P2-B 数据目录改造前，
#       all callers still resolve to the install dir — 行为与改造前一致。
def _resolve_default_project_dir() -> str:
    return os.environ.get("MJQ_PROJECT_DIR") or os.path.dirname(os.path.abspath(__file__))


def current_runtime() -> SchemaRuntime:
    return get_runtime(_resolve_default_project_dir())
