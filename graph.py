#!/usr/bin/env python3
"""Knowledge graph helpers."""
import copy
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List

from app import WIKI_DIR, get_wiki_subdirs, parse_frontmatter


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_GRAPH_CACHE = {"signature": None, "graph": None}


def extract_wikilinks(content: str) -> List[str]:
    pattern = r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]"
    return [match[0].strip() for match in re.findall(pattern, content)]


def _list_wiki_files() -> List[Path]:
    files = []
    for subdir in get_wiki_subdirs():
        directory = Path(WIKI_DIR) / subdir
        if directory.exists():
            files.extend(sorted(directory.glob("*.md")))
    return files


def _graph_signature() -> tuple:
    signature = []
    for path in _list_wiki_files():
        stat = path.stat()
        signature.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(signature)


def _normalize_slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^\w\u4e00-\u9fff-]+", "-", (value or "").strip())).strip("-_ ").lower()


def _load_pages() -> List[Dict]:
    pages = []
    for path in _list_wiki_files():
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        meta, body = parse_frontmatter(content)
        pages.append(
            {
                "slug": path.stem,
                "type": path.parent.name,
                "title": meta.get("title", path.stem),
                "meta": meta,
                "body": body or "",
            }
        )
    return pages


def build_graph(force_refresh: bool = False) -> Dict:
    """
    Build knowledge graph data from wiki pages.

    Returns:
        {
            "nodes": [...],
            "edges": [...],
            "communities": [...],
        }
    """
    signature = _graph_signature()
    if not force_refresh and _GRAPH_CACHE["signature"] == signature and _GRAPH_CACHE["graph"] is not None:
        return copy.deepcopy(_GRAPH_CACHE["graph"])

    pages = _load_pages()
    slug_lookup = {page["slug"].lower(): page["slug"] for page in pages}
    title_lookup = {_normalize_slug(page["title"]): page["slug"] for page in pages}

    node_map = {}
    for page in pages:
        node_map[page["slug"]] = {
            "id": page["slug"],
            "label": page["title"],
            "type": page["type"],
            "linkCount": 0,
        }

    edge_map = {}

    def ensure_edge(source: str, target: str, relation: str = "", weight: int = 1):
        if source == target or source not in node_map or target not in node_map:
            return
        ordered = tuple(sorted([source, target]))
        edge = edge_map.setdefault(
            ordered,
            {
                "source": ordered[0],
                "target": ordered[1],
                "weight": 0,
                "relation": relation or "",
                "kind": "relation" if relation else "wikilink",
            },
        )
        edge["weight"] += weight
        if relation and not edge.get("relation"):
            edge["relation"] = relation
            edge["kind"] = "relation"
        node_map[source]["linkCount"] += weight
        node_map[target]["linkCount"] += weight

    def resolve_target(raw_target: str) -> str | None:
        target = (raw_target or "").strip()
        if not target:
            return None
        lowered = target.lower()
        normalized = _normalize_slug(target)
        return slug_lookup.get(lowered) or title_lookup.get(normalized) or slug_lookup.get(normalized)

    for page in pages:
        for target in extract_wikilinks(page["body"]):
            target_slug = resolve_target(target)
            if target_slug:
                ensure_edge(page["slug"], target_slug)

        for relation in page["meta"].get("relations", []) or []:
            source_slug = resolve_target(relation.get("source"))
            target_slug = resolve_target(relation.get("target"))
            ensure_edge(source_slug, target_slug, relation.get("relation", ""), weight=2)

    parent = {node_id: node_id for node_id in node_map.keys()}

    def find(node_id: str) -> str:
        while parent[node_id] != node_id:
            parent[node_id] = parent[parent[node_id]]
            node_id = parent[node_id]
        return node_id

    def union(left: str, right: str):
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_left] = root_right

    for edge in edge_map.values():
        union(edge["source"], edge["target"])

    communities = {}
    for node_id in node_map.keys():
        root = find(node_id)
        if root not in communities:
            community_id = len(communities)
            communities[root] = {
                "id": community_id,
                "name": f"社区 {community_id + 1}",
                "nodeCount": 0,
                "nodes": [],
                "centerLabel": "",
            }
        communities[root]["nodeCount"] += 1
        communities[root]["nodes"].append(node_id)

    for root, community in communities.items():
        core_node = max(community["nodes"], key=lambda node_id: node_map[node_id]["linkCount"])
        community["centerLabel"] = node_map[core_node]["label"]
        community["name"] = f"{community['centerLabel']} 相关"
        for node_id in community["nodes"]:
            node_map[node_id]["community"] = community["id"]

    graph_data = {
        "nodes": list(node_map.values()),
        "edges": list(edge_map.values()),
        "communities": list(communities.values()),
    }
    _GRAPH_CACHE["signature"] = signature
    _GRAPH_CACHE["graph"] = copy.deepcopy(graph_data)
    return graph_data


