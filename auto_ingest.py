#!/usr/bin/env python3
"""
自动摄入模块 - 文件 → LLM 分析 → 生成 Wiki 页面
支持：笔录、话单、资金流水、文件、工作日志等

调用模式（受 config.yaml ingest.single_call 控制，默认 True）：
  - single_call=True : 一次 LLM 调用直接产出 FILE blocks（实测砍掉 ~50% 单文件耗时）
  - single_call=False: 旧的 2 次调用（analyze 然后 generate），保留作为 fallback
"""
import os
import re
import json
import time
import yaml
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from llm_client import chat_completion
from mjq_logging import get_logger

logger = get_logger(__name__)

# P2-B：数据路径从 user_data 解析（绑定时 ~/.handynotes/<user>/，未绑定时 install_dir）
# 老调用方传递的 PROJECT_DIR/WIKI_DIR 仍以本模块常量为准；note_intake.py 中的运行时 swap 也可正常工作。
try:
    from user_data import get_user_data_dir as _resolve_data_dir
    PROJECT_DIR = _resolve_data_dir()
except Exception:  # 防御性：user_data 未就绪时退回 install dir
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WIKI_DIR = os.path.join(PROJECT_DIR, 'wiki')

# ─── P2 起：以下 4 个映射改为从 schema_runtime 读取（按 schema.yaml 决定） ──
# 保留同名常量作为兼容入口（== 警务模板默认值），原有外部代码 / tests 仍可读到合理结果。
# 真正的运行时映射统一走 _runtime() 解析，自动按当前用户 schema 切换。
def _runtime():
    from schema_runtime import current_runtime
    return current_runtime()


INTELLIGENCE_TYPE_DIRS = {
    'case': 'cases',
    'person': 'persons',
    'location': 'locations',
    'law': 'laws',
    'technique': 'techniques',
    'note': 'notes',
    'summary': 'summaries',
    'output': 'outputs',
    'organization': 'organizations',
    'event': 'events',
    'evidence': 'evidence',
    'case_summary': 'case_summaries',
    'crime_pattern': 'crime_patterns',
    'conclusion': 'conclusions',
}

TEMPLATE_TYPE_FILES = {
    'person': 'persons.md',
    'event': 'events.md',
    'evidence': 'evidence.md',
    'conclusion': 'conclusions.md',
}

DEFAULT_TEMPLATE_SECTIONS = {
    'person': ['关联案件', '关联实体', '来源与证据', '更新记录'],
    'event': ['基本事实', '关联案件', '关联实体', '来源与证据', '更新记录'],
    'evidence': ['证据概况', '证明对象', '关联实体', '来源与证据', '更新记录'],
    'conclusion': ['结论', '依据', '可信度', '建议动作', '来源与证据', '更新记录'],
}


def load_agent_config() -> Dict:
    try:
        from config_store import load_config
        return load_config(os.path.join(PROJECT_DIR, 'config', 'config.yaml'))
    except Exception:
        return {}


def custom_category_map() -> Dict[str, str]:
    config = load_agent_config()
    runtime_type_dirs = _runtime().type_directory_map
    result = {}
    for item in config.get('wiki', {}).get('custom_categories', []) or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get('key') or item.get('name') or '').strip().lower()
        label = str(item.get('label') or item.get('name') or key).strip()
        if key in runtime_type_dirs:
            continue
        if key:
            result[key] = label
    return result


def type_directory_policy_text() -> str:
    runtime = _runtime()
    type_dirs = runtime.type_directory_map
    stable_types = runtime.stable_types or list(type_dirs.keys())
    lines = ["Type-directory rules:"]
    for page_type in stable_types:
        target = type_dirs.get(page_type)
        if not target:
            continue
        lines.append(f"- {page_type} -> wiki/{target}/")
    for page_type, label in custom_category_map().items():
        lines.append(f"- {page_type} -> wiki/{page_type}/ ({label})")
    lines.extend([
        "- The YAML frontmatter `type` must match the page path directory.",
        "- Do not use type: note as a fallback when the material contains people, organizations, events, evidence, locations, patterns, or conclusions.",
        "- For web articles, split concrete facts into classified entity/event/evidence/conclusion pages; keep a note page only for the original article summary when useful.",
    ])
    return "\n".join(lines)


