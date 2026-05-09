"""Schema 合成 agent —— 把"管理目标 + 主要对象"翻译成结构化 schema YAML。

输入：
  goal:    一句话目标（如"管理我的读书笔记"）
  objects: 关键对象清单（如 ["书", "作者", "概念", "金句"]）

输出（dict，schema_runtime 可直接消费）：
  key:    "custom:<short-hash>"
  label:  人读名（基于 goal 截取）
  description
  wiki_dirs:        每个对象一个目录（slugified）
  category_labels:  目录 → 标签
  type_directory_map: 单数类型名 → 目录名
  template_type_files: 默认空（用户可后续上传）
  template_sections: 给每个类型一组通用 section
  stable_types: 等同 type_directory_map.keys()
  derived_categories: 给前端展示用的"知识卡片分类"概览（包含每类的描述）

实现：
  1. LLM 模式（cloud.llm 已配置）：调一次 LLM 产出严格 JSON
  2. Mock 模式（无 LLM key）：基于规则生成（每对象 → slug 目录 + 通用 sections）
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Dict, List, Optional

from cloud import llm as cloud_llm


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """把任意字符串变成 ascii 小写 slug；中文字符走 transliteration 不可行，
    所以中文直接用拼音不现实——退一步用 hash 后缀保证稳定唯一。
    """
    base = (text or "").strip().lower()
    ascii_part = _SLUG_RE.sub("-", base.encode("ascii", "ignore").decode("ascii")).strip("-")
    if ascii_part:
        return ascii_part[:32]
    # 全中文/Unicode → hash 化
    h = hashlib.md5(base.encode("utf-8")).hexdigest()[:8]
    return f"obj-{h}"


def _short_hash(*parts: str) -> str:
    h = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return h[:8]


SYSTEM_PROMPT = """你是知识图谱 schema 设计师。用户会给你一个管理目标和一组主要对象，你必须输出一份用于知识库（双向链接 wiki）的 schema。