def _resolve_page_target(raw_target: str, slug_lookup: Dict[str, str], title_lookup: Dict[str, str]) -> str | None:
    target = (raw_target or "").strip()
    if not target:
        return None
    lowered = target.lower()
    normalized = _normalize_slug(target)
    return slug_lookup.get(lowered) or title_lookup.get(normalized) or slug_lookup.get(normalized)


def _coerce_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


def run_lint(stale_after_days: int = 180) -> Dict:
    """Inspect wiki pages for broken links, orphan pages, and stale content."""
    pages = _load_pages()
    slug_lookup = {page["slug"].lower(): page["slug"] for page in pages}
    title_lookup = {_normalize_slug(page["title"]): page["slug"] for page in pages}
    page_by_slug = {page["slug"]: page for page in pages}

    broken_links = []
    linked_slugs = set()
    pages_with_any_link = set()

    for page in pages:
        for target in extract_wikilinks(page["body"]):
            pages_with_any_link.add(page["slug"])
            target_slug = _resolve_page_target(target, slug_lookup, title_lookup)
            if target_slug:
                linked_slugs.add(target_slug)
            else:
                broken_links.append({"from": page["slug"], "to": target})

        for relation in page["meta"].get("relations", []) or []:
            source_slug = _resolve_page_target(relation.get("source"), slug_lookup, title_lookup)
            target_slug = _resolve_page_target(relation.get("target"), slug_lookup, title_lookup)
            if source_slug:
                pages_with_any_link.add(source_slug)
                linked_slugs.add(source_slug)
            if target_slug:
                pages_with_any_link.add(target_slug)
                linked_slugs.add(target_slug)

    orphan_pages = []
    for page in pages:
        if page["meta"].get("standalone"):
            continue
        if page["slug"] not in linked_slugs and page["slug"] not in pages_with_any_link:
            orphan_pages.append({"slug": page["slug"], "type": page["type"], "title": page["title"]})

    cutoff = date.today() - timedelta(days=stale_after_days)
    stale_pages = []
    placeholder_pages = []
    for page in pages:
        meta = page["meta"]
        # 占位页（orphan_detector 自动建的、frontmatter 含 placeholder: true）
        if meta.get("placeholder"):
            placeholder_pages.append({
                "slug": page["slug"],
                "type": page["type"],
                "title": page["title"],
                "tags": meta.get("tags", []),
            })
            # 占位页本身不算 stale（即便长时间没更新），它是已知"待补"
            continue
        if meta.get("standalone"):
            continue
        updated = _coerce_date(meta.get("updated") or meta.get("created"))
        if updated and updated < cutoff:
            stale_pages.append({
                "slug": page["slug"],
                "type": page["type"],
                "title": page["title"],
                "updated": updated.isoformat(),
            })

    suggestions = []
    if broken_links:
        suggestions.append(f"发现 {len(broken_links)} 条断链（指向不存在的页），可删除链接或一键建占位页。")
    if orphan_pages:
        suggestions.append(f"发现 {len(orphan_pages)} 个孤立页面（无人引用、自身也无外联），可补充关联或标记独立。")
    if stale_pages:
        suggestions.append(f"发现 {len(stale_pages)} 个长期未更新页面（>{stale_after_days} 天），可确认或刷新。")
    if placeholder_pages:
        suggestions.append(f"发现 {len(placeholder_pages)} 个占位页（自动生成、待补充），可一键 LLM 补全或确认存档。")
    if not suggestions:
        suggestions.append("知识库体检通过，暂未发现需要处理的问题。")

    # 健康度公式：100 - 各类问题的加权扣分
    # 权重：断链 3 / 孤立 1 / 过期 0.5 / 占位 1.5；除以总页数（最少 1）
    total_pages = max(len(page_by_slug), 1)
    weighted = (
        len(broken_links) * 3
        + len(orphan_pages) * 1
        + len(stale_pages) * 0.5
        + len(placeholder_pages) * 1.5
    )
    health_score = max(0, min(100, round(100 - weighted * 100 / total_pages)))

    return {
        "broken_links": broken_links,
        "orphan_pages": orphan_pages,
        "stale_pages": stale_pages,
        "placeholder_pages": placeholder_pages,
        "suggestions": suggestions,
        "health_score": health_score,
        "summary": {
            "pages": len(page_by_slug),
            "broken_links": len(broken_links),
            "orphan_pages": len(orphan_pages),
            "stale_pages": len(stale_pages),
            "placeholder_pages": len(placeholder_pages),
            "health_score": health_score,
            "formula": "100 - (断链*3 + 孤立*1 + 过期*0.5 + 占位*1.5) * 100 / 总页数",
        },
    }


