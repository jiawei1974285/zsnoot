#!/usr/bin/env python3
"""Agent-owned note intake helpers."""
import os
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional


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


def build_note_pages(project_dir: str, title: str, content: str, tags: Optional[List[str]] = None) -> Dict:
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

    generated = []
    note_path = save_wiki_page(note_slug, "notes", note_meta, note_body)
    generated.append(os.path.relpath(note_path, project_dir).replace("\\", "/"))

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
        generated.append(os.path.relpath(person_path, project_dir).replace("\\", "/"))

    ensure_bidirectional_links(project_dir, generated)
    record(
        project_dir,
        "agent_create_note",
        note_slug,
        {
            "title": title,
            "relation_count": len(relations),
            "generated_files": generated,
        },
    )

    return {
        "slug": note_slug,
        "title": title,
        "content": content,
        "relations": relations,
        "generated_files": generated,
        "created": today,
    }