严格要求：
1. 仅输出 JSON 对象（无说明、无 Markdown 代码块）。
2. 字段必须包含：key, label, description, wiki_dirs, category_labels, type_directory_map, template_type_files, template_sections, stable_types。
3. wiki_dirs 是字符串数组，元素是 ascii 小写复数目录名（如 books, authors, concepts）。
4. type_directory_map 单数类型名 → 复数目录名（如 book → books）。所有类型必须存在于 wiki_dirs 中对应目录。
5. category_labels 把每个目录映射到中文短标签（≤4 字）。
6. template_sections 给每个核心类型一组中文 section 名（4-6 个），覆盖"基本信息/关联/来源/更新记录"语义。
7. template_type_files 留空对象 {}（用户后续上传）。
8. stable_types 等于 type_directory_map 的 keys。
9. 强烈推荐至少包含 notes（笔记）和 outputs（问答记忆）两个目录。
"""


def _build_user_prompt(goal: str, objects: List[str]) -> str:
    objs = ", ".join(o.strip() for o in objects if o.strip())
    return (
        f"管理目标：{goal.strip()}\n"
        f"主要对象：{objs}\n\n"
        "请输出 schema JSON。"
    )


def _validate_and_normalize(data: Dict, goal: str, objects: List[str]) -> Optional[Dict]:
    """LLM 输出必填字段校验 + 默认补全。失败返回 None 让 caller 走 fallback。"""
    if not isinstance(data, dict):
        return None
    wiki_dirs = data.get("wiki_dirs")
    if not isinstance(wiki_dirs, list) or not all(isinstance(x, str) for x in wiki_dirs):
        return None
    type_map = data.get("type_directory_map") or {}
    if not isinstance(type_map, dict):
        return None

    # 兜底：notes / outputs
    for sub, label in (("notes", "笔记"), ("outputs", "问答记忆")):
        if sub not in wiki_dirs:
            wiki_dirs.append(sub)
        if sub not in (data.get("category_labels") or {}):
            data.setdefault("category_labels", {})[sub] = label

    # singular types for note / output
    type_map.setdefault("note", "notes")
    type_map.setdefault("output", "outputs")

    label = (data.get("label") or goal or "自定义 schema").strip()[:24]
    description = (data.get("description") or f"基于目标「{goal}」自动生成").strip()[:200]
    template_sections = data.get("template_sections") or {}
    if not isinstance(template_sections, dict):
        template_sections = {}
    return {
        "key": data.get("key") or f"custom:{_short_hash(goal, *objects)}",
        "label": label,
        "description": description,
        "wiki_dirs": list(wiki_dirs),
        "category_labels": dict(data.get("category_labels") or {}),
        "type_directory_map": type_map,
        "template_type_files": data.get("template_type_files") or {},
        "template_sections": template_sections,
        "stable_types": list(data.get("stable_types") or list(type_map.keys())),
    }


def _mock_synthesize(goal: str, objects: List[str]) -> Dict:
    """无 LLM 时的规则化生成器（仍可用，演示也跑得通）。"""
    objects = [o.strip() for o in objects if o.strip()]
    wiki_dirs: List[str] = []
    type_map: Dict[str, str] = {}
    labels: Dict[str, str] = {}
    sections: Dict[str, List[str]] = {}

    for obj in objects:
        type_name = _slugify(obj).rstrip("s") or _slugify(obj)
        dir_name = type_name + "s" if not type_name.endswith("s") else type_name
        if dir_name in wiki_dirs:
            continue
        wiki_dirs.append(dir_name)
        type_map[type_name] = dir_name
        labels[dir_name] = obj[:6]
        sections[type_name] = ["基本信息", "关联实体", "来源", "笔记", "更新记录"]

    # 兜底两个常用目录
    for sub, label in (("notes", "笔记"), ("outputs", "问答记忆")):
        if sub not in wiki_dirs:
            wiki_dirs.append(sub)
            labels[sub] = label
    type_map.setdefault("note", "notes")
    type_map.setdefault("output", "outputs")

    return {
        "key": f"custom:{_short_hash(goal, *objects)}",
        "label": (goal or "自定义 schema").strip()[:24] or "自定义 schema",
        "description": f"基于目标「{goal}」+ 对象 {objects} 自动生成（mock 模式）",
        "wiki_dirs": wiki_dirs,
        "category_labels": labels,
        "type_directory_map": type_map,
        "template_type_files": {},
        "template_sections": sections,
        "stable_types": list(type_map.keys()),
    }


def derived_categories(schema: Dict) -> List[Dict]:
    """从 schema 派生 / 知识卡片分类 / 视图（前端 maintenance / dashboard 用）。"""
    labels = schema.get("category_labels") or {}
    return [
        {"key": d, "label": labels.get(d, d), "description": ""}
        for d in (schema.get("wiki_dirs") or [])
    ]


def synthesize(goal: str, objects: List[str]) -> Dict:
    """主入口。优先 LLM，失败 fallback 到 mock。返回带 derived_categories 的 dict。"""
    objects = [o for o in (objects or []) if isinstance(o, str) and o.strip()]
    if not goal or not goal.strip():
        raise ValueError("goal 不能为空")
    if not objects:
        raise ValueError("objects 至少需要 1 项")

    schema: Optional[Dict] = None
    if cloud_llm.is_configured():
        raw = cloud_llm.chat_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(goal, objects)},
            ],
            max_tokens=2000,
            temperature=0.2,
            response_format_json=True,
        )
        if raw:
            try:
                schema = _validate_and_normalize(json.loads(raw), goal, objects)
            except (json.JSONDecodeError, TypeError):
                schema = None
    if not schema:
        schema = _mock_synthesize(goal, objects)

    return {
        "schema": schema,
        "derived_categories": derived_categories(schema),
        "source": "llm" if cloud_llm.is_configured() and schema and schema.get("key", "").startswith("custom:") and "mock" not in (schema.get("description", "")) else "mock",
    }
