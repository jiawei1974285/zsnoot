#!/usr/bin/env python3
"""
知识图谱模块 - 从 Wiki 页面提取实体和关系
"""
import os
import re
import json
from typing import List, Dict, Tuple
from app import get_wiki_pages, get_wiki_page

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WIKI_DIR = os.path.join(PROJECT_DIR, 'wiki')


def extract_wikilinks(content: str) -> List[str]:
    """提取页面中的 wikilink"""
    links = []
    pattern = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
    matches = re.findall(pattern, content)
    for match in matches:
        target = match[0].strip()
        links.append(target)
    return links


def build_graph() -> Dict:
    """
    构建知识图谱
    
    Returns: {
        'nodes': [{'id': '...', 'label': '...', 'type': '...', 'linkCount': N}, ...],
        'edges': [{'source': '...', 'target': '...', 'weight': N}, ...],
        'communities': [{'id': N, 'name': '...', 'nodeCount': N, 'nodes': [...]}, ...]
    }
    """
    pages = get_wiki_pages()
    
    # 构建节点
    nodes = []
    node_map = {}
    
    for page in pages:
        node_id = page['slug']
        node_map[node_id] = {
            'id': node_id,
            'label': page['title'],
            'type': page['type'],
            'linkCount': 0
        }
    
    # 构建边
    edges = []
    edge_counts = {}
    
    for page in pages:
        full_page = get_wiki_page(page['slug'], page['type'])
        if not full_page:
            continue
        
        content = full_page.get('body', '')
        links = extract_wikilinks(content)
        
        for target in links:
            # 规范化 target
            target_normalized = target.lower().replace(' ', '-')
            
            # 查找匹配的节点
            target_id = None
            for nid in node_map.keys():
                if nid.lower() == target_normalized or nid.lower() == target.lower():
                    target_id = nid
                    break
            
            if target_id and target_id != page['slug']:
                edge_key = f"{page['slug']}->{target_id}"
                reverse_key = f"{target_id}->{page['slug']}"
                
                if edge_key not in edge_counts and reverse_key not in edge_counts:
                    edge_counts[edge_key] = 0
                
                edge_counts[edge_key] = edge_counts.get(edge_key, 0) + 1
                node_map[page['slug']]['linkCount'] += 1
                node_map[target_id]['linkCount'] += 1
    
    # 转换边
    for edge_key, weight in edge_counts.items():
        source, target = edge_key.split('->')
        edges.append({
            'source': source,
            'target': target,
            'weight': weight
        })
    
    # 社区检测（连通分量 + 基于边的社区发现）
    # 1. 使用并查集找连通分量
    parent = {nid: nid for nid in node_map.keys()}
    
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # 路径压缩
            x = parent[x]
        return x
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    for edge in edges:
        union(edge['source'], edge['target'])
    
    # 2. 按连通分量分组
    community_map = {}  # node_id -> community_id
    communities = {}
    
    for node_id in node_map.keys():
        root = find(node_id)
        if root not in communities:
            comm_id = len(communities)
            communities[root] = {
                'id': comm_id,
                'name': f'社区 {comm_id + 1}',
                'nodeCount': 0,
                'nodes': [],
                'centerLabel': ''
            }
        communities[root]['nodeCount'] += 1
        communities[root]['nodes'].append(node_id)
        community_map[node_id] = comm_id
    
    # 3. 为每个社区命名（取核心节点标签）
    for root, comm in communities.items():
        # 找 linkCount 最高的节点作为核心
        core_node = max(comm['nodes'], key=lambda nid: node_map[nid]['linkCount'])
        comm['centerLabel'] = node_map[core_node]['label']
        comm['name'] = f'{comm["centerLabel"]} 相关'
    
    # 4. 为每个节点添加社区 ID
    for node_id, node in node_map.items():
        node['community'] = community_map.get(node_id, 0)
    
    return {
        'nodes': list(node_map.values()),
        'edges': edges,
        'communities': list(communities.values())
    }


