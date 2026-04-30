#!/usr/bin/env python3
"""Agent-owned note intake helpers."""
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List


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
        rf"(?P<a>[\u4e00-\u9fff]{{2,4}})\s*(?:和|与|跟|同)\s*(?P<b>[\u4e00-\u9fff]{{2,4}})\s*(?:是|为|系)?\s*(?P<relation>{relation_pattern})",
        rf"(?P<a>[\u4e00-\u9fff]{{2,4}})\s*(?:是|为|系)\s*(?P<b>[\u4e00-\u9fff]{{2,4}})\s*的\s*(?P<relation>{relation_pattern})",
    ]
    relations = []
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            a = match.group("a").strip()
            b = match.group("b").strip()
            relation = match.group("relation").strip()
            if a == b:
                continue
            key = tuple(sorted([a, b]) + [relation])
            if key in seen:
                continue
            seen.add(key)
            relations.append({"source": a, "target": b, "relation": relation})
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


def build_note_pages(project_dir: str, title: str, content: str, tags: List[str] | None = None) -> Dict:
    from activity_log import record
    from app import save_wiki_page, slugify
    from wiki_links import ensure_bidirectional_links

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    base_slug = slugify(f"{today}-{title}")[:72] or f"note-{now}"
    note_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
    relations = extract_note_relations(content)
    linked_content = link_note_content(content, relations)
    related = sorted({slugify_name(r["source"]) for r in relations} | {slugify_name(r["target"]) for r in relations})

    note_body = f"# {title}\n\n{linked_content.strip()}\n"
    if relations:
        note_body += "\n## 抽取关系\n\n"
        for item in relations:
            note_body += f"- [[{slugify_name(item['source'])}|{item['source']}]] 与 [[{slugify_name(item['target'])}|{item['target']}]]：{item['relation']}\n"

    note_meta = {
        "type": "note",
        "title": title,
        "tags": tags or [],
        "related": [f"[[{slug}]]" for slug in related],
        "relations": relations,
        "conflicts": [],
        "created": today,
        "updated": today,
        "source": "manual_note",
    }
    generated = []
    note_path = save_wiki_page(note_slug, "notes", note_meta, note_body)
    generated.append(os.path.relpath(note_path, project_dir).replace("\\", "/"))

    for name in sorted({n for r in relations for n in (r["source"], r["target"])}):
        slug = slugify_name(name)
        person_relations = [r for r in relations if r["source"] == name or r["target"] == name]
        lines = [f"# {name}", "", "## 关系", ""]
        related_links = [f"[[{note_slug}]]"]
        for item in person_relations:
            other = item["target"] if item["source"] == name else item["source"]
            other_slug = slugify_name(other)
            lines.append(f"- [[{other_slug}|{other}]]：{item['relation']}")
            related_links.append(f"[[{other_slug}]]")
        lines.extend(["", "## 来源", "", f"- [[{note_slug}|{title}]]"])
        person_meta = {
            "type": "person",
            "title": name,
            "tags": ["笔记抽取"],
            "related": sorted(set(related_links)),
            "relations": person_relations,
            "conflicts": [],
            "created": today,
            "updated": today,
            "source": "manual_note",
        }
        person_path = save_wiki_page(slug, "persons", person_meta, "\n".join(lines) + "\n")
        generated.append(os.path.relpath(person_path, project_dir).replace("\\", "/"))

    ensure_bidirectional_links(project_dir, generated)
    record(project_dir, "agent_create_note", note_slug, {
        "title": title,
        "relation_count": len(relations),
        "generated_files": generated,
    })
    return {
        "slug": note_slug,
        "title": title,
        "content": content,
        "relations": relations,
        "generated_files": generated,
        "created": today,
    }