def material_specific_policy(file_type: str) -> str:
    if (file_type or '').lower() != '.web.md':
        return ""
    return """## Web article extraction rules

This material came from a web article or WeChat Official Account page.
- Treat it as source material, not merely as a diary note.
- Extract all named people, organizations, places, events, evidence items, conclusions, crime patterns, cases, laws, and techniques supported by the article.
- Create separate Wiki pages with precise `type` values and correct directories.
- Do not save every finding as type: note.
- Preserve the source URL and article title in source/evidence sections when present.

Allowed type to directory mapping:
{type_policy}
""".format(type_policy=type_directory_policy_text())


def enabled_skills_text() -> str:
    config = load_agent_config()
    skills = config.get('agent', {}).get('skills', []) or []
    enabled = [item for item in skills if isinstance(item, dict) and item.get('enabled', True)]
    if not enabled:
        return '未配置额外技能。'
    lines = []
    for item in enabled:
        name = item.get('name') or '未命名技能'
        desc = item.get('description') or ''
        trigger = item.get('trigger') or ''
        lines.append(f"- {name}: {desc} 触发条件: {trigger}")
    return "\n".join(lines)


def model_role_hint(file_type: str) -> str:
    ext = (file_type or '').lower()
    if ext in {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}:
        return '当前材料为图片，优先考虑 OCR 模型提取文字；如需理解画面、票据、截图结构，可使用视觉模型。'
    if ext == '.pdf':
        return '当前材料为 PDF。如正文解析为空或疑似扫描件，优先考虑 OCR 模型；普通文本 PDF 使用文本模型。'
    if ext == '.web.md':
        return '当前材料为网页/微信公众号文章正文，优先使用文本模型；重点抽取文章中的实体、关系、事件、证据和结论，并按类型生成知识页。'
    return '当前材料已解析为文本，优先使用文本模型；只有遇到图片语义或 OCR 需求时再切换模型。'


CONFLICT_POLICY = """
## Conflict policy

If sources disagree about identity, time, location, amount, role, or case facts, do not silently merge them.
Every affected page must include `conflicts: []` in frontmatter when there is no disagreement.
When there is disagreement, include `conflicts: [...]` in frontmatter and a `## Conflicts` section listing each claim, source, and unresolved/resolved status.
"""


REPARSE_DEEPENING_POLICY = """
## 再次解析补充模式

这是对同一份材料的再次解析，不要只复刻上一次的概要。
请把下面的历史结果当作已知上下文，重点补充遗漏信息：
- 逐页细读原文，尽量抽取此前遗漏的人物、地点、组织、事件、证据、结论、案件摘要和关系。
- 对同名实体输出同一路径页面，补充新的 tags、related、relations 和正文事实；系统会与历史页面合并。
- 如果历史结果里已经有某个实体，请优先寻找它的新关系、时间、地点、角色、证据来源和冲突信息。
- 如果原文支持新的实体或关系，请创建新的 wiki 页面；没有新增事实时，也要在已有页面中补充更细的证据描述。

## 历史已生成结果
{reparse_context}
"""


def reparse_policy_text(reparse_context: str = "") -> str:
    context = (reparse_context or "").strip()
    if not context:
        return ""
    return REPARSE_DEEPENING_POLICY.format(reparse_context=context)


def normalize_generated_file_path(block: Dict) -> str:
    """Route generated pages by frontmatter type into stable wiki directories."""
    rel_path = (block.get('path') or '').strip().replace('\\', '/')
    if not rel_path.startswith('wiki/'):
        rel_path = f'wiki/{rel_path}'

    meta = block.get('meta') or {}
    page_type = str(meta.get('type') or '').strip().lower()
    type_dirs = _runtime().type_directory_map
    target_dir = type_dirs.get(page_type) or (page_type if page_type in custom_category_map() else None)
    if not target_dir:
        return rel_path

    filename = os.path.basename(rel_path)
    if not filename:
        title = str(meta.get('title') or page_type or 'untitled')
        filename = f"{title}.md"
    if not filename.endswith('.md'):
        filename = f"{filename}.md"
    return f"wiki/{target_dir}/{filename}"