def merge_related_nodes(graph_data: Dict, threshold: float = 0.5) -> Dict:
    """
    合并高度关联的节点
    
    Args:
        graph_data: 原始图谱数据
        threshold: 合并阈值（基于连接密度）
    
    Returns:
        合并后的图谱数据
    """
    import copy
    merged = copy.deepcopy(graph_data)
    
    # 构建邻接表
    adj = {}
    for edge in merged['edges']:
        src, tgt = edge['source'], edge['target']
        if src not in adj:
            adj[src] = set()
        if tgt not in adj:
            adj[tgt] = set()
        adj[src].add(tgt)
        adj[tgt].add(src)
    
    # 计算节点间的连接强度
    node_map = {n['id']: n for n in merged['nodes']}
    merge_groups = []
    merged_ids = set()
    
    for node_id, neighbors in adj.items():
        if node_id in merged_ids:
            continue
        
        # 找共同邻居多的节点进行合并
        group = {node_id}
        for neighbor in neighbors:
            if neighbor in merged_ids:
                continue
            # 计算 Jaccard 相似度
            common = neighbors & adj.get(neighbor, set())
            total = neighbors | adj.get(neighbor, set())
            if len(total) > 0 and len(common) / len(total) >= threshold:
                group.add(neighbor)
        
        if len(group) > 1:
            merge_groups.append(group)
            merged_ids.update(group)
    
    # 5. 执行合并
    if merge_groups:
        new_nodes = []
        new_edges = []
        id_remap = {}  # 旧 ID -> 新 ID
        
        for group in merge_groups:
            # 创建合并节点
            group_nodes = [node_map[nid] for nid in group]
            core_node = max(group_nodes, key=lambda n: n['linkCount'])
            
            merged_label = ' + '.join([n['label'] for n in group_nodes])
            merged_id = f'_merged_{core_node["id"]}'
            
            new_node = {
                'id': merged_id,
                'label': merged_label,
                'type': core_node['type'],
                'linkCount': sum(n['linkCount'] for n in group_nodes),
                'community': core_node.get('community', 0),
                'isMerged': True,
                'members': list(group)
            }
            new_nodes.append(new_node)
            
            # 记录 ID 映射
            for nid in group:
                id_remap[nid] = merged_id
        
        # 添加未合并的节点
        for node in merged['nodes']:
            if node['id'] not in merged_ids:
                new_nodes.append(node)
        
        # 重映射边
        edge_set = set()
        for edge in merged['edges']:
            new_src = id_remap.get(edge['source'], edge['source'])
            new_tgt = id_remap.get(edge['target'], edge['target'])
            
            if new_src == new_tgt:
                continue  # 跳过自环
            
            edge_key = f"{new_src}->{new_tgt}"
            reverse_key = f"{new_tgt}->{new_src}"
            if edge_key not in edge_set and reverse_key not in edge_set:
                edge_set.add(edge_key)
                new_edges.append({
                    'source': new_src,
                    'target': new_tgt,
                    'weight': edge['weight']
                })
        
        merged['nodes'] = new_nodes
        merged['edges'] = new_edges
    
    return merged


def get_type_name(type_key: str) -> str:
    """获取类型中文名"""
    type_names = {
        'cases': '案件',
        'persons': '人物',
        'locations': '地点',
        'laws': '法规',
        'techniques': '技战法',
        'notes': '笔记',
        'summaries': '研判'
    }
    return type_names.get(type_key, type_key)


