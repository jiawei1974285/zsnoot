#!/usr/bin/env python3
"""Agent-owned note intake helpers."""
import os
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional


WEB_ARTICLE_EXTRACTION_GUIDE = """WEB_ARTICLE_DEEP_EXTRACTION

This source is a web article. Analyze it as structured source material.
Do not save every finding as type: note.
Extract concrete people, organizations, places, events, evidence, conclusions, crime patterns, cases, laws, techniques, and explicit relationships.

Allowed type to directory mapping:
- case -> wiki/cases/
- person -> wiki/persons/
- location -> wiki/locations/
- organization -> wiki/organizations/
- event -> wiki/events/
- evidence -> wiki/evidence/
- case_summary -> wiki/case_summaries/
- crime_pattern -> wiki/crime_patterns/
- conclusion -> wiki/conclusions/
- law -> wiki/laws/
- technique -> wiki/techniques/
- note -> wiki/notes/
- summary -> wiki/summaries/
"""


RELATION_WORDS = [
    "夫妻",
    "夫妇",
    "情侣",
    "同事",
    "朋友",
    "亲属",
    "父子",
    "母子",
    "父女",
    "母女",
    "兄弟",
    "姐妹",
    "合伙人",
    "上下级",
    "邻居",
]


def slugify_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-_ ")
    return cleaned or f"entity-{uuid.uuid4().hex[:8]}"


def extract_note_relations(content: str) -> List[Dict]:
    relation_pattern = "|".join(map(re.escape, RELATION_WORDS))
    patterns = [
        rf"(?P<a>[\u4e00-\u9fff]{{2,4}}?)\s*[和与跟同]\s*(?P<b>[\u4e00-\u9fff]{{2,4}}?)\s*是\s*(?P<relation>{relation_pattern})",
        rf"(?P<a>[\u4e00-\u9fff]{{2,4}}?)\s*与\s*(?P<b>[\u4e00-\u9fff]{{2,4}}?)\s*为\s*(?P<relation>{relation_pattern})",
        rf"(?P<a>[\u4e00-\u9fff]{{2,4}}?)\s*是\s*(?P<b>[\u4e00-\u9fff]{{2,4}}?)\s*的\s*(?P<relation>{relation_pattern})",
    ]
    relations = []
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            source = match.group("a").strip()
            target = match.group("b").strip()
            relation = match.group("relation").strip()
            if source == target:
                continue
            key = tuple(sorted([source, target]) + [relation])
            if key in seen:
                continue
            seen.add(key)
            relations.append({"source": source, "target": target, "relation": relation})
    return relations


def link_note_content(content: str, relations: List[Dict]) -> str:
    linked = content
    names = []
    for relation in relations:
        names.extend([relation["source"], relation["target"]])
    for name in sorted(set(names), key=len, reverse=True):
        slug = slugify_name(name)
        linked = re.sub(
            rf"(?<!\[\[){re.escape(name)}(?![^\[]*\]\])",
            f"[[{slug}|{name}]]",
            linked,
            count=1,
        )
    return linked


def _build_person_body(name: str, title: str, note_slug: str, relations: List[Dict]) -> str:
    lines = [f"# {name}", "", "## 关系", ""]
    for item in relations:
        other = item["target"] if item["source"] == name else item["source"]
        lines.append(f"- [[{slugify_name(other)}|{other}]]：{item['relation']}")
    lines.extend(["", "## 来源", "", f"- [[{note_slug}|{title}]]"])
    return "\n".join(lines) + "\n"


def _relpath(path: str, project_dir: str) -> str:
    return os.path.relpath(path, project_dir).replace("\\", "/")


def _dedupe_paths(paths: List[str]) -> List[str]:
    return list(dict.fromkeys(paths))


def _generated_page_slugs(paths: List[str], note_slug: str) -> List[str]:
    slugs = []
    for path in paths:
        normalized = (path or "").replace("\\", "/")
        if not normalized.startswith("wiki/") or not normalized.endswith(".md"):
            continue
        slug = os.path.splitext(os.path.basename(normalized))[0]
        if not slug or slug == note_slug:
            continue
        slugs.append(slug)
    return list(dict.fromkeys(slugs))


def _append_deep_links(note_body: str, generated_slugs: List[str]) -> str:
    if not generated_slugs:
        return note_body
    marker = "## 深度抽取实体"
    lines = ["", marker, ""]
    lines.extend(f"- [[{slug}]]" for slug in generated_slugs)
    base = note_body.split(marker, 1)[0].rstrip()
    return base + "\n" + "\n".join(lines) + "\n"


def _archive_article_source(project_dir: str, note_slug: str, title: str, content: str, source_url: str) -> Dict:
    raw_dir = os.path.join(project_dir, "raw", "web")
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, f"{note_slug}.md")
    parts = [WEB_ARTICLE_EXTRACTION_GUIDE.strip(), "", f"# {title}", ""]
    if source_url:
        parts.extend([f"Source URL: {source_url}", ""])
    parts.append(content.strip())
    raw_text = "\n".join(parts).strip() + "\n"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_text)
    return {"path": raw_path, "content": raw_text}