def _template_sections_from_file(page_type: str) -> List[str]:
    runtime = _runtime()
    template_name = runtime.template_type_files.get(page_type)
    fallback = runtime.template_sections.get(page_type) or []
    if not template_name:
        return list(fallback)
    # 优先用户 wiki/templates/，找不到再回退到 install_dir/wiki/templates/（种子模板）
    template_path = os.path.join(WIKI_DIR, 'templates', template_name)
    if not os.path.exists(template_path):
        try:
            from user_data import get_install_wiki_templates_dir
            seed = os.path.join(get_install_wiki_templates_dir(), template_name)
            if os.path.exists(seed):
                template_path = seed
            else:
                return list(fallback)
        except Exception:
            return list(fallback)
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    sections = re.findall(r'^##\s+(.+?)\s*$', template, re.MULTILINE)
    return sections or list(fallback)


def apply_intelligence_template(block: Dict) -> str:
    """Ensure core intelligence pages keep canonical investigation sections."""
    content = block.get('content') or ''
    meta = block.get('meta') or {}
    page_type = str(meta.get('type') or '').strip().lower()
    sections = _template_sections_from_file(page_type)
    if not sections:
        return content

    additions = []
    for section in sections:
        if not re.search(rf'^##\s+{re.escape(section)}\s*$', content, re.MULTILINE):
            additions.append(f"## {section}\n\n待补充\n")
    if not additions:
        return content
    return content.rstrip() + "\n\n" + "\n".join(additions)


def build_analysis_prompt(schema_content: str, purpose_content: str, file_content: str, file_type: str = '', reparse_context: str = '') -> str:
    """构建分析 Prompt"""
    type_hint = f"（文件类型：{file_type}）" if file_type else ""
    custom_types = custom_category_map()
    custom_type_text = "、".join(custom_types.keys()) if custom_types else "无"
    skill_text = enabled_skills_text()
    role_hint = model_role_hint(file_type)
    
    return f"""你是一个警务知识分析助手。你的任务是分析民警提供的文件，提取关键信息并构建知识库。

## 项目规范

{schema_content}

## 项目目标

{purpose_content}

## 可用技能

{skill_text}

## 模型选择提示

{role_hint}

{CONFLICT_POLICY}

{reparse_policy_text(reparse_context)}

## 自定义页面类型

{custom_type_text}

## 分析任务

实体提取必须穷尽：
- 列出材料中所有出现的具体人物（含嫌疑人、受害人、证人、报案人、查询人、办案民警、交易对手、家属、关系人等），包括以"、"或"，"列举的成员、"某某"形式部分脱敏的姓名（如"张某"、"李某甲"）。
- 列出所有组织（公司、银行、平台、团伙等）、地点（小区、门牌号、商铺等）、数字资产/账户/物证。
- 不要因为"出现次数少"或"信息不全"就跳过。entities 数组应当尽可能完整。

请分析以下文件{type_hint}，输出 JSON 格式的分析结果：

```json
{{
  "document_type": "笔录 | 话单 | 资金流水 | 文件 | 工作日志 | 其他",
  "summary": "文件摘要",
  "entities": [
    {{
      "name": "实体名称",
      "type": "person | location | case | law | technique | organization | event | evidence | case_summary | crime_pattern | conclusion | {custom_type_text} | other",
      "description": "简要描述",
      "role": "角色（如：嫌疑人、受害人、证人等）",
      "details": "详细信息"
    }}
  ],
  "key_facts": ["关键事实 1", "关键事实 2"],
  "case_info": {{
    "case_type": "案件类型",
    "status": "案件状态",
    "date": "日期",
    "location": "地点"
  }},
  "suggested_pages": [
    {{
      "title": "建议创建的 Wiki 页面标题",
      "type": "case | person | location | organization | event | evidence | case_summary | crime_pattern | conclusion | law | technique | note | summary | {custom_type_text}",
      "reason": "创建理由"
    }}
  ],
  "related_topics": ["相关主题 1"]
}}
```

## 待分析文件

{file_content}

请输出分析结果（只输出 JSON，不要其他内容）：
"""