def analyze_case_similarity(case1: Dict, case2: Dict) -> Dict:
    """
    分析两个案件的相似度
    
    Returns: {
        'similarity': 0.0-1.0,
        'factors': {
            'location': 0.0-1.0,
            'method': 0.0-1.0,
            'suspect': 0.0-1.0,
            'time': 0.0-1.0
        },
        'suggestion': '串并案建议'
    }
    """
    factors = {
        'location': 0.0,
        'method': 0.0,
        'suspect': 0.0,
        'time': 0.0
    }
    
    # 提取案件内容
    content1 = case1.get('body', '')
    content2 = case2.get('body', '')
    
    # 1. 地点相似度
    location1 = extract_locations(content1)
    location2 = extract_locations(content2)
    if location1 and location2:
        if location1.lower() == location2.lower():
            factors['location'] = 1.0
        elif location1 in location2 or location2 in location1:
            factors['location'] = 0.7
    
    # 2. 作案手法相似度
    method1 = extract_method(content1)
    method2 = extract_method(content2)
    if method1 and method2:
        similarity = text_similarity(method1, method2)
        factors['method'] = similarity
    
    # 3. 嫌疑人相似度
    suspect1 = extract_suspect(content1)
    suspect2 = extract_suspect(content2)
    if suspect1 and suspect2:
        if suspect1.lower() == suspect2.lower():
            factors['suspect'] = 1.0
        else:
            factors['suspect'] = text_similarity(suspect1, suspect2)
    
    # 4. 时间相似度
    time1 = extract_date(content1)
    time2 = extract_date(content2)
    if time1 and time2:
        days_diff = abs((time1 - time2).days)
        if days_diff <= 7:
            factors['time'] = 1.0
        elif days_diff <= 30:
            factors['time'] = 0.7
        elif days_diff <= 90:
            factors['time'] = 0.4
        else:
            factors['time'] = 0.1
    
    # 计算总相似度
    weights = {
        'location': 0.3,
        'method': 0.3,
        'suspect': 0.2,
        'time': 0.2
    }
    
    similarity = sum(factors[k] * weights[k] for k in factors)
    
    # 生成建议
    suggestion = generate_suggestion(similarity, factors)
    
    return {
        'similarity': round(similarity, 3),
        'factors': {k: round(v, 3) for k, v in factors.items()},
        'suggestion': suggestion
    }