def deep_extract_article(project_dir: str, note_slug: str, title: str, content: str, source_url: str = "") -> Dict:
    archived = _archive_article_source(project_dir, note_slug, title, content, source_url)
    import auto_ingest as auto_ingest_module

    previous_project_dir = getattr(auto_ingest_module, "PROJECT_DIR", None)
    previous_wiki_dir = getattr(auto_ingest_module, "WIKI_DIR", None)
    auto_ingest_module.PROJECT_DIR = project_dir
    auto_ingest_module.WIKI_DIR = os.path.join(project_dir, "wiki")
    try:
        result = auto_ingest_module.auto_ingest(archived["path"], archived["content"], ".web.md")
    finally:
        if previous_project_dir is not None:
            auto_ingest_module.PROJECT_DIR = previous_project_dir
        if previous_wiki_dir is not None:
            auto_ingest_module.WIKI_DIR = previous_wiki_dir
    analysis = result.get("analysis") or {}
    return {
        "status": result.get("status", "error"),
        "message": result.get("message", ""),
        "source_path": _relpath(archived["path"], project_dir),
        "generated_files": result.get("generated_files") or [],
        "entities": analysis.get("entities") or [],
        "relations": analysis.get("relations") or [],
    }


def build_note_pages(
    project_dir: str,
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    source_url: str = "",
    deep_extract: bool = False,
) -> Dict:
    from activity_log import record
    from app import save_wiki_page, slugify
    from wiki_links import ensure_bidirectional_links

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    base_slug = slugify(f"{today}-{title}")[:72] or f"note-{now.strftime('%Y%m%d%H%M%S')}"
    note_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
    relations = extract_note_relations(content)
    linked_content = link_note_content(content, relations)

    related_slugs = sorted(
        {
            slugify_name(item["source"])
            for item in relations
        }
        | {
            slugify_name(item["target"])
            for item in relations
        }
    )

    note_body = f"# {title}\n\n{linked_content.strip()}\n"
    if source_url:
        note_body += f"\n## 来源链接\n\n- {source_url}\n"
    if relations:
        note_body += "\n## 抽取关系\n\n"
        for item in relations:
            note_body += (
                f"- [[{slugify_name(item['source'])}|{item['source']}]] 与 "
                f"[[{slugify_name(item['target'])}|{item['target']}]]：{item['relation']}\n"
            )

    note_meta = {
        "type": "note",
        "title": title,
        "tags": tags or [],
        "related": [f"[[{slug}]]" for slug in related_slugs],
        "relations": relations,
        "conflicts": [],
        "created": today,
        "updated": today,
        "source": "manual_note",
    }
    if source_url:
        note_meta["source_url"] = source_url
        note_meta["source"] = "web_note"

    generated = []
    note_path = save_wiki_page(note_slug, "notes", note_meta, note_body)
    generated.append(_relpath(note_path, project_dir))

    people = sorted({name for relation in relations for name in (relation["source"], relation["target"])})
    for name in people:
        slug = slugify_name(name)
        person_relations = [item for item in relations if item["source"] == name or item["target"] == name]
        person_meta = {
            "type": "person",
            "title": name,
            "tags": ["笔记抽取"],
            "related": sorted(
                {
                    f"[[{note_slug}]]",
                    *[
                        f"[[{slugify_name(item['target'] if item['source'] == name else item['source'])}]]"
                        for item in person_relations
                    ],
                }
            ),
            "relations": person_relations,
            "conflicts": [],
            "created": today,
            "updated": today,
            "source": "manual_note",
        }
        person_body = _build_person_body(name, title, note_slug, person_relations)
        person_path = save_wiki_page(slug, "persons", person_meta, person_body)
        generated.append(_relpath(person_path, project_dir))

    deep_result = None
    entities = []
    deep_relations = []
    if deep_extract and content.strip():
        try:
            deep_result = deep_extract_article(project_dir, note_slug, title, content, source_url)
            generated.extend(deep_result.get("generated_files") or [])
            entities.extend(deep_result.get("entities") or [])
            deep_relations.extend(deep_result.get("relations") or [])
        except Exception as exc:
            deep_result = {"status": "error", "message": str(exc)}

    generated = _dedupe_paths(generated)
    deep_slugs = _generated_page_slugs(generated, note_slug)
    if deep_slugs:
        note_meta["related"] = sorted(set(note_meta.get("related") or []) | {f"[[{slug}]]" for slug in deep_slugs})
        note_body = _append_deep_links(note_body, deep_slugs)
        save_wiki_page(note_slug, "notes", note_meta, note_body)
    ensure_bidirectional_links(project_dir, generated)
    record(
        project_dir,
        "agent_create_note",
        note_slug,
        {
            "title": title,
            "relation_count": len(relations),
            "generated_files": generated,
            "deep_extract": deep_result,
        },
    )

    return {
        "slug": note_slug,
        "title": title,
        "content": content,
        "relations": relations,
        "entities": entities,
        "deep_relations": deep_relations,
        "deep_extract": deep_result,
        "generated_files": generated,
        "created": today,
    }