def build_generation_prompt(schema_content: str, analysis: Dict, file_content: str, reparse_context: str = '') -> str:
    """构建生成 Prompt"""
    custom_types = custom_category_map()
    custom_type_text = "、".join(custom_types.keys()) if custom_types else "无"
    custom_dir_text = "\n".join([f"- {key}: wiki/{key}/ ({label})" for key, label in custom_types.items()]) or "无"
    type_policy = type_directory_policy_text()
    web_policy = material_specific_policy('.web.md') if 'WEB_ARTICLE_DEEP_EXTRACTION' in (file_content or '') else ''
    return f"""你是一个警务知识库生成助手。根据分析结果，生成结构化的 Wiki 页面。

## 项目规范

{schema_content}

## 分析结果

```json
{json.dumps(analysis, ensure_ascii=False, indent=2)}
```

## 原始文件内容

{file_content}

## 生成任务

根据分析结果，生成以下 Wiki 页面（使用 ---FILE: path--- 和 ---END FILE--- 分隔）：

1. **主页面**（根据 document_type 选择目录）
2. **实体页面**（人物、地点、案件等）
3. **关联页面**（法规、技战法等）

每个页面必须包含 YAML frontmatter 和 Markdown 内容。
页面 type 必须使用这些稳定类型：case、person、location、organization、event、evidence、case_summary、crime_pattern、conclusion、law、technique、note、summary。
新增类型对应目录：wiki/organizations、wiki/events、wiki/evidence、wiki/case_summaries、wiki/crime_patterns、wiki/conclusions。
自定义类型也可以使用：{custom_type_text}
自定义类型对应目录：
{custom_dir_text}

{type_policy}

{web_policy}

{CONFLICT_POLICY}

{reparse_policy_text(reparse_context)}

## 输出格式

```
---FILE: wiki/cases/2024-盗窃-小区电动车.md---
---
type: case
title: XX小区电动车盗窃案
case_type: 盗窃
status: 侦查中
tags: [盗窃，电动车]
related: []
created: 2024-03-15
updated: 2024-03-15
---
# XX小区电动车盗窃案

## 案情描述

...

## 关联

- [[XX小区]]
- [[嫌疑人 - 张某]]
---END FILE---

---FILE: wiki/persons/嫌疑人 - 张某.md---
---
type: person
title: 嫌疑人 - 张某
role: 嫌疑人
case_ref: "[[2024-盗窃-小区电动车]]"
created: 2024-03-15
updated: 2024-03-15
---
# 嫌疑人 - 张某

## 特征描述

...
---END FILE---
```

请生成所有相关页面（只输出 FILE blocks，不要其他内容）：
"""


def build_unified_prompt(schema_content: str, purpose_content: str, file_content: str, file_type: str = '', reparse_context: str = '') -> str:
    """合并版 prompt：一次调用直接产出 FILE blocks，不再先 analyze 后 generate。

    设计：把原来 build_analysis_prompt + build_generation_prompt 的指令合二为一。
    返回的内容仍然是 ---FILE: ...--- ... ---END FILE--- 格式，便于复用 parse_file_blocks。
    """
    type_hint = f"（文件类型：{file_type}）" if file_type else ""
    custom_types = custom_category_map()
    custom_type_text = "、".join(custom_types.keys()) if custom_types else "无"
    custom_dir_text = "\n".join([f"- {key}: wiki/{key}/ ({label})" for key, label in custom_types.items()]) or "无"
    skill_text = enabled_skills_text()
    role_hint = model_role_hint(file_type)
    type_policy = type_directory_policy_text()
    specific_policy = material_specific_policy(file_type)

    return f"""你是一个警务知识库构建助手。任务：分析下方材料，直接生成结构化 Wiki 页面。

## 项目规范

{schema_content}

## 项目目标

{purpose_content}

## 可用技能

{skill_text}

## 模型选择提示

{role_hint}

{CONFLICT_POLICY}

{reparse_policy_text(reparse_context)}

## 自定义页面类型

{custom_type_text}

## 生成任务

直接根据材料生成所需的 Wiki 页面，每个页面用 ---FILE: path--- 和 ---END FILE--- 包裹。
- 主页面（按 document_type 分类到合适目录）
- 实体页面（人物、地点、案件、组织、事件、证据等）
- 关联页面（法规、技战法等，按需）

## 实体抽取必须做到完整（重要）

不要只挑"显眼"的实体，必须穷尽材料中所有可识别对象，每一个独立人/组织/地点都要单独成页：
- 人物：包括嫌疑人、受害人、证人、报案人、查询人、办案民警、交易对手、家属、关系人等所有出现过的具体人名；包括以"、"或"，"等列举的成员（例："交易对手共 6 人：甲、乙、丙、丁、戊、己" → 6 个独立 person 页面，每个一个 FILE block）；包括用"某某"形式部分脱敏的姓名（如"张某"、"李某甲"）。
- 组织：所有公司、单位、派出所、银行、电商平台、群组、团伙等。
- 地点：具体小区、门牌号、商铺、银行网点、案发地点等。
- 数字资产/物证/账户：每张银行卡号、虚拟货币钱包、被盗物品等单独建页。
- 不要因为"出现次数少"或"信息不全"就跳过；信息不全的实体页可以只填 title + 来源引用，留待后续补充。

页面 type 必须使用稳定类型：case、person、location、organization、event、evidence、case_summary、crime_pattern、conclusion、law、technique、note、summary。
新增类型对应目录：wiki/organizations、wiki/events、wiki/evidence、wiki/case_summaries、wiki/crime_patterns、wiki/conclusions。
自定义类型也可使用：{custom_type_text}
自定义类型对应目录：
{custom_dir_text}

{type_policy}

{specific_policy}

## 输出格式

```
---FILE: wiki/cases/2024-盗窃-小区电动车.md---
---
type: case
title: XX小区电动车盗窃案
case_type: 盗窃
status: 侦查中
tags: [盗窃, 电动车]
related: []
created: {datetime.now().strftime('%Y-%m-%d')}
updated: {datetime.now().strftime('%Y-%m-%d')}
---
# XX小区电动车盗窃案

## 案情描述

...

## 关联

- [[XX小区]]
- [[嫌疑人 - 张某]]
---END FILE---
```

每个页面必须包含 YAML frontmatter（type/title/created/updated 必填）和 markdown 正文。
互相引用的页面使用 [[wiki-link]] 格式。

## 待分析材料{type_hint}

{file_content}

请直接输出所有 FILE blocks（不要任何额外文字、不要 JSON、不要解释）：
"""