def extract_locations(content: str) -> str:
    """提取地点信息"""
    # 简单正则匹配
    patterns = [
        r'在\s*([^\s，。、]+小区)',
        r'在\s*([^\s，。、]+街道)',
        r'在\s*([^\s，。、]+路)',
        r'案发地点[：:]\s*([^\s，。、]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    
    return ''


def extract_method(content: str) -> str:
    """提取作案手法"""
    # 提取关键动词短语
    patterns = [
        r'作案手法[：:]\s*([^\n]+)',
        r'手法[：:]\s*([^\n]+)',
        r'盗窃[^\n]*',
        r'诈骗[^\n]*',
        r'抢夺[^\n]*'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(0)
    
    return ''


def extract_suspect(content: str) -> str:
    """提取嫌疑人信息"""
    patterns = [
        r'嫌疑人[：:]\s*([^\n，。]+)',
        r'嫌疑人\s*([^\n，。]{2,10})',
        r'男子[^\n，。]{2,10}',
        r'女性[^\n，。]{2,10}'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(0)
    
    return ''


def extract_date(content: str) -> 'datetime.date':
    """提取日期"""
    from datetime import datetime
    
    patterns = [
        r'(\d{4}年\d{1,2}月\d{1,2}日)',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{4}/\d{2}/\d{2})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            date_str = match.group(1)
            try:
                if '年' in date_str:
                    return datetime.strptime(date_str, '%Y年%m月%d日').date()
                elif '-' in date_str:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                elif '/' in date_str:
                    return datetime.strptime(date_str, '%Y/%m/%d').date()
            except ValueError:
                continue
    
    return None


def text_similarity(text1: str, text2: str) -> float:
    """计算文本相似度（基于字符集 Jaccard 相似度）"""
    if not text1 or not text2:
        return 0.0
    
    # 分词（简单按字符）
    chars1 = set(text1)
    chars2 = set(text2)
    
    if not chars1 or not chars2:
        return 0.0
    
    intersection = chars1 & chars2
    union = chars1 | chars2
    
    return len(intersection) / len(union) if union else 0.0


def generate_suggestion(similarity: float, factors: Dict) -> str:
    """生成串并案建议"""
    if similarity >= 0.8:
        return "高度相似，建议立即串并案侦查"
    elif similarity >= 0.6:
        return "较为相似，建议关注并进一步比对"
    elif similarity >= 0.4:
        return "部分相似，建议记录在案"
    else:
        return "相似度较低，暂无串并案必要"


def find_related_cases(case_slug: str) -> List[Dict]:
    """
    查找与指定案件相关的案件
    
    Returns: [
        {'case_slug': '...', 'case_title': '...', 'similarity': 0.0, 'factors': {...}, 'suggestion': '...'},
        ...
    ]
    """
    case_page = get_wiki_page(case_slug, 'cases')
    if not case_page:
        return []
    
    all_cases = get_wiki_pages('cases')
    related = []
    
    for other_case in all_cases:
        if other_case['slug'] == case_slug:
            continue
        
        other_page = get_wiki_page(other_case['slug'], 'cases')
        if not other_page:
            continue
        
        analysis = analyze_case_similarity(case_page, other_page)
        
        if analysis['similarity'] >= 0.3:
            related.append({
                'case_slug': other_case['slug'],
                'case_title': other_case['title'],
                'similarity': analysis['similarity'],
                'factors': analysis['factors'],
                'suggestion': analysis['suggestion']
            })
    
    # 按相似度排序
    related.sort(key=lambda x: x['similarity'], reverse=True)
    return related


def run_lint() -> Dict:
    """
    运行 Wiki 维护检查
    
    Returns: {
        'orphan_pages': [...],
        'broken_links': [...],
        'stale_pages': [...],
        'suggestions': [...]
    }
    """
    pages = get_wiki_pages()
    
    # 1. 检查孤立页面（没有入链）
    all_links = set()
    for page in pages:
        full_page = get_wiki_page(page['slug'], page['type'])
        if full_page:
            links = extract_wikilinks(full_page.get('body', ''))
            for link in links:
                all_links.add(link.lower())
    
    orphan_pages = []
    for page in pages:
        if page['slug'].lower() not in all_links and page['type'] not in ['notes']:
            orphan_pages.append({
                'slug': page['slug'],
                'title': page['title'],
                'type': page['type']
            })
    
    # 2. 检查断链
    broken_links = []
    page_slugs = set(p['slug'].lower() for p in pages)
    
    for page in pages:
        full_page = get_wiki_page(page['slug'], page['type'])
        if not full_page:
            continue
        
        links = extract_wikilinks(full_page.get('body', ''))
        for link in links:
            if link.lower() not in page_slugs:
                broken_links.append({
                    'from': page['slug'],
                    'to': link
                })
    
    # 3. 检查过期页面（超过 30 天未更新）
    from datetime import datetime, timedelta
    stale_pages = []
    threshold = datetime.now().date() - timedelta(days=30)
    
    for page in pages:
        updated = page.get('updated')
        if updated:
            try:
                if isinstance(updated, str):
                    updated_date = datetime.strptime(updated, '%Y-%m-%d').date()
                else:
                    updated_date = updated
                
                if updated_date < threshold:
                    stale_pages.append({
                        'slug': page['slug'],
                        'title': page['title'],
                        'last_updated': str(updated_date)
                    })
            except (ValueError, TypeError):
                pass
    
    return {
        'orphan_pages': orphan_pages,
        'broken_links': broken_links,
        'stale_pages': stale_pages,
        'suggestions': generate_lint_suggestions(orphan_pages, broken_links, stale_pages)
    }


def generate_lint_suggestions(orphan_pages, broken_links, stale_pages) -> List[str]:
    """生成维护建议"""
    suggestions = []
    
    if orphan_pages:
        suggestions.append(f"发现 {len(orphan_pages)} 个孤立页面，建议添加 wikilink 关联")
    
    if broken_links:
        suggestions.append(f"发现 {len(broken_links)} 个断链，建议修复或删除")
    
    if stale_pages:
        suggestions.append(f"发现 {len(stale_pages)} 个过期页面，建议更新内容")
    
    if not suggestions:
        suggestions.append("知识库状态良好，无需维护")
    
    return suggestions