def merge_related_nodes(graph_data: Dict, threshold: float = 0.5) -> Dict:
    """Merge highly similar nodes for a compact graph view."""
    merged = copy.deepcopy(graph_data)
    adjacency = {}
    for edge in merged["edges"]:
        source, target = edge["source"], edge["target"]
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)

    node_map = {node["id"]: node for node in merged["nodes"]}
    merge_groups = []
    merged_ids = set()

    for node_id, neighbors in adjacency.items():
        if node_id in merged_ids:
            continue
        group = {node_id}
        for neighbor in neighbors:
            if neighbor in merged_ids:
                continue
            common = neighbors & adjacency.get(neighbor, set())
            total = neighbors | adjacency.get(neighbor, set())
            if total and len(common) / len(total) >= threshold:
                group.add(neighbor)
        if len(group) > 1:
            merge_groups.append(group)
            merged_ids.update(group)

    if not merge_groups:
        return merged

    new_nodes = []
    new_edges = []
    id_remap = {}

    for group in merge_groups:
        group_nodes = [node_map[node_id] for node_id in group]
        core_node = max(group_nodes, key=lambda node: node["linkCount"])
        merged_id = f"_merged_{core_node['id']}"
        new_nodes.append(
            {
                "id": merged_id,
                "label": " + ".join(node["label"] for node in group_nodes),
                "type": core_node["type"],
                "linkCount": sum(node["linkCount"] for node in group_nodes),
                "community": core_node.get("community", 0),
                "isMerged": True,
                "members": list(group),
            }
        )
        for node_id in group:
            id_remap[node_id] = merged_id

    for node in merged["nodes"]:
        if node["id"] not in merged_ids:
            new_nodes.append(node)

    seen_edges = set()
    for edge in merged["edges"]:
        new_source = id_remap.get(edge["source"], edge["source"])
        new_target = id_remap.get(edge["target"], edge["target"])
        if new_source == new_target:
            continue
        edge_key = tuple(sorted([new_source, new_target]))
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        new_edges.append(
            {
                "source": edge_key[0],
                "target": edge_key[1],
                "weight": edge["weight"],
                "relation": edge.get("relation", ""),
                "kind": edge.get("kind", "wikilink"),
            }
        )

    merged["nodes"] = new_nodes
    merged["edges"] = new_edges
    return merged


def find_related_cases(case_slug: str) -> List[Dict]:
    """Return case pages directly connected to a case in the knowledge graph."""
    target_slug = (case_slug or "").strip()
    if not target_slug:
        return []

    graph_data = build_graph()
    nodes_by_id = {node["id"]: node for node in graph_data.get("nodes", [])}
    if target_slug not in nodes_by_id:
        return []

    related = {}
    for edge in graph_data.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if source == target_slug:
            other = target
        elif target == target_slug:
            other = source
        else:
            continue

        node = nodes_by_id.get(other)
        if not node or node.get("type") != "cases":
            continue
        item = related.setdefault(
            other,
            {
                "slug": other,
                "title": node.get("label") or other,
                "type": node.get("type"),
                "relation_count": 0,
                "weight": 0,
                "relations": [],
            },
        )
        item["relation_count"] += 1
        item["weight"] += int(edge.get("weight") or 1)
        if edge.get("relation"):
            item["relations"].append(edge["relation"])

    return sorted(
        related.values(),
        key=lambda item: (-item["weight"], item["title"]),
    )