def derive_analysis_from_blocks(blocks: List[Dict]) -> Dict:
    """从生成的 FILE blocks 中反推 analysis 字典（保持下游接口兼容）。

    原来的 analysis 主要用于 ingest_service 提取 entities。这里直接从生成页面的
    frontmatter 中提取，准确性更高（直接是落盘的事实，不是 LLM 中间猜测）。
    """
    entities = []
    page_types = set()
    for block in blocks:
        meta = block.get('meta') or {}
        page_type = str(meta.get('type') or '').strip().lower()
        title = str(meta.get('title') or '').strip()
        if not page_type or not title:
            continue
        page_types.add(page_type)
        entities.append({
            'name': title,
            'type': page_type,
            'role': str(meta.get('role') or ''),
            'description': '',
        })

    document_type = 'note'
    if 'case' in page_types:
        document_type = 'case'
    elif 'summary' in page_types or 'case_summary' in page_types:
        document_type = 'summary'

    return {
        'document_type': document_type,
        'entities': entities,
        'page_types': sorted(page_types),
    }


def parse_file_blocks(text: str) -> List[Dict]:
    """解析 LLM 生成的 FILE blocks"""
    blocks = []
    pattern = r'---\s*FILE:\s*(.+?)\s*---\n([\s\S]*?)---\s*END\s+FILE\s*---'
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    for path, content in matches:
        path = path.strip()
        content = content.strip()
        
        # 解析 frontmatter
        meta = {}
        body = content
        fm_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if fm_match:
            try:
                meta = yaml.safe_load(fm_match.group(1)) or {}
                body = fm_match.group(2).strip()
            except yaml.YAMLError:
                pass
        
        blocks.append({
            'path': path,
            'content': content,
            'meta': meta,
            'body': body
        })
    
    return blocks


def _ingest_config() -> Dict:
    """读取 config.yaml 中 ingest 段。所有键都有默认值，缺失也能跑。"""
    config = load_agent_config()
    section = config.get('ingest') or {}
    return {
        'single_call': bool(section.get('single_call', True)),
        'max_tokens': int(section.get('max_tokens', 8000)),
    }


def _read_text_file(path: str) -> str:
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content or "", re.DOTALL)
    if not match:
        return {}, content or ""
    try:
        return yaml.safe_load(match.group(1)) or {}, match.group(2)
    except yaml.YAMLError:
        return {}, content or ""


def _dedupe_list(values: List) -> List:
    seen = set()
    result = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _merge_page_content(existing: str, incoming: str) -> str:
    old_meta, old_body = parse_frontmatter(existing)
    new_meta, new_body = parse_frontmatter(incoming)
    merged_meta = {**old_meta, **new_meta}
    for key in ("tags", "related", "relations"):
        merged_meta[key] = _dedupe_list(list(old_meta.get(key) or []) + list(new_meta.get(key) or []))

    old_text = (old_body or "").strip()
    new_text = (new_body or "").strip()
    if not old_text:
        merged_body = new_text
    elif not new_text or new_text in old_text:
        merged_body = old_text
    else:
        merged_body = f"{old_text}\n\n## 再次解析补充\n\n{new_text}"

    yaml_str = yaml.dump(merged_meta, allow_unicode=True, default_flow_style=False)
    return f"---\n{yaml_str}---\n{merged_body.rstrip()}\n"


def _apply_block_meta(content: str, block_meta: Dict) -> str:
    if not block_meta:
        return content
    meta, body = parse_frontmatter(content)
    merged = {**meta, **block_meta}
    for key in ("tags", "related", "relations"):
        merged[key] = _dedupe_list(list(meta.get(key) or []) + list(block_meta.get(key) or []))
    yaml_str = yaml.dump(merged, allow_unicode=True, default_flow_style=False)
    return f"---\n{yaml_str}---\n{body.lstrip()}"


def _write_blocks_to_disk(file_blocks: List[Dict]) -> List[str]:
    """落盘 FILE blocks 并返回相对路径列表。"""
    generated_files: List[str] = []
    for block in file_blocks:
        rel_path = normalize_generated_file_path(block)
        full_path = os.path.join(PROJECT_DIR, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        content = apply_intelligence_template(block)
        content = _apply_block_meta(content, block.get('meta') or {})
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = _merge_page_content(f.read(), content)
        # 原子写：tmp 同目录写入后 os.replace，避免并发或崩溃导致半截内容
        tmp_path = f"{full_path}.tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(tmp_path, full_path)
        generated_files.append(rel_path)
        try:
            from activity_log import record
            record(PROJECT_DIR, 'agent_generate_page', rel_path, {
                'title': (block.get('meta') or {}).get('title'),
                'type': (block.get('meta') or {}).get('type'),
            })
        except Exception as exc:
            logger.warning("record agent_generate_page failed path=%s: %s", rel_path, exc)
    return generated_files


def _append_wiki_log(file_path: str, count: int) -> None:
    log_path = os.path.join(WIKI_DIR, 'log.md')
    today = datetime.now().strftime('%Y-%m-%d')
    log_entry = f"\n## {today}\n\n- 自动分析文件：{os.path.basename(file_path)}，生成 {count} 个 Wiki 页面\n"
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as exc:
        logger.warning("写 wiki/log.md 失败: %s", exc)


def _auto_ingest_single_call(file_path: str, file_content: str, file_type: str,
                             schema_content: str, purpose_content: str,
                             model_role: str, max_tokens: int,
                             reparse_context: str = "") -> Dict:
    """合并 prompt：一次 LLM 调用直接产出 FILE blocks。"""
    from agent_status import set_status

    set_status(PROJECT_DIR, 'generating',
               f'正在生成知识页面 {os.path.basename(file_path)}',
               {'model_role': model_role, 'mode': 'single_call'})
    prompt = build_unified_prompt(schema_content, purpose_content, file_content, file_type, reparse_context)
    t0 = time.time()
    text = chat_completion(
        [
            {'role': 'system', 'content': '你是警务知识库构建助手，善于把材料直接编译为结构化 markdown 页面。'},
            {'role': 'user', 'content': prompt},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
        role=model_role,
    )
    elapsed_ms = int((time.time() - t0) * 1000)
    if not text:
        logger.warning("single_call 生成失败 file=%s elapsed=%dms",
                       os.path.basename(file_path), elapsed_ms)
        return {'status': 'error', 'message': 'LLM 生成失败（single_call 模式）'}

    blocks = parse_file_blocks(text)
    if not blocks:
        logger.warning("single_call LLM 返回未识别为 FILE blocks file=%s preview=%r",
                       os.path.basename(file_path), text[:200])
        return {'status': 'error', 'message': 'LLM 输出未包含可识别的 FILE blocks'}

    generated_files = _write_blocks_to_disk(blocks)
    analysis = derive_analysis_from_blocks(blocks)
    _append_wiki_log(file_path, len(generated_files))
    logger.info("single_call ok file=%s blocks=%d elapsed=%dms",
                os.path.basename(file_path), len(generated_files), elapsed_ms)
    return {
        'status': 'success',
        'analysis': analysis,
        'generated_files': generated_files,
        'message': f'成功生成 {len(generated_files)} 个 Wiki 页面（single_call）',
    }


def _auto_ingest_two_call(file_path: str, file_content: str, file_type: str,
                          schema_content: str, purpose_content: str,
                          model_role: str, max_tokens: int,
                          reparse_context: str = "") -> Dict:
    """旧的 2 次调用流程：先 analyze 再 generate。保留作为 fallback。"""
    from agent_status import set_status

    # 步骤 1: 分析
    set_status(PROJECT_DIR, 'analyzing',
               f'正在分析 {os.path.basename(file_path)}',
               {'model_role': model_role, 'mode': 'two_call'})
    analysis_prompt = build_analysis_prompt(schema_content, purpose_content, file_content, file_type, reparse_context)
    analysis_text = chat_completion(
        [
            {'role': 'system', 'content': '你是警务知识分析助手。'},
            {'role': 'user', 'content': analysis_prompt},
        ],
        temperature=0.1,
        role=model_role,
    )
    if not analysis_text:
        return {'status': 'error', 'message': 'LLM 分析失败'}

    analysis: Dict = {}
    try:
        json_match = re.search(r'```json\s*(.*?)\s*```', analysis_text, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group(1))
        else:
            analysis = json.loads(analysis_text)
    except json.JSONDecodeError as exc:
        logger.warning("分析结果 JSON 解析失败 file=%s err=%s",
                       os.path.basename(file_path), exc)
        # 解析失败短路：直接返回错误，不再发起一次注定无效的 generate 调用
        return {'status': 'error', 'message': f'分析结果 JSON 解析失败: {exc}'}

    # 步骤 2: 生成 Wiki 页面
    set_status(PROJECT_DIR, 'generating',
               f'正在生成知识页面 {os.path.basename(file_path)}',
               {'model_role': 'llm', 'mode': 'two_call'})
    generation_prompt = build_generation_prompt(schema_content, analysis, file_content, reparse_context)
    generation_text = chat_completion(
        [
            {'role': 'system', 'content': '你是警务知识库生成助手。'},
            {'role': 'user', 'content': generation_prompt},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
        role='llm',
    )
    if not generation_text:
        return {'status': 'error', 'message': 'LLM 生成失败'}

    blocks = parse_file_blocks(generation_text)
    generated_files = _write_blocks_to_disk(blocks)
    _append_wiki_log(file_path, len(generated_files))
    return {
        'status': 'success',
        'analysis': analysis,
        'generated_files': generated_files,
        'message': f'成功生成 {len(generated_files)} 个 Wiki 页面',
    }


def auto_ingest(file_path: str, file_content: str, file_type: str = '', mode: str = "batch", reparse_context: str = '') -> Dict:
    """
    自动摄入：文件 → LLM → Wiki 页面

    根据 config.yaml 中 ingest.single_call (默认 True) 选择主路径：
      - True : 一次 LLM 调用 (build_unified_prompt)
                若 LLM 输出未包含 FILE blocks（提示词不被遵循），自动 fallback 到 two_call
      - False: 直接走两次调用 (analyze + generate)

    Returns: {'status': 'success'|'error', 'analysis': {...}, 'generated_files': [...], 'message': '...'}
    """
    cfg = _ingest_config()
    schema_content = _read_text_file(os.path.join(PROJECT_DIR, 'schema.md'))
    purpose_content = _read_text_file(os.path.join(PROJECT_DIR, 'purpose.md'))
    model_role = 'ocr_model' if file_type.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.gif'} else 'llm'
    context = reparse_context if mode == "reparse" else ""

    if cfg['single_call']:
        result = _auto_ingest_single_call(
            file_path, file_content, file_type,
            schema_content, purpose_content,
            model_role, cfg['max_tokens'],
            context,
        )
        # single_call 拿到 LLM 响应但未识别为 FILE blocks 时，提示词没被遵循；
        # 此时退到 two_call 重试一次（two_call 的 generate 阶段对格式要求更明确）。
        if (result.get('status') != 'success'
                and result.get('message') == 'LLM 输出未包含可识别的 FILE blocks'):
            logger.info("single_call 输出无 FILE blocks，回退到 two_call 重试 file=%s",
                        os.path.basename(file_path))
            return _auto_ingest_two_call(
                file_path, file_content, file_type,
                schema_content, purpose_content,
                model_role, cfg['max_tokens'],
                context,
            )
        return result
    return _auto_ingest_two_call(
        file_path, file_content, file_type,
        schema_content, purpose_content,
        model_role, cfg['max_tokens'],
        context,
    )


def enrich_wikilinks(page_content: str, existing_pages: List[Dict]) -> str:
    """
    为页面自动添加 wikilink
    
    Args:
        page_content: 页面内容
        existing_pages: 现有页面列表 [{'title': '...', 'slug': '...'}, ...]
    
    Returns:
        添加了 wikilink 的页面内容
    """
    # 构建页面索引
    index_text = '\n'.join([f"- {p['slug']}: {p.get('title', '')}" for p in existing_pages])
    
    prompt = f"""你是一个 Wiki 链接助手。请分析页面内容，找出应该链接到现有 Wiki 页面的术语。

## 现有 Wiki 页面索引

{index_text}

## 页面内容

{page_content}

## 任务

返回 JSON 格式的链接建议：

```json
{{
  "links": [
    {{"term": "页面中出现的术语", "target": "目标页面 slug"}}
  ]
}}
```

规则：
- term 必须是页面内容中 literal 出现的文本
- target 必须是索引中存在的页面 slug
- 只包含明确匹配的术语
- 只输出 JSON，不要其他内容
"""
    
    result_text = chat_completion([
        {'role': 'system', 'content': '你是 Wiki 链接助手。'},
        {'role': 'user', 'content': prompt}
    ], temperature=0.1)
    
    if not result_text:
        return page_content
    
    # 解析链接
    links = []
    try:
        json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            links = data.get('links', [])
        else:
            data = json.loads(result_text)
            links = data.get('links', [])
    except json.JSONDecodeError:
        pass
    
    # 应用链接（只替换第一次出现）
    enriched = page_content
    linked_targets = set()
    
    for link in links:
        term = link.get('term', '')
        target = link.get('target', '')
        
        if not term or not target:
            continue
        if target.lower() in linked_targets:
            continue
        
        # 查找 term 在内容中的位置（跳过 frontmatter）
        fm_end = enriched.find('\n---\n')
        search_start = fm_end + 5 if fm_end > 0 else 0
        
        idx = enriched.find(term, search_start)
        if idx == -1:
            continue
        
        # 检查是否已经在 wikilink 中
        if idx >= 2 and enriched[idx-2:idx] == '[[':
            continue
        
        # 替换
        if term.lower() == target.lower():
            replacement = f'[[{term}]]'
        else:
            replacement = f'[[{target}|{term}]]'
        
        enriched = enriched[:idx] + replacement + enriched[idx + len(term):]
        linked_targets.add(target.lower())
    
    return enriched


def batch_ingest(inbox_dir: str) -> Dict:
    """
    批量处理 inbox 文件夹中的文件
    
    Args:
        inbox_dir: inbox 文件夹路径
    
    Returns:
        处理结果统计
    """
    from file_parser import parse_file, get_file_info
    
    if not os.path.exists(inbox_dir):
        return {'status': 'error', 'message': 'inbox 文件夹不存在'}
    
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'files': []
    }
    
    for filename in os.listdir(inbox_dir):
        file_path = os.path.join(inbox_dir, filename)
        if not os.path.isfile(file_path):
            continue
        
        results['total'] += 1
        
        try:
            # 解析文件
            file_content = parse_file(file_path)
            file_info = get_file_info(file_path)
            
            # LLM 分析
            result = auto_ingest(file_path, file_content, file_info['ext'])
            
            if result['status'] == 'success':
                results['success'] += 1
                results['files'].append({
                    'file': filename,
                    'status': 'success',
                    'generated': result['generated_files']
                })
            else:
                results['failed'] += 1
                results['files'].append({
                    'file': filename,
                    'status': 'failed',
                    'error': result['message']
                })
            
        except Exception as e:
            results['failed'] += 1
            results['files'].append({
                'file': filename,
                'status': 'failed',
                'error': str(e)
            })
    
    return results


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"处理文件：{file_path}")
        
        from file_parser import parse_file
        file_content = parse_file(file_path)
        result = auto_ingest(file_path, file_content)
        
        print(f"状态：{result['status']}")
        print(f"生成文件：{result['generated_files']}")
    else:
        print("用法：python auto_ingest.py <file_path>")
