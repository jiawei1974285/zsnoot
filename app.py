#!/usr/bin/env python3
"""
知枢 - Phase 1 升级版
功能：笔记记录 + Markdown 文件存储 + YAML frontmatter + LLM 自动组织
"""
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from typing import List, Dict
from html.parser import HTMLParser
import os
import secrets
import uuid
import hashlib
import yaml
import re
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# 启动即初始化 logging（必须在任何业务模块 import 之前）
from mjq_logging import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

# 用于 admin_required 装饰器（lazy 拿 PROJECT_DIR，避免装饰器定义时 PROJECT_DIR 还未定义的死锁）
def _project_dir():
    return PROJECT_DIR

app = Flask(__name__)

# === 路径解析（P2-B：拆分代码 vs 用户数据）===
# INSTALL_DIR = 代码安装目录（frontend/dist、jwt.secret、Flask session secret 都在这里）
# PROJECT_DIR = 用户数据目录（wiki/raw/data/config/.env 都在这里）
#   - 有绑定（machine_binding.json）时 → ~/.handynotes/<cloud_user>/
#   - 无绑定时 → INSTALL_DIR（老部署 0 迁移）
# 大量历史代码以 PROJECT_DIR 名义引用数据路径，故沿用此符号；新增 INSTALL_DIR
# 给真正"代码安装"语义的少数路径专用。
from user_data import (  # noqa: E402
    INSTALL_DIR,
    get_user_data_dir,
    current_bound_user,
)
PROJECT_DIR = get_user_data_dir()
# 当老部署没有绑定时，PROJECT_DIR == INSTALL_DIR，行为完全等价于 P2-A 之前。


# === Session secret_key ===
def _load_or_create_secret_key():
    # session secret 与 Flask 进程绑定（不是用户数据），放 INSTALL_DIR
    secret_path = os.path.join(INSTALL_DIR, 'config', 'secret.key')
    if os.path.exists(secret_path):
        with open(secret_path, 'rb') as f:
            data = f.read().strip()
            if len(data) >= 32:
                return data
    os.makedirs(os.path.dirname(secret_path), exist_ok=True)
    key = secrets.token_hex(32).encode()
    with open(secret_path, 'wb') as f:
        f.write(key)
    return key


app.secret_key = _load_or_create_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,  # 30 天
)
WIKI_DIR = os.path.join(PROJECT_DIR, 'wiki')
def get_raw_sources_dir():
    """返回 raw/sources 目录(根据 config.raw_dir 动态计算)。"""
    from config_store import get_raw_dir
    return os.path.join(get_raw_dir(PROJECT_DIR), 'sources')


# 保留 RAW_DIR 常量用于不依赖配置的简单场景(向后兼容)
RAW_DIR = os.path.join(PROJECT_DIR, 'raw', 'sources')


class WebTextExtractor(HTMLParser):
    """Extract readable text and title from simple HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.in_title = False
        self.capture_stack = []
        self.title_parts = []
        self.heading_parts = []
        self.meta_title = ''
        self.author_parts = []
        self.date_parts = []
        self.main_parts = []
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        tag = (tag or '').lower()
        attrs_dict = {str(key).lower(): str(value or '') for key, value in attrs}
        marker = _article_marker(tag, attrs_dict)
        if tag in {'script', 'style', 'noscript', 'svg', 'canvas'}:
            self.skip_depth += 1
        elif tag == 'title':
            self.in_title = True
        elif tag == 'meta':
            name = (attrs_dict.get('property') or attrs_dict.get('name') or '').lower()
            if name in {'og:title', 'twitter:title'} and attrs_dict.get('content'):
                self.meta_title = attrs_dict['content'].strip()
        tracked_tags = {'article', 'main', 'section', 'div', 'h1', 'h2', 'h3', 'span', 'p', 'li', 'tr'}
        if tag in tracked_tags:
            self.capture_stack.append(marker)
        if tag in {'p', 'div', 'article', 'section', 'br', 'li', 'h1', 'h2', 'h3', 'tr'}:
            self.text_parts.append('\n')
            if self.capture_stack:
                self._append_to_capture('\n')

    def handle_endtag(self, tag):
        tag = (tag or '').lower()
        if tag in {'script', 'style', 'noscript', 'svg', 'canvas'} and self.skip_depth:
            self.skip_depth -= 1
        elif tag == 'title':
            self.in_title = False
        elif tag in {'p', 'div', 'article', 'section', 'li', 'h1', 'h2', 'h3', 'tr'}:
            self.text_parts.append('\n')
            if self.capture_stack:
                self._append_to_capture('\n')
        if self.capture_stack and tag in {'article', 'main', 'section', 'div', 'h1', 'h2', 'h3', 'span', 'p', 'li', 'tr'}:
            self.capture_stack.pop()

    def handle_data(self, data):
        text = (data or '').strip()
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        if not self.skip_depth and not self.in_title:
            self.text_parts.append(text)
            self._append_to_capture(text)

    def _append_to_capture(self, text):
        if not self.capture_stack:
            return
        marker = next((item for item in reversed(self.capture_stack) if item), '')
        if not marker:
            return
        if marker == 'title':
            self.heading_parts.append(text)
        elif marker == 'author':
            self.author_parts.append(text)
        elif marker == 'date':
            self.date_parts.append(text)
        elif marker == 'main':
            self.main_parts.append(text)


def _article_marker(tag: str, attrs: Dict) -> str:
    element_id = (attrs.get('id') or '').lower()
    class_name = (attrs.get('class') or '').lower()
    role = (attrs.get('role') or '').lower()
    joined = f'{element_id} {class_name} {role}'
    if element_id in {'activity-name', 'js_article_title'} or 'article-title' in class_name:
        return 'title'
    if element_id in {'js_name', 'profilebt'} or 'author' in class_name:
        return 'author'
    if element_id in {'publish_time', 'js_publish_time'} or 'rich_media_meta_text' in class_name or 'time' in class_name:
        return 'date'
    if tag in {'article', 'main'} or any(token in joined for token in (
        'js_content',
        'rich_media_content',
        'article-content',
        'article_content',
        'post-content',
        'post_content',
        'entry-content',
        'entry_content',
        'content-body',
        'content_body',
        'main-content',
        'main_content',
    )):
        return 'main'
    return ''


def _clean_extracted_text(text: str) -> str:
    lines = []
    for line in re.split(r'[\r\n]+', text or ''):
        cleaned = re.sub(r'\s+', ' ', line).strip()
        if cleaned:
            lines.append(cleaned)
    return '\n'.join(lines)


def extract_web_page_text(html: str) -> Dict:
    parser = WebTextExtractor()
    parser.feed(html or '')
    title = (
        _clean_extracted_text(' '.join(parser.heading_parts))
        or _clean_extracted_text(parser.meta_title)
        or _clean_extracted_text(' '.join(parser.title_parts))
    )
    main_content = _clean_extracted_text('\n'.join(parser.main_parts))
    if main_content:
        byline = _clean_extracted_text('\n'.join([
            ' '.join(parser.author_parts),
            ' '.join(parser.date_parts),
        ]))
        content = '\n'.join(part for part in [byline, main_content] if part)
    else:
        content = _clean_extracted_text('\n'.join(parser.text_parts))
    return {'title': title, 'content': content}

# Wiki 子目录
DEFAULT_WIKI_SUBDIRS = [
    'cases',
    'persons',
    'locations',
    'organizations',
    'events',
    'evidence',
    'case_summaries',
    'crime_patterns',
    'conclusions',
    'laws',
    'techniques',
    'notes',
    'summaries',
    'outputs',
]
DEFAULT_WIKI_CATEGORY_LABELS = {
    'cases': '案件',
    'persons': '人员',
    'locations': '地点',
    'organizations': '组织',
    'events': '事件',
    'evidence': '证据',
    'case_summaries': '案件摘要',
    'crime_patterns': '犯罪模式',
    'conclusions': '研判结论',
    'laws': '法规',
    'techniques': '技战法',
    'notes': '笔记',
    'summaries': '研判',
    'outputs': '问答记忆',
}


def init_wiki():
    """初始化 Wiki 目录结构"""
    os.makedirs(WIKI_DIR, exist_ok=True)
    os.makedirs(get_raw_sources_dir(), exist_ok=True)
    for subdir in get_wiki_subdirs():
        os.makedirs(os.path.join(WIKI_DIR, subdir), exist_ok=True)
    
    # 初始化 index.md 和 log.md
    index_path = os.path.join(WIKI_DIR, 'index.md')
    log_path = os.path.join(WIKI_DIR, 'log.md')
    
    if not os.path.exists(index_path):
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("# 知枢 - 知识库索引\n\n")
            f.write("## 案件\n\n## 人物\n\n## 地点\n\n")
            f.write("## 法规\n\n## 技战法\n\n## 日常笔记\n\n## 研判总结\n")
    
    if not os.path.exists(log_path):
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("# 知识库日志\n\n")

    # 兼容早期示例目录：cases/persons/locations/laws -> wiki/*
    try:
        from ingest_service import migrate_legacy_wiki_pages
        migrate_legacy_wiki_pages(PROJECT_DIR)
    except Exception as e:
        print(f"[WARN] 示例知识页迁移失败: {e}")


def slugify(text):
    """将文本转换为 kebab-case slug"""
    # 保留中文、字母、数字
    text = re.sub(r'[^\w\u4e00-\u9fff-]', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-').lower()


def load_project_config():
    config_path = os.path.join(PROJECT_DIR, 'config', 'config.yaml')
    try:
        from config_store import load_config
        return load_config(config_path)
    except Exception:
        return {}


def get_custom_wiki_categories():
    config = load_project_config()
    raw_categories = config.get('wiki', {}).get('custom_categories', [])
    categories = []
    for item in raw_categories:
        if isinstance(item, str):
            key = slugify(item)
            label = item
        elif isinstance(item, dict):
            key = slugify(item.get('key') or item.get('name') or item.get('label') or '')
            label = item.get('label') or item.get('name') or key
        else:
            continue
        if key and key not in DEFAULT_WIKI_SUBDIRS and all(existing['key'] != key for existing in categories):
            categories.append({'key': key, 'label': label})
    return categories


def _schema_subdirs():
    """从 schema_runtime 取当前用户的 wiki 子目录；失败回退到 DEFAULT_WIKI_SUBDIRS。"""
    try:
        from schema_runtime import get_runtime
        return get_runtime(PROJECT_DIR).wiki_dirs
    except Exception:
        return DEFAULT_WIKI_SUBDIRS


def _schema_labels():
    try:
        from schema_runtime import get_runtime
        return get_runtime(PROJECT_DIR).category_labels
    except Exception:
        return DEFAULT_WIKI_CATEGORY_LABELS


def get_wiki_subdirs():
    base = _schema_subdirs()
    return list(base) + [item['key'] for item in get_custom_wiki_categories() if item['key'] not in base]


def get_wiki_category_options():
    labels = _schema_labels()
    options = [{'key': key, 'label': labels.get(key, key)} for key in _schema_subdirs()]
    options.extend(get_custom_wiki_categories())
    return options


def ensure_custom_category_dirs():
    for item in get_custom_wiki_categories():
        os.makedirs(os.path.join(WIKI_DIR, item['key']), exist_ok=True)


def update_schema_custom_categories():
    """Sync custom category documentation into schema.md."""
    # schema.md 是人读文档，与代码同寿命 → INSTALL_DIR
    schema_path = os.path.join(INSTALL_DIR, 'schema.md')
    categories = get_custom_wiki_categories()
    if not os.path.exists(schema_path):
        return
    with open(schema_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start = '<!-- CUSTOM_CATEGORIES_START -->'
    end = '<!-- CUSTOM_CATEGORIES_END -->'
    lines = [start, '', '## 自定义页面类型', '']
    if categories:
        lines.extend(['| 类型 | 目录 | 用途 |', '|------|------|------|'])
        for item in categories:
            lines.append(f"| {item['key']} | wiki/{item['key']}/ | {item['label']} |")
        lines.extend([
            '',
            '自定义类型由系统配置生成。LLM 入库时可根据材料语义选择这些类型，并将页面写入对应目录。',
            '',
            'Frontmatter `type` 允许使用以上自定义类型。',
        ])
    else:
        lines.append('暂无自定义页面类型。')
    lines.extend(['', end])
    block = '\n'.join(lines)

    pattern = re.compile(r'<!-- CUSTOM_CATEGORIES_START -->[\s\S]*?<!-- CUSTOM_CATEGORIES_END -->')
    if pattern.search(content):
        content = pattern.sub(block, content)
    else:
        content = content.rstrip() + '\n\n' + block + '\n'
    with open(schema_path, 'w', encoding='utf-8') as f:
        f.write(content)


def parse_frontmatter(content):
    """解析 Markdown 的 YAML frontmatter"""
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if match:
        try:
            meta = yaml.safe_load(match.group(1))
            body = match.group(2)
            return meta or {}, body
        except yaml.YAMLError:
            return {}, content
    return {}, content


def build_frontmatter(meta, body=''):
    """构建带 frontmatter 的 Markdown"""
    yaml_str = yaml.dump(meta, allow_unicode=True, default_flow_style=False)
    return f'---\n{yaml_str}---\n{body}'


def _wiki_import_index():
    """Map generated wiki page paths to the latest ingest batch that produced them."""
    batch_path = os.path.join(PROJECT_DIR, 'data', 'ingest_batches.json')
    if not os.path.exists(batch_path):
        return {}
    try:
        with open(batch_path, 'r', encoding='utf-8') as f:
            batches = json.load(f)
    except Exception:
        return {}

    index = {}
    for batch in batches if isinstance(batches, list) else []:
        imported_at = batch.get('updated_at') or batch.get('created_at') or ''
        batch_id = batch.get('id') or ''
        for rel_path in batch.get('generated_files') or []:
            key = str(rel_path).replace('\\', '/').lstrip('./')
            existing = index.get(key)
            if not existing or str(imported_at) > str(existing.get('last_imported_at', '')):
                index[key] = {
                    'last_imported_at': imported_at,
                    'last_import_batch_id': batch_id,
                }
    return index


def get_wiki_pages(page_type=None):
    """获取 Wiki 页面列表"""
    pages = []
    search_dirs = [page_type] if page_type else get_wiki_subdirs()
    import_index = _wiki_import_index()
    
    for subdir in search_dirs:
        dir_path = os.path.join(WIKI_DIR, subdir)
        if not os.path.exists(dir_path):
            continue
        for filename in os.listdir(dir_path):
            if filename.endswith('.md'):
                file_path = os.path.join(dir_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    meta, body = parse_frontmatter(content)
                    slug = filename[:-3]  # 去掉 .md
                    rel_path = f'wiki/{subdir}/{filename}'
                    import_meta = import_index.get(rel_path, {})
                    pages.append({
                        'slug': slug,
                        'type': subdir,
                        'title': meta.get('title', slug),
                        'path': rel_path,
                        'created': meta.get('created', ''),
                        'updated': meta.get('updated', ''),
                        'last_imported_at': import_meta.get('last_imported_at', ''),
                        'last_import_batch_id': import_meta.get('last_import_batch_id', ''),
                        'tags': meta.get('tags', []),
                        'related': meta.get('related', []),
                        'body_preview': body[:200] if body else ''
                    })
                except Exception:
                    continue
    
    pages.sort(
        key=lambda x: (
            str(x.get('last_imported_at') or ''),
            str(x.get('updated') or ''),
            str(x.get('created') or ''),
        ),
        reverse=True,
    )
    return pages


def get_wiki_page(slug, page_type=None):
    """获取单个 Wiki 页面"""
    if page_type:
        file_path = os.path.join(WIKI_DIR, page_type, f'{slug}.md')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            meta, body = parse_frontmatter(content)
            return {'slug': slug, 'type': page_type, 'meta': meta, 'body': body, 'content': content}
    else:
        # 搜索所有目录
        for subdir in get_wiki_subdirs():
            file_path = os.path.join(WIKI_DIR, subdir, f'{slug}.md')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                meta, body = parse_frontmatter(content)
                return {'slug': slug, 'type': subdir, 'meta': meta, 'body': body, 'content': content}
    return None


def save_wiki_page(slug, page_type, meta, body):
    """保存 Wiki 页面"""
    dir_path = os.path.join(WIKI_DIR, page_type)
    os.makedirs(dir_path, exist_ok=True)
    
    file_path = os.path.join(dir_path, f'{slug}.md')
    content = build_frontmatter(meta, body)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path


# ==================== 鉴权中间件 ====================

# 免登录的路径前缀(静态资源 + auth 端点 + 登录前必需的状态查询 + 健康检查)
_AUTH_PUBLIC_PREFIXES = (
    '/api/auth/',
    '/api/health',
)
_AUTH_PUBLIC_EXACT = {'/', '/logo.png', '/favicon.ico'}


# ─── 云本机分离模式（P1 起）────────────────────────────────────
# 当浏览器从云端前端发请求过来时：
#   - 跨域 → CORS 头放行（origin 来自 MJQ_LOCAL_CORS_ORIGINS）
#   - 鉴权 → Authorization: Bearer <jwt> 验签后写入 flask.g
# 单体模式（不设环境变量）行为完全不变。
def _local_cors_origins() -> List[str]:
    raw = os.environ.get('MJQ_LOCAL_CORS_ORIGINS', '').strip()
    if raw:
        return [o.strip() for o in raw.split(',') if o.strip()]
    # 默认开发端口
    return [
        'http://localhost:5174', 'http://127.0.0.1:5174',
        'http://localhost:4174', 'http://127.0.0.1:4174',
    ]


def _jwt_secret_cached():
    """惰性加载 JWT 共享密钥（与 cloud/main.py 共用文件）。

    没装 PyJWT 或没设密钥 → 返回 None，本机 agent 退化为单体 session 模式。
    """
    cached = getattr(_jwt_secret_cached, '_cache', None)
    if cached is not None:
        return cached or None  # '' 也表示已尝试过
    try:
        from cloud.jwt_utils import load_or_create_secret
        # JWT secret 是云本机共享的 → INSTALL_DIR（与 cloud/main.py 用同一份）
        secret = load_or_create_secret(INSTALL_DIR)
    except Exception as exc:  # 包括 PyJWT 未安装
        logger.warning(f"[auth] JWT 不可用，本机 agent 仅支持 session 模式：{exc}")
        secret = ''
    _jwt_secret_cached._cache = secret
    return secret or None


@app.after_request
def _apply_local_cors(resp):
    origin = request.headers.get('Origin', '')
    if origin and origin in _local_cors_origins():
        resp.headers['Access-Control-Allow-Origin'] = origin
        resp.headers['Access-Control-Allow-Credentials'] = 'true'
        resp.headers['Vary'] = 'Origin'
        resp.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return resp


@app.before_request
def _require_login():
    from auth import current_username
    from flask import g
    path = request.path or ''

    # CORS 预检放行（OPTIONS）
    if request.method == 'OPTIONS' and path.startswith('/api/'):
        return ('', 204)

    # 公开路径优先放行（包括 /api/health 与 /api/auth/* —— 让前端在未绑定时仍能探测）
    if path in _AUTH_PUBLIC_EXACT:
        return None
    if path.startswith('/assets/'):
        return None
    if any(path.startswith(p) for p in _AUTH_PUBLIC_PREFIXES):
        return None

    # ── JWT bridge：把 cloud 颁发的 access token 翻译成本请求的 g.user ──
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
        secret = _jwt_secret_cached()
        if secret and token:
            try:
                from cloud.jwt_utils import verify_token, InvalidTokenError
                claims = verify_token(secret, token, expected_typ='access')
                jwt_user = claims.get('sub')
                # P2-B：本机绑定校验（多租户隔离的硬闸门）
                bound = current_bound_user()
                if bound is None:
                    # 未绑定：可选自动绑定（开发友好），否则强制要求显式 bind
                    if os.environ.get('MJQ_AUTOBIND', '').lower() in {'1', 'true', 'yes'}:
                        try:
                            from user_data import bind_machine_to
                            bind_machine_to(jwt_user)
                            return jsonify({
                                'error': 'agent_just_bound',
                                'message': f'本机 agent 已绑定到 {jwt_user}，请重启 agent 后重试',
                                'bound_user': jwt_user,
                            }), 409
                        except Exception as exc:
                            logger.warning(f"[bind] auto-bind failed: {exc}")
                    return jsonify({
                        'error': 'agent_not_bound',
                        'message': '本机 agent 尚未绑定云端用户。请运行: python -m scripts.bind_user bind <username>',
                    }), 412
                if jwt_user != bound:
                    return jsonify({
                        'error': 'wrong_user',
                        'message': f'本机 agent 已绑定到 {bound}，不接受 {jwt_user} 的 token',
                        'bound_user': bound,
                    }), 403
                g.user = jwt_user
                g.user_role = claims.get('role')
                # 首次见到此用户 → 拉云端 schema 写本地 config/schema.yaml
                try:
                    from agent_bootstrap import ensure_schema_for
                    ensure_schema_for(PROJECT_DIR, g.user, token)
                except Exception as exc:
                    logger.warning(f"[bootstrap] schema sync skipped: {exc}")
            except Exception as exc:
                # 验签失败不直接 401——继续走原有逻辑（公开端点仍可放行）
                logger.debug(f"[auth] JWT verify failed: {exc}")

    # 非 API 路径(如 SPA 内部路由请求)放行,让前端自己处理
    if not path.startswith('/api/'):
        return None
    # API 路径必须登录（session 模式 fallback；JWT 已在上面被翻译成 session 等价态）
    if not current_username():
        return jsonify({'error': 'unauthorized'}), 401
    return None


# ==================== 鉴权 API ====================

@app.route('/api/auth/status', methods=['GET'])
def api_auth_status():
    """返回当前认证状态(免登录)。

    新增 role 字段：admin/member/None，便于前端判断是否显示「用户与邀请码」管理页。
    """
    from auth import has_any_user, current_username, get_user
    user = current_username()
    role = None
    if user:
        u = get_user(PROJECT_DIR, user)
        role = u.get('role') if u else None
    return jsonify({
        'has_user': has_any_user(PROJECT_DIR),
        'logged_in': bool(user),
        'username': user or None,
        'role': role,
    })


@app.route('/api/auth/setup', methods=['POST'])
def api_auth_setup():
    """首次设置账号(仅当 users.json 为空)。

    body: {username, password, unit?, title?, email?}
    unit/title/email 不强制（保持兼容旧版客户端），admin 后续可在「个人资料」补填。
    """
    from auth import has_any_user, setup_first_user
    if has_any_user(PROJECT_DIR):
        return jsonify({'error': '已存在用户,请使用登录'}), 400
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    try:
        user = setup_first_user(
            PROJECT_DIR, username, password,
            unit=data.get('unit', ''),
            title=data.get('title', ''),
            email=data.get('email', ''),
        )
    except (ValueError, PermissionError) as exc:
        return jsonify({'error': str(exc)}), 400
    session['user'] = user['username']
    session.permanent = True
    try:
        from activity_log import record
        record(PROJECT_DIR, 'auth_setup', user['username'], {})
    except Exception:
        pass
    return jsonify({'username': user['username'], 'role': user.get('role')})


@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    """凭邀请码注册新成员（公开端点）。

    body: {invite_code, username, password, unit, title, email?}
    单位/职务必填，邮箱选填。注册成功自动登录。
    """
    from auth import register_user
    data = request.json or {}
    try:
        user = register_user(
            PROJECT_DIR,
            invite_code=data.get('invite_code', ''),
            username=data.get('username', ''),
            password=data.get('password', ''),
            unit=data.get('unit', ''),
            title=data.get('title', ''),
            email=data.get('email', ''),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    session['user'] = user['username']
    session.permanent = True
    try:
        from activity_log import record
        record(PROJECT_DIR, 'register', user['username'], {
            'invite_code': data.get('invite_code', '')[:4] + '****',
            'unit': user.get('unit'),
        })
    except Exception:
        pass
    return jsonify({'username': user['username'], 'role': user.get('role')})


@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    """登录。"""
    from auth import verify_login
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    user = verify_login(PROJECT_DIR, username, password)
    if not user:
        return jsonify({'error': '用户名或密码错误'}), 401
    session['user'] = user['username']
    session.permanent = True
    try:
        from activity_log import record
        record(PROJECT_DIR, 'login', user['username'], {})
    except Exception:
        pass
    return jsonify({'username': user['username']})


@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    session.pop('user', None)
    return jsonify({'status': 'ok'})


# ==================== 邀请码管理（admin only） ====================

@app.route('/api/admin/invites', methods=['GET'])
def api_admin_invites_list():
    """列出所有邀请码（含已用），admin only。"""
    from auth import current_username, is_admin, list_invites
    user = current_username()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401
    if not is_admin(PROJECT_DIR, user):
        return jsonify({'error': 'forbidden'}), 403
    return jsonify(list_invites(PROJECT_DIR))


@app.route('/api/admin/invites', methods=['POST'])
def api_admin_invites_create():
    """生成新邀请码，admin only。body: {note?}"""
    from auth import current_username, is_admin, create_invite
    user = current_username()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401
    if not is_admin(PROJECT_DIR, user):
        return jsonify({'error': 'forbidden'}), 403
    data = request.json or {}
    note = (data.get('note') or '').strip()
    invite = create_invite(PROJECT_DIR, created_by=user, note=note)
    try:
        from activity_log import record
        record(PROJECT_DIR, 'invite_create', invite['code'], {'note': note})
    except Exception:
        pass
    return jsonify(invite)


@app.route('/api/admin/invites/<code>', methods=['DELETE'])
def api_admin_invites_revoke(code):
    """撤销未用的邀请码，admin only。已使用的不可撤。"""
    from auth import current_username, is_admin, revoke_invite
    user = current_username()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401
    if not is_admin(PROJECT_DIR, user):
        return jsonify({'error': 'forbidden'}), 403
    try:
        ok = revoke_invite(PROJECT_DIR, code)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    if not ok:
        return jsonify({'error': '邀请码不存在'}), 404
    try:
        from activity_log import record
        record(PROJECT_DIR, 'invite_revoke', code, {})
    except Exception:
        pass
    return jsonify({'status': 'ok'})


@app.route('/api/auth/change-password', methods=['POST'])
def api_auth_change_password():
    from auth import current_username, change_password
    user = current_username()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.json or {}
    old_pw = data.get('old') or ''
    new_pw = data.get('new') or ''
    try:
        ok = change_password(PROJECT_DIR, user, old_pw, new_pw)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    if not ok:
        return jsonify({'error': '原密码错误'}), 400
    return jsonify({'status': 'ok'})


# ==================== 活动日志 + 首页统计 ====================

@app.route('/api/activity', methods=['GET'])
def api_activity():
    from activity_log import recent
    limit = int(request.args.get('limit', 20))
    return jsonify(recent(PROJECT_DIR, limit))


@app.route('/api/agent/status', methods=['GET'])
def api_agent_status():
    from agent_status import get_status
    return jsonify(get_status(PROJECT_DIR))


@app.route('/api/stats', methods=['GET'])
def api_stats():
    """首页 dashboard 数据。

    返回字段：
      pages / batches / by_type / this_week / last_week / daily_activity / recent_qa
    """
    from activity_log import count_between, count_by_day
    pages = get_wiki_pages()
    by_type: Dict[str, int] = {}
    for page in pages:
        t = page.get('type', 'unknown')
        by_type[t] = by_type.get(t, 0) + 1

    # 入库文件数：从 ingest_batches.json 中累加 original_files 长度（不是批次数）
    batches_path = os.path.join(PROJECT_DIR, 'data', 'ingest_batches.json')
    batches_count = 0
    ingested_files = 0
    if os.path.exists(batches_path):
        try:
            with open(batches_path, 'r', encoding='utf-8') as f:
                batches_data = json.load(f) or []
            batches_count = len(batches_data)
            for b in batches_data:
                ingested_files += len(b.get('original_files') or [])
        except Exception:
            pass

    today = count_between(PROJECT_DIR, 0, 1)
    week = count_between(PROJECT_DIR, 0, 7)
    last_week = count_between(PROJECT_DIR, 7, 14)

    actions_to_track = ['ingest', 'chat', 'create_page', 'edit_page']
    period_summary = {
        action: {
            'this_week': week.get(action, 0),
            'last_week': last_week.get(action, 0),
        }
        for action in actions_to_track
    }

    # 最近问答（来自 wiki/outputs/，按 created 倒序前 5 条）
    recent_qa: List[Dict] = []
    recent_notes: List[Dict] = []
    for page in pages:
        ptype = page.get('type')
        if ptype == 'outputs':
            recent_qa.append({
                'slug': page['slug'],
                'title': page.get('title', page['slug']),
                'created': str(page.get('created') or ''),
                'snippet': (page.get('body_preview') or '')[:120],
            })
        elif ptype == 'notes':
            recent_notes.append({
                'slug': page['slug'],
                'type': ptype,
                'title': page.get('title', page['slug']),
                'created': str(page.get('created') or ''),
                'updated': str(page.get('updated') or ''),
                'snippet': (page.get('body_preview') or '')[:120],
            })
    recent_qa.sort(key=lambda x: x['created'], reverse=True)
    recent_qa = recent_qa[:5]
    # 排序按 updated 优先（覆盖二次解析），缺失则回退 created
    recent_notes.sort(key=lambda x: (x['updated'] or x['created']), reverse=True)
    recent_notes = recent_notes[:5]

    daily_activity = count_by_day(PROJECT_DIR, days=14, actions=actions_to_track)

    return jsonify({
        'pages': len(pages),
        'batches': batches_count,
        'ingested_files': ingested_files,
        'by_type': by_type,
        'today': {a: today.get(a, 0) for a in actions_to_track},
        'this_week': {a: week.get(a, 0) for a in actions_to_track},
        'last_week': {a: last_week.get(a, 0) for a in actions_to_track},
        'period_summary': period_summary,
        'daily_activity': daily_activity,
        'recent_qa': recent_qa,
        'recent_notes': recent_notes,
    })


# ==================== 原有 API（兼容） ====================

@app.route('/')
def index():
    # 前端是代码资源，不随用户切换 → INSTALL_DIR
    frontend_dist = os.path.join(INSTALL_DIR, 'frontend', 'dist')
    if os.path.exists(os.path.join(frontend_dist, 'index.html')):
        return send_from_directory(frontend_dist, 'index.html')
    return render_template('index.html')


@app.route('/assets/<path:filename>')
def frontend_assets(filename):
    frontend_assets_dir = os.path.join(INSTALL_DIR, 'frontend', 'dist', 'assets')
    if os.path.exists(frontend_assets_dir):
        return send_from_directory(frontend_assets_dir, filename)
    return jsonify({'error': 'Asset not found'}), 404


@app.route('/<path:filename>')
def frontend_public(filename):
    """服务 frontend/dist 根目录下的静态文件 (logo.png / favicon 等)"""
    if filename.startswith('api/') or filename.startswith('assets/'):
        return jsonify({'error': 'Not found'}), 404
    frontend_dist = os.path.join(INSTALL_DIR, 'frontend', 'dist')
    file_path = os.path.join(frontend_dist, filename)
    if os.path.isfile(file_path):
        return send_from_directory(frontend_dist, filename)
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/notes', methods=['GET'])
def get_notes():
    """获取所有笔记（兼容旧 API）"""
    pages = get_wiki_pages('notes')
    return jsonify(pages)


@app.route('/api/notes', methods=['POST'])
def create_note():
    """Create an agent-owned note and extract simple relations into wiki pages."""
    data = request.json or {}
    title = (data.get('title') or '').strip() or '未命名笔记'
    content = (data.get('content') or '').strip()
    tags = data.get('tags') or []
    source_url = (data.get('source_url') or data.get('sourceUrl') or '').strip()
    deep_extract = bool(data.get('deep_extract') or data.get('deepExtract') or source_url)

    try:
        from note_intake import build_note_pages

        result = build_note_pages(
            PROJECT_DIR,
            title,
            content,
            tags=tags,
            source_url=source_url,
            deep_extract=deep_extract,
        )
        return jsonify(result)
    except Exception as exc:
        logger.exception("create note failed title=%s", title)
        return jsonify({'error': f'创建笔记失败: {exc}'}), 500


@app.route('/api/web/extract', methods=['POST'])
def api_extract_web_content():
    """Fetch a web page and return readable text for note intake."""
    data = request.json or {}
    url = (data.get('url') or '').strip()
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        return jsonify({'error': '请输入有效的 http/https URL'}), 400

    try:
        import requests

        response = requests.get(
            url,
            timeout=12,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml,text/plain;q=0.8,*/*;q=0.5',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.7',
            },
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("web extract fetch failed url=%s error=%s", url, exc)
        return jsonify({'error': f'网页提取失败: {exc}'}), 502

    content_type = (response.headers.get('content-type') or '').lower()
    if content_type and not any(kind in content_type for kind in ('text/html', 'application/xhtml', 'text/plain')):
        return jsonify({'error': f'暂不支持该内容类型: {content_type}'}), 415

    html = (response.text or '')[:2_000_000]
    extracted = extract_web_page_text(html)
    content = extracted.get('content') or ''
    if not content:
        return jsonify({'error': '未能从该网页提取到正文文本'}), 422

    return jsonify({
        'url': url,
        'title': extracted.get('title') or '',
        'content': content,
    })


# ==================== Wiki API ====================

@app.route('/api/wiki/pages', methods=['GET'])
def api_wiki_pages():
    """获取 Wiki 页面列表"""
    page_type = request.args.get('type')
    pages = get_wiki_pages(page_type)
    return jsonify(pages)


@app.route('/api/wiki/pages/<slug>', methods=['GET'])
def api_wiki_page(slug):
    """获取单个 Wiki 页面"""
    page_type = request.args.get('type')
    page = get_wiki_page(slug, page_type)
    if page:
        try:
            from wiki_links import collect_backlinks, extract_wikilinks
            page['backlinks'] = collect_backlinks(PROJECT_DIR, slug)
            page['outlinks'] = extract_wikilinks(page.get('body', ''))
        except Exception:
            page['backlinks'] = []
            page['outlinks'] = []
        return jsonify(page)
    return jsonify({'error': 'Page not found'}), 404


@app.route('/api/wiki/pages', methods=['POST'])
def api_create_wiki_page():
    """创建 Wiki 页面"""
    return jsonify({'error': 'Wiki pages are agent-owned and read-only'}), 403
    data = request.json
    slug = data.get('slug', slugify(data.get('title', 'untitled')))
    page_type = data.get('type', 'notes')
    meta = data.get('meta', {})
    body = data.get('body', '')
    
    if page_type not in get_wiki_subdirs():
        return jsonify({'error': f'Invalid page type. Must be one of: {get_wiki_subdirs()}'}), 400
    
    today = datetime.now().strftime('%Y-%m-%d')
    if 'created' not in meta:
        meta['created'] = today
    meta['updated'] = today
    meta['type'] = page_type
    
    save_wiki_page(slug, page_type, meta, body)

    try:
        from activity_log import record
        record(PROJECT_DIR, 'create_page', slug, {'type': page_type, 'title': meta.get('title', slug)})
    except Exception:
        pass

    return jsonify({'slug': slug, 'type': page_type, 'meta': meta})


@app.route('/api/wiki/pages/<slug>', methods=['PUT'])
def api_update_wiki_page(slug):
    """更新 Wiki 页面"""
    return jsonify({'error': 'Wiki pages are agent-owned and read-only'}), 403
    data = request.json
    page_type = data.get('type')

    if not page_type:
        # 查找现有页面
        page = get_wiki_page(slug)
        if page:
            page_type = page['type']
        else:
            return jsonify({'error': 'Page not found'}), 404

    meta = data.get('meta', {})
    body = data.get('body', '')

    meta['updated'] = datetime.now().strftime('%Y-%m-%d')

    save_wiki_page(slug, page_type, meta, body)

    try:
        from activity_log import record
        record(PROJECT_DIR, 'edit_page', slug, {'type': page_type, 'title': meta.get('title', slug)})
    except Exception:
        pass

    return jsonify({'slug': slug, 'type': page_type, 'meta': meta})


@app.route('/api/wiki/pages/<slug>', methods=['DELETE'])
def api_delete_wiki_page(slug):
    """删除 Wiki 页面。要求登录，避免未认证调用方直接删除。"""
    from auth import current_username
    if not current_username():
        return jsonify({'error': 'unauthorized'}), 401

    page_type = request.args.get('type')
    page = get_wiki_page(slug, page_type)

    if not page:
        return jsonify({'error': 'Page not found'}), 404

    file_path = os.path.join(WIKI_DIR, page['type'], f"{slug}.md")
    if os.path.exists(file_path):
        os.remove(file_path)

    try:
        from activity_log import record
        record(PROJECT_DIR, 'delete_page', slug, {'type': page['type']})
    except Exception:
        pass

    return jsonify({'deleted': slug})


# ==================== 搜索 API ====================

@app.route('/api/search', methods=['GET'])
def api_search():
    """搜索 Wiki 页面"""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    
    pages = get_wiki_pages()
    results = []
    
    for page in pages:
        score = 0
        # 标题匹配
        if query in page['title'].lower():
            score += 10
        # slug 匹配
        if query in page['slug'].lower():
            score += 5
        # 内容匹配
        if query in page['body_preview'].lower():
            score += page['body_preview'].lower().count(query)
        # tags 匹配
        for tag in page.get('tags', []):
            if query in tag.lower():
                score += 3
        
        if score > 0:
            results.append({**page, 'score': score})
    
    # 按分数排序
    results.sort(key=lambda x: x['score'], reverse=True)
    return jsonify(results[:20])


# ==================== 入库批次 API ====================

@app.route('/api/ingest/upload', methods=['POST'])
def api_ingest_upload():
    """上传文件并自动入库。"""
    files = request.files.getlist('files')
    if not files:
        single = request.files.get('file')
        files = [single] if single else []

    files = [item for item in files if item and item.filename]
    if not files:
        return jsonify({'error': '请上传至少一个文件'}), 400

    from ingest_service import ingest_uploaded_files
    result = ingest_uploaded_files(files, PROJECT_DIR)

    try:
        from activity_log import record
        record(PROJECT_DIR, 'ingest', result.get('id'), {
            'file_count': len(files),
            'generated_count': len(result.get('generated_files', []) or []),
        })
    except Exception:
        pass

    return jsonify(result)


@app.route('/api/ingest/batches', methods=['GET'])
def api_ingest_batches():
    """获取最近入库批次。"""
    from ingest_batches import default_store
    store = default_store(PROJECT_DIR)
    return jsonify(store.list_batches())


@app.route('/api/ingest/batches', methods=['DELETE'])
def api_delete_ingest_batches():
    """批量删除入库批次记录，不删除原始材料和已生成知识页。"""
    from ingest_batches import default_store
    data = request.json or {}
    batch_ids = data.get('ids') or []
    if not isinstance(batch_ids, list) or not batch_ids:
        return jsonify({'error': 'ids must be a non-empty list'}), 400
    store = default_store(PROJECT_DIR)
    deleted = store.delete_batches([str(batch_id) for batch_id in batch_ids])
    try:
        from activity_log import record
        record(PROJECT_DIR, 'delete_batches', ','.join([item.get('id', '') for item in deleted]), {'count': len(deleted)})
    except Exception:
        pass
    return jsonify({'deleted': [item.get('id') for item in deleted], 'count': len(deleted)})


@app.route('/api/ingest/batches/<batch_id>', methods=['GET'])
def api_ingest_batch(batch_id):
    """获取入库批次详情。"""
    from ingest_batches import default_store
    store = default_store(PROJECT_DIR)
    batch = store.get_batch(batch_id)
    if not batch:
        return jsonify({'error': 'Batch not found'}), 404
    return jsonify(batch)


@app.route('/api/ingest/batches/<batch_id>/open-source-folder', methods=['POST'])
def api_open_ingest_batch_source_folder(batch_id):
    """Open the source folder for this ingest batch on the host machine."""
    from ingest_batches import default_store
    store = default_store(PROJECT_DIR)
    batch = store.get_batch(batch_id)
    if not batch:
        return jsonify({'error': 'Batch not found'}), 404

    root = Path(PROJECT_DIR).resolve()
    original_files = batch.get('original_files') or []
    if original_files and original_files[0].get('path'):
        raw_path = Path(str(original_files[0].get('path')))
        source_dir = raw_path.parent if raw_path.is_absolute() else (root / raw_path).resolve().parent
    else:
        source_dir = (root / 'raw' / 'sources' / batch_id).resolve()

    if not source_dir.exists() or not source_dir.is_dir():
        return jsonify({'error': 'Source folder not found'}), 404

    try:
        if os.name == 'nt':
            os.startfile(str(source_dir))
        else:
            import subprocess
            opener = 'open' if os.uname().sysname == 'Darwin' else 'xdg-open'
            subprocess.Popen([opener, str(source_dir)])
    except Exception as exc:
        logger.warning("open source folder failed batch=%s path=%s error=%s", batch_id, source_dir, exc)
        return jsonify({'error': f'Open folder failed: {exc}'}), 500

    return jsonify({'opened': str(source_dir)})


@app.route('/api/ingest/batches/<batch_id>', methods=['DELETE'])
def api_delete_ingest_batch(batch_id):
    """删除单个入库批次记录，不删除原始材料和已生成知识页。"""
    from ingest_batches import default_store
    store = default_store(PROJECT_DIR)
    try:
        deleted = store.delete_batch(batch_id)
    except KeyError:
        return jsonify({'error': 'Batch not found'}), 404
    try:
        from activity_log import record
        record(PROJECT_DIR, 'delete_batch', batch_id, {})
    except Exception:
        pass
    return jsonify({'deleted': deleted.get('id')})


@app.route('/api/ingest/batches/<batch_id>/rollback', methods=['POST'])
def api_ingest_rollback(batch_id):
    """撤回某次入库生成的知识，保留原始材料。"""
    from ingest_service import rollback_batch
    try:
        result = rollback_batch(batch_id, PROJECT_DIR)
        try:
            from activity_log import record
            record(PROJECT_DIR, 'rollback', batch_id, {})
        except Exception:
            pass
        return jsonify(result)
    except KeyError:
        return jsonify({'error': 'Batch not found'}), 404


@app.route('/api/ingest/batches/<batch_id>/reparse', methods=['POST'])
def api_ingest_reparse(batch_id):
    """Re-run parsing for an existing batch and merge newly generated knowledge."""
    from ingest_service import reparse_batch
    try:
        result = reparse_batch(batch_id, PROJECT_DIR)
    except KeyError:
        return jsonify({'error': 'Batch not found'}), 404
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    try:
        from activity_log import record
        record(PROJECT_DIR, 'reparse_batch', batch_id, {
            'generated_count': len(result.get('generated_files', []) or []),
            'entity_count': len(result.get('entities', []) or []),
        })
    except Exception:
        pass
    return jsonify(result)


@app.route('/api/ingest/stale', methods=['GET'])
def api_ingest_stale():
    """列出 status: 待精炼 的 fallback 页面，含源材料是否仍存在。"""
    from ingest_service import find_stale_notes
    items = find_stale_notes(PROJECT_DIR)
    return jsonify({
        'total': len(items),
        'recoverable': sum(1 for s in items if s['source_exists']),
        'items': items,
    })


@app.route('/api/ingest/retry-stale', methods=['POST'])
def api_ingest_retry_stale():
    """对 status: 待精炼 的 fallback 页面重跑 auto_ingest。

    Request body:
      {
        "stale_paths": ["wiki/notes/..."],   # 可选；不传则重试全部 stale
        "delete_on_success": true            # 可选；默认 true（成功后删原 stale 页）
      }
    """
    from ingest_service import retry_stale_notes
    data = request.json or {}
    stale_paths = data.get('stale_paths')
    if stale_paths is not None and not isinstance(stale_paths, list):
        return jsonify({'error': 'stale_paths 必须是数组'}), 400
    delete_on_success = bool(data.get('delete_on_success', True))
    try:
        result = retry_stale_notes(
            PROJECT_DIR,
            stale_paths=stale_paths,
            delete_on_success=delete_on_success,
        )
        try:
            from activity_log import record
            record(PROJECT_DIR, 'retry_stale', result.get('batch_id'), {
                'total': result.get('total'),
                'succeeded': result.get('succeeded'),
                'still_stale': result.get('still_stale'),
            })
        except Exception:
            pass
        return jsonify(result)
    except Exception as exc:
        logger.exception("retry_stale 失败")
        return jsonify({'error': str(exc)}), 500


# ==================== 索引和日志 ====================

@app.route('/api/wiki/index', methods=['GET'])
def api_wiki_index():
    """获取 wiki/index.md 内容"""
    index_path = os.path.join(WIKI_DIR, 'index.md')
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return jsonify({'content': f.read()})
    return jsonify({'content': ''})


@app.route('/api/wiki/log', methods=['GET'])
def api_wiki_log():
    """获取 wiki/log.md 内容"""
    log_path = os.path.join(WIKI_DIR, 'log.md')
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            return jsonify({'content': f.read()})
    return jsonify({'content': ''})


# ==================== 对话查询 API ====================

def _extract_person_name(page):
    """从人物页面标题/正文里提取姓名。"""
    title = str(page.get('title') or page.get('slug') or '')
    title = re.sub(r'^(嫌疑人|受害人|证人|其他|人员|联系人)\s*[-—]\s*', '', title).strip()
    title = re.sub(r'\s+', '', title)
    if title:
        return title
    body = page.get('full_content') or page.get('body_preview') or ''
    match = re.search(r'姓名[：:]\s*([^\s，,。；;）)]+)', body)
    return match.group(1).strip() if match else str(page.get('slug') or '')


def _linked_case_titles(person_slug):
    """查找引用了人物页面的案件标题。"""
    titles = []
    link_patterns = (f'[[{person_slug}]]', f'[[{person_slug}|')
    for page in get_wiki_pages('cases'):
        full = get_wiki_page(page['slug'], page['type'])
        body = full['body'] if full else page.get('body_preview', '')
        related = page.get('related') or []
        related_text = '\n'.join(str(item) for item in related)
        if any(pattern in body or pattern in related_text for pattern in link_patterns):
            titles.append(page.get('title') or page['slug'])
    return titles


def _batch_entity_suspects_by_surname(surname):
    """从批次记录实体里兜底查找嫌疑人，适用于 wiki 文件缺失或未完成写入的情况。"""
    batch_path = os.path.join(PROJECT_DIR, 'data', 'ingest_batches.json')
    if not os.path.exists(batch_path):
        return []
    try:
        with open(batch_path, 'r', encoding='utf-8') as f:
            batches = json.load(f)
    except Exception:
        return []

    found = {}
    for batch in batches if isinstance(batches, list) else []:
        generated_files = batch.get('generated_files') or []
        case_titles = [
            Path(path).stem
            for path in generated_files
            if str(path).replace('\\', '/').startswith('wiki/cases/')
        ]
        for entity in batch.get('entities') or []:
            name = str(entity.get('name') or '').strip()
            if not name.startswith(surname):
                continue
            haystack = ' '.join(str(entity.get(key) or '') for key in ('type', 'role', 'description', 'details'))
            if '嫌疑' not in haystack:
                continue
            item = found.setdefault(name, {
                'slug': f'嫌疑人-{name}',
                'type': 'persons',
                'title': f'嫌疑人 - {name}',
                'name': name,
                'cases': [],
                'full_content': '',
            })
            for title in case_titles:
                if title not in item['cases']:
                    item['cases'].append(title)
            detail = entity.get('description') or entity.get('details') or ''
            if detail and detail not in item['full_content']:
                item['full_content'] = (item['full_content'] + '\n' + detail).strip()
    return list(found.values())


def answer_structured_local_query(query):
    """对常见清单类问题使用本地确定性查询，避免 LLM 不可用时完全无反馈。"""
    normalized = re.sub(r'\s+', '', query or '')
    surname_match = re.search(r'姓([\u4e00-\u9fff])', normalized)
    asks_suspect = '嫌疑' in normalized
    asks_person_list = any(word in normalized for word in ('哪些', '有谁', '名单', '列出'))
    if not (surname_match and asks_person_list and asks_suspect):
        return None

    surname = surname_match.group(1)
    matches = []
    for page in get_wiki_pages('persons'):
        full = get_wiki_page(page['slug'], page['type'])
        body = full['body'] if full else page.get('body_preview', '')
        meta = full.get('meta', {}) if full else {}
        title = meta.get('title') or page.get('title') or page['slug']
        role_text = ' '.join([
            str(meta.get('role') or ''),
            str(title),
            ' '.join(str(tag) for tag in (meta.get('tags') or page.get('tags') or [])),
            body[:500],
        ])
        if '嫌疑' not in role_text:
            continue
        name = _extract_person_name({**page, 'title': title, 'full_content': body})
        if not name.startswith(surname):
            continue
        cases = _linked_case_titles(page['slug'])
        matches.append({
            **page,
            'title': title,
            'name': name,
            'cases': cases,
            'full_content': body[:1000],
        })

    if not matches:
        matches = _batch_entity_suspects_by_surname(surname)

    if not matches:
        return {
            'response': f'本地知识库中暂未检索到姓“{surname}”的嫌疑人。',
            'sources': [],
        }

    lines = [f'本地知识库中检索到 {len(matches)} 名姓“{surname}”的嫌疑人：']
    for idx, item in enumerate(matches, 1):
        case_text = '；关联案件：' + '、'.join(item['cases'][:3]) if item['cases'] else ''
        lines.append(f'{idx}. {item["name"]}（页面：{item["title"]}）{case_text}')
    return {
        'response': '\n'.join(lines),
        'sources': matches,
    }

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """对话查询 - 基于知识库的 QA"""
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400

    local_answer = answer_structured_local_query(query)
    if local_answer:
        relevant_pages = local_answer['sources'][:5]
        response = local_answer['response']
        auto_save_qa(query, response, relevant_pages)
        try:
            from activity_log import record
            record(PROJECT_DIR, 'chat', None, {
                'query': query[:80],
                'sources': [p['title'] for p in relevant_pages[:3]],
                'mode': 'local_structured',
            })
        except Exception:
            pass
        return jsonify({
            'query': query,
            'response': response,
            'sources': serialize_chat_sources(relevant_pages),
            'mode': 'local_structured',
        })
    
    # 搜索相关知识库页面（读取完整内容）
    all_pages = get_wiki_pages()
    relevant_pages = []
    
    # 分词搜索（支持中文 bigram）
    def tokenize_query(query):
        """改进分词：支持中文 bigram"""
        import re
        # 去除标点符号
        query = re.sub(r'[，。！？、；：""''（）()？]', ' ', query)
        # 分割（按空格）
        raw_tokens = query.lower().split()
        
        tokens = []
        stop_words = {'的', '是', '了', '什么', '在', '有', '和', '与', '对', '从', '吗', '呢', '吧', '啊'}
        
        for token in raw_tokens:
            if not token or token in stop_words:
                continue
            # 检查是否包含中文字符
            has_cjk = any('\u4e00' <= c <= '\u9fff' for c in token)
            if has_cjk:
                # 添加 bigram
                for i in range(len(token) - 1):
                    bigram = token[i:i+2]
                    if bigram not in stop_words:
                        tokens.append(bigram)
                # 添加单个字符
                for c in token:
                    if c not in stop_words:
                        tokens.append(c)
                # 添加完整 token
                tokens.append(token)
            else:
                tokens.append(token)
        
        return list(set(tokens))
    
    tokens = tokenize_query(query)
    
    for page in all_pages:
        # 读取完整内容
        full_page = get_wiki_page(page['slug'], page['type'])
        full_content = full_page['body'] if full_page else page['body_preview']
        
        score = 0
        title_lower = str(page.get('title') or '').lower()
        content_lower = str(full_content or '').lower()
        
        # 对每个 token 进行匹配
        for token in tokens:
            if token in title_lower:
                score += 10
            if token in content_lower:
                score += content_lower.count(token) * 2
            # tags 在 frontmatter 写 `tags:` (无值) 时被 yaml 解析为 None；用 `or []` 兜底
            for tag in (page.get('tags') or []):
                # tag 可能是 int / None / dict（来自 frontmatter 解析），强制 str
                if token in str(tag).lower():
                    score += 3
        
        if score > 0:
            relevant_pages.append({**page, 'full_content': full_content[:1000], 'score': score})
    
    relevant_pages.sort(key=lambda x: x['score'], reverse=True)
    relevant_pages = relevant_pages[:5]  # 关键词命中 top 5

    # 图谱二跳扩展：沿 [[wiki-link]] 边把强相关但关键词没命中的页拉进来
    # 串并案场景刚需：A 案命中关键词、B 案没命中但通过同一嫌疑人/地点连着 → 应一并入上下文
    chat_cfg = _load_chat_runtime_config()
    expanded = _expand_via_graph(
        relevant_pages, all_pages,
        enable=chat_cfg['graph_expand'],
        hops=chat_cfg['graph_hops'],
        max_added=chat_cfg['graph_max_added'],
    )

    # 字符预算分配：替代原来的硬编码 [:1000] 截断
    # 关键词命中页拿大头，扩展页拿余量；单页上限由 max_chars_per_page 控制
    context_parts = _build_chat_context(
        relevant_pages, expanded,
        budget_chars=int(chat_cfg['context_budget_chars'] * chat_cfg['wiki_share']),
        max_chars_per_page=chat_cfg['max_chars_per_page'],
    )
    context = '\n\n'.join(context_parts) if context_parts else '知识库中没有相关内容。'
    
    # 调用 LLM 生成回答
    from llm_client import chat_completion, last_llm_error
    
    prompt = f"""你是一个警务知识库助手。根据以下知识库内容，回答用户的问题。

## 知识库内容

{context}

## 用户问题

{query}

## 回答要求

1. 基于知识库内容回答
2. 如果知识库中没有相关信息，明确告知用户
3. 引用相关页面时，使用页面标题
4. 回答简洁明了
5. 使用中文回答

请直接回答用户的问题：
"""
    
    response_text = chat_completion([
        {'role': 'system', 'content': '你是警务知识库助手，帮助民警查询和分析知识库内容。'},
        {'role': 'user', 'content': prompt}
    ], temperature=0.3)
    
    llm_error = last_llm_error()
    if response_text:
        response = response_text
    elif llm_error:
        response = (
            '当前已检索到相关知识库页面，但模型调用失败，无法生成完整回答。\n\n'
            f'后台错误：{llm_error}\n\n'
            '请在“系统配置”中检查模型 API Key、模型名称和接口地址。'
        )
    else:
        response = '抱歉，我无法回答这个问题。'

    # 来源 = 关键词命中 + 图谱扩展（扩展页标记 source: graph 给前端区分）
    all_sources = list(relevant_pages) + [{**p, '_graph_expanded': True} for p in expanded]

    # 复利循环：自动将问答结果存回 wiki
    auto_save_qa(query, response, all_sources)

    try:
        from activity_log import record
        record(PROJECT_DIR, 'chat', None, {
            'query': query[:80],
            'sources': [p['title'] for p in relevant_pages[:3]],
            'graph_expanded': len(expanded),
        })
    except Exception:
        pass

    return jsonify({
        'query': query,
        'response': response,
        'sources': serialize_chat_sources(all_sources),
        'llm_error': llm_error,
    })


def _load_chat_runtime_config() -> Dict:
    """读取 chat 段配置，给安全默认值。配置缺失/异常都退回到合理默认。"""
    defaults = {
        'graph_expand': True,
        'graph_hops': 1,
        'graph_max_added': 5,
        'context_budget_chars': 150000,
        'wiki_share': 0.75,
        'max_chars_per_page': 10000,
    }
    try:
        from config_store import load_config
        section = load_config(os.path.join(PROJECT_DIR, 'config', 'config.yaml')).get('chat') or {}
    except Exception:
        section = {}
    out = dict(defaults)
    for k, v in section.items():
        if k in defaults and v is not None:
            try:
                out[k] = type(defaults[k])(v) if not isinstance(defaults[k], bool) else bool(v)
            except (TypeError, ValueError):
                pass
    # 边界保护
    out['graph_hops'] = max(0, min(2, int(out['graph_hops'])))
    out['graph_max_added'] = max(0, min(20, int(out['graph_max_added'])))
    out['context_budget_chars'] = max(2000, min(500000, int(out['context_budget_chars'])))
    out['wiki_share'] = max(0.3, min(0.95, float(out['wiki_share'])))
    out['max_chars_per_page'] = max(300, min(30000, int(out['max_chars_per_page'])))
    return out


def _expand_via_graph(seed_pages: List[Dict], all_pages: List[Dict], *,
                      enable: bool, hops: int, max_added: int) -> List[Dict]:
    """从 seed_pages 沿知识图谱 [[wiki-link]] 边走 hops 跳，返回新增的页面对象。

    设计要点：
      - 任何异常 / 空图谱都安全退回到 []，不影响主流程（原则 14 容错）
      - 不替换关键词命中结果，只追加；上下文体积由 _build_chat_context 控制
      - max_added 控制扩展规模，避免低相关页冲淡上下文
    """
    if not enable or hops <= 0 or max_added <= 0 or not seed_pages:
        return []

    try:
        from graph import build_graph
        graph_data = build_graph()
    except Exception as exc:
        from mjq_logging import get_logger
        get_logger(__name__).warning('chat graph_expand 失败，退回纯关键词检索: %s', exc)
        return []

    # 邻接表
    adj: Dict[str, set] = {}
    for edge in graph_data.get('edges', []):
        s, t = edge.get('source'), edge.get('target')
        if not s or not t:
            continue
        adj.setdefault(s, set()).add(t)
        adj.setdefault(t, set()).add(s)

    seed_slugs = {p.get('slug') for p in seed_pages if p.get('slug')}
    visited = set(seed_slugs)
    frontier = set(seed_slugs)
    expanded_slugs: List[str] = []

    for _ in range(hops):
        next_frontier: set = set()
        for slug in frontier:
            for neighbor in adj.get(slug, ()):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                next_frontier.add(neighbor)
                expanded_slugs.append(neighbor)
                if len(expanded_slugs) >= max_added:
                    break
            if len(expanded_slugs) >= max_added:
                break
        if len(expanded_slugs) >= max_added:
            break
        frontier = next_frontier

    if not expanded_slugs:
        return []

    page_by_slug = {p.get('slug'): p for p in all_pages if p.get('slug')}
    out: List[Dict] = []
    for slug in expanded_slugs[:max_added]:
        meta = page_by_slug.get(slug)
        if not meta:
            continue
        full = get_wiki_page(slug, meta.get('type'))
        body = (full or {}).get('body') or meta.get('body_preview') or ''
        out.append({**meta, 'full_content': body, 'score': 0, '_graph_expanded': True})
    return out


def _build_chat_context(primary: List[Dict], expanded: List[Dict], *,
                        budget_chars: int, max_chars_per_page: int = 1000) -> List[str]:
    """按字符预算给每页分配长度，替代旧的硬编码 [:1000] 截断。

    分配策略：primary 拿 70% 预算，expanded 拿 30%；同组内按页数等分；
    单页地板 300、天花板 max_chars_per_page（默认 1000，由 chat.max_chars_per_page 控制）。
    """
    if not primary and not expanded:
        return []

    parts: List[str] = []
    primary_budget = int(budget_chars * 0.7) if expanded else budget_chars
    expanded_budget = budget_chars - primary_budget
    ceiling = max(300, int(max_chars_per_page))

    def _emit(pages: List[Dict], total_budget: int, label: str = '') -> None:
        if not pages or total_budget <= 0:
            return
        per_page = max(300, min(ceiling, total_budget // len(pages)))
        for page in pages:
            content = page.get('full_content') or page.get('body_preview') or ''
            if len(content) > per_page:
                content = content[:per_page].rstrip() + '\n……（内容较长，按上下文预算截取）'
            heading = f"## {page.get('title') or page.get('slug')}"
            if label:
                heading += f"  _{label}_"
            parts.append(f"{heading}\n{content}")

    _emit(primary, primary_budget)
    _emit(expanded, expanded_budget, label='图谱关联页')
    return parts


def serialize_chat_sources(pages: List[Dict]) -> List[Dict]:
    sources = []
    for page in pages:
        slug = page.get('slug')
        page_type = page.get('type')
        title = page.get('title') or slug
        if not slug or not page_type:
            continue
        item = {'slug': slug, 'type': page_type, 'title': title}
        if page.get('_graph_expanded'):
            item['source'] = 'graph'
        sources.append(item)
    return sources


def auto_save_qa(query: str, response: str, sources: List[Dict]):
    """自动将问答结果存回 wiki，形成复利循环"""
    from datetime import datetime
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()[:12]
    slug = slugify(f"qa-{now.strftime('%Y%m%d%H%M%S')}-{query_hash}-{uuid.uuid4().hex[:8]}")
    
    # 构建引用链接
    related = [f"[[{p['slug']}]]" for p in sources]
    
    meta = {
        'type': 'output',
        'title': f"问答：{query}",
        'tags': ['问答', '自动保存'],
        'related': related,
        'created': today,
        'updated': today,
        'query': query,
        'query_hash': query_hash,
    }
    
    body = f"# 问答：{query}\n\n## 问题\n\n{query}\n\n## 回答\n\n{response}\n\n## 参考来源\n\n{', '.join(related)}\n"
    
    path = save_wiki_page(slug, 'outputs', meta, body)
    try:
        from activity_log import record
        record(PROJECT_DIR, 'agent_save_output', slug, {
            'query_hash': query_hash,
            'source_count': len(sources),
            'path': os.path.relpath(path, PROJECT_DIR).replace('\\', '/'),
        })
    except Exception:
        pass
    return {'slug': slug, 'type': 'outputs', 'path': path, 'meta': meta}


# ==================== 手动分析 API ====================

@app.route('/api/analyze/<slug>', methods=['POST'])
def api_analyze_note(slug):
    """手动触发笔记分析"""
    page = get_wiki_page(slug, 'notes')
    if not page:
        return jsonify({'error': 'Note not found'}), 404
    
    from auto_ingest import auto_ingest
    result = auto_ingest(slug, page['body'], page['meta'])
    
    return jsonify(result)


@app.route('/api/enrich/<slug>', methods=['POST'])
def api_enrich_wikilinks(slug):
    """手动触发 wikilink 富化"""
    page = get_wiki_page(slug)
    if not page:
        return jsonify({'error': 'Page not found'}), 404
    
    all_pages = get_wiki_pages()
    from auto_ingest import enrich_wikilinks
    
    enriched_content = enrich_wikilinks(page['content'], all_pages)
    
    # 保存更新后的内容
    save_wiki_page(slug, page['type'], page['meta'], enriched_content)
    
    return jsonify({'status': 'success', 'slug': slug})


# ==================== 知识图谱 API ====================

@app.route('/api/graph', methods=['GET'])
def api_graph():
    """获取知识图谱数据"""
    from graph import build_graph
    graph_data = build_graph()
    return jsonify(graph_data)


@app.route('/api/graph/merged', methods=['GET'])
def api_graph_merged():
    """获取合并后的知识图谱数据"""
    threshold = float(request.args.get('threshold', 0.3))
    from graph import build_graph, merge_related_nodes
    graph_data = build_graph()
    merged_data = merge_related_nodes(graph_data, threshold)
    return jsonify(merged_data)


@app.route('/api/cases/<slug>/related', methods=['GET'])
def api_related_cases(slug):
    """查找与指定案件相关的案件"""
    from graph import find_related_cases
    related = find_related_cases(slug)
    return jsonify(related)


@app.route('/api/cases', methods=['GET'])
def api_cases():
    """获取所有案件列表"""
    cases = get_wiki_pages('cases')
    return jsonify(cases)


@app.route('/api/lint', methods=['GET'])
def api_lint():
    """运行 Wiki 维护检查"""
    from graph import run_lint
    lint_result = run_lint()
    return jsonify(lint_result)


@app.route('/api/lint/run', methods=['POST'])
def api_run_lint():
    """运行并自动修复 Wiki 维护问题"""
    from graph import run_lint
    lint_result = run_lint()

    # 自动修复断链
    fixed = []
    for link in lint_result.get('broken_links', []):
        # 尝试修复断链（移除或替换）
        fixed.append(link)

    # 标记过期页面
    stale = lint_result.get('stale_pages', [])

    return jsonify({
        'status': 'completed',
        'fixed': fixed,
        'stale': stale,
        'suggestions': lint_result.get('suggestions', [])
    })


@app.route('/api/lint/fix', methods=['POST'])
def api_lint_fix():
    """按类别批量修复体检问题。

    Request body:
      {
        "category": "broken_links" | "orphan_pages" | "stale_pages",
        "items": [
          # broken_links: { "from": str, "to": str, "action": "remove" | "create_stub" }
          # orphan_pages: { "slug": str, "type": str, "action": "enrich" | "ignore" }
          # stale_pages:  { "slug": str, "type": str, "action": "touch" | "ignore" }
        ]
      }
    """
    import re
    from datetime import datetime
    data = request.json or {}
    category = data.get('category')
    items = data.get('items', [])

    if category not in {'broken_links', 'orphan_pages', 'stale_pages'}:
        return jsonify({'error': f'未知类别: {category}'}), 400
    if not isinstance(items, list):
        return jsonify({'error': 'items 必须为数组'}), 400

    succeeded = []
    failed = []
    today = datetime.now().strftime('%Y-%m-%d')

    if category == 'broken_links':
        for item in items:
            src_slug = item.get('from')
            target = item.get('to')
            action = item.get('action', 'remove')
            try:
                src = get_wiki_page(src_slug)
                if not src:
                    failed.append({'item': item, 'error': '源页面不存在'})
                    continue
                if action == 'remove':
                    # 删除 [[target]] 或 [[target|alias]]，含周围空格
                    pattern = re.compile(
                        r'\[\[\s*' + re.escape(target) + r'\s*(?:\|[^\]]+)?\]\]',
                        re.IGNORECASE,
                    )
                    new_body, count = pattern.subn('', src['body'])
                    if count == 0:
                        failed.append({'item': item, 'error': '未在源页中找到该链接'})
                        continue
                    meta = dict(src['meta'])
                    meta['updated'] = today
                    save_wiki_page(src_slug, src['type'], meta, new_body)
                    succeeded.append({'item': item, 'removed': count})
                elif action == 'create_stub':
                    # 创建空白目标页（默认 notes 类型）
                    stub_slug = target.strip()
                    if get_wiki_page(stub_slug):
                        failed.append({'item': item, 'error': '目标页已存在'})
                        continue
                    stub_meta = {
                        'type': 'notes',
                        'title': stub_slug,
                        'tags': [],
                        'related': [],
                        'created': today,
                        'updated': today,
                    }
                    save_wiki_page(stub_slug, 'notes', stub_meta, f'# {stub_slug}\n\n（占位页面，由体检修复创建，请补充内容。）\n')
                    succeeded.append({'item': item, 'created': stub_slug})
                else:
                    failed.append({'item': item, 'error': f'broken_links 不支持动作: {action}'})
            except Exception as exc:  # noqa: BLE001
                failed.append({'item': item, 'error': str(exc)})

    elif category == 'orphan_pages':
        # 把 enrich 与 ignore 分开：enrich 走并发（LLM I/O 密集），ignore 顺序处理。
        # 顺序执行 N 个 enrich 是历史耗时根因（每个 ~5-30s LLM 调用串行）。
        all_pages = get_wiki_pages() if any(i.get('action') == 'enrich' for i in items) else []
        try:
            from auto_ingest import enrich_wikilinks
        except Exception:  # noqa: BLE001
            enrich_wikilinks = None

        enrich_jobs = []  # (item, page) 待并发 enrich
        for item in items:
            slug = item.get('slug')
            page_type = item.get('type')
            action = item.get('action', 'ignore')
            try:
                page = get_wiki_page(slug, page_type)
                if not page:
                    failed.append({'item': item, 'error': '页面不存在'})
                    continue
                if action == 'enrich':
                    if not enrich_wikilinks:
                        failed.append({'item': item, 'error': 'enrich_wikilinks 不可用'})
                        continue
                    enrich_jobs.append((item, page))
                elif action == 'ignore':
                    meta = dict(page['meta'])
                    meta['standalone'] = True
                    meta['updated'] = today
                    save_wiki_page(slug, page['type'], meta, page['body'])
                    succeeded.append({'item': item, 'ignored': True})
                else:
                    failed.append({'item': item, 'error': f'orphan_pages 不支持动作: {action}'})
            except Exception as exc:  # noqa: BLE001
                failed.append({'item': item, 'error': str(exc)})

        # 并发执行 enrich：LLM 调用是 I/O 密集，并行可大幅缩短总耗时。
        if enrich_jobs:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            max_workers = min(5, len(enrich_jobs))

            def _do_enrich(job):
                jitem, jpage = job
                return jitem, jpage, enrich_wikilinks(jpage['content'], all_pages)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_do_enrich, job) for job in enrich_jobs]
                for future in as_completed(futures):
                    try:
                        item, page, enriched = future.result()
                    except Exception as exc:  # noqa: BLE001
                        failed.append({'item': None, 'error': f'enrich 异常: {exc}'})
                        continue
                    try:
                        new_meta, new_body = parse_frontmatter(enriched)
                        if not new_meta:
                            new_meta = dict(page['meta'])
                            new_body = enriched
                        new_meta['updated'] = today
                        save_wiki_page(item.get('slug'), page['type'], new_meta, new_body)
                        succeeded.append({'item': item, 'enriched': True})
                    except Exception as exc:  # noqa: BLE001
                        failed.append({'item': item, 'error': str(exc)})

    else:  # stale_pages
        for item in items:
            slug = item.get('slug')
            page_type = item.get('type')
            action = item.get('action', 'touch')
            try:
                page = get_wiki_page(slug, page_type)
                if not page:
                    failed.append({'item': item, 'error': '页面不存在'})
                    continue
                meta = dict(page['meta'])
                if action == 'touch':
                    meta['updated'] = today
                    save_wiki_page(slug, page['type'], meta, page['body'])
                    succeeded.append({'item': item, 'touched': True})
                elif action == 'ignore':
                    meta['standalone'] = True
                    meta['updated'] = today
                    save_wiki_page(slug, page['type'], meta, page['body'])
                    succeeded.append({'item': item, 'ignored': True})
                else:
                    failed.append({'item': item, 'error': f'stale_pages 不支持动作: {action}'})
            except Exception as exc:  # noqa: BLE001
                failed.append({'item': item, 'error': str(exc)})

    try:
        from activity_log import record
        record(PROJECT_DIR, 'agent_lint_fix', category, {
            'succeeded': len(succeeded),
            'failed': len(failed),
            'actions': [item.get('action') for item in items if isinstance(item, dict)],
        })
    except Exception:
        pass

    return jsonify({
        'status': 'completed',
        'category': category,
        'succeeded': succeeded,
        'failed': failed,
    })


@app.route('/api/config', methods=['GET'])
def api_config():
    """获取系统配置（api_key 从 .env 读取，不从 yaml 返回）"""
    config_path = os.path.join(PROJECT_DIR, 'config', 'config.yaml')
    from config_store import MODEL_ENV_FIELDS, load_config, load_dotenv
    config = load_config(config_path)
    dotenv_vars = load_dotenv(PROJECT_DIR)

    for section, field_map in MODEL_ENV_FIELDS.items():
        if section not in config:
            config[section] = {}
        for yaml_key, env_key in field_map.items():
            if env_key in dotenv_vars and dotenv_vars[env_key]:
                config[section][yaml_key] = dotenv_vars[env_key]
        raw_key = config.get(section, {}).get('api_key', '')
        if raw_key and len(raw_key) > 10 and not raw_key.startswith('${'):
            config[section]['api_key'] = raw_key[:6] + '****' + raw_key[-4:]

    if config:
        return jsonify(config)
    return jsonify({'error': 'Config not found'}), 404


@app.route('/api/config', methods=['PUT'])
def api_update_config():
    """更新系统配置（api_key 自动存入 .env，不入 yaml）"""
    data = request.json or {}
    config_path = os.path.join(PROJECT_DIR, 'config', 'config.yaml')
    from config_store import MODEL_ENV_FIELDS, update_config, save_dotenv, load_dotenv

    dotenv_overrides = {}
    for section, field_map in MODEL_ENV_FIELDS.items():
        model_data = data.get(section, {})
        if not isinstance(model_data, dict):
            continue
        for yaml_key, env_key in field_map.items():
            if yaml_key in model_data:
                value = model_data.pop(yaml_key) or ''
                if yaml_key == 'api_key' and '****' in value:
                    continue
                dotenv_overrides[env_key] = value
    if dotenv_overrides:
        save_dotenv(PROJECT_DIR, dotenv_overrides)

    config = update_config(config_path, data)
    ensure_custom_category_dirs()
    update_schema_custom_categories()

    dotenv_vars = load_dotenv(PROJECT_DIR)
    for section, field_map in MODEL_ENV_FIELDS.items():
        if section not in config:
            config[section] = {}
        for yaml_key, env_key in field_map.items():
            if env_key in dotenv_vars:
                config[section][yaml_key] = dotenv_vars[env_key]
            elif yaml_key in config.get(section, {}):
                config[section].pop(yaml_key, None)
        raw_key = config.get(section, {}).get('api_key', '')
        if raw_key and len(raw_key) > 10 and not raw_key.startswith('${'):
            config[section]['api_key'] = raw_key[:6] + '****' + raw_key[-4:]

    return jsonify({'status': 'success', 'config': config})


@app.route('/api/config/test-llm', methods=['POST'])
def api_test_llm_config():
    """测试模型连接。"""
    data = request.json or {}
    role = data.get('role') or 'llm'
    model_config = data.get(role) or data.get('config') or data.get('llm') or data
    if role not in ('llm', 'vision_model', 'ocr_model'):
        role = 'llm'

    from config_store import MODEL_ENV_FIELDS, load_config, load_dotenv
    config_path = os.path.join(PROJECT_DIR, 'config', 'config.yaml')
    saved_config = load_config(config_path)
    dotenv_vars = load_dotenv(PROJECT_DIR)
    llm_fallback = saved_config.get('llm', {}) or {}
    role_saved = saved_config.get(role, {}) or {}
    llm_config = {**llm_fallback, **role_saved, **(model_config or {})}

    if role != 'llm':
        for key in ('provider', 'base_url', 'model', 'api_key'):
            if not llm_config.get(key):
                llm_config[key] = llm_fallback.get(key, '')

    field_map = MODEL_ENV_FIELDS.get(role, MODEL_ENV_FIELDS['llm'])
    fallback_fields = MODEL_ENV_FIELDS['llm']
    api_key = str(llm_config.get('api_key') or '')
    if '****' in api_key or not api_key:
        llm_config['api_key'] = (
            dotenv_vars.get(field_map['api_key'])
            or dotenv_vars.get(fallback_fields['api_key'])
            or dotenv_vars.get('BAILIAN_API_KEY')
            or api_key
        )
    for yaml_key, env_key in field_map.items():
        if yaml_key == 'api_key':
            continue
        if not llm_config.get(yaml_key) and dotenv_vars.get(env_key):
            llm_config[yaml_key] = dotenv_vars[env_key]

    from llm_tester import test_llm_connection
    result = test_llm_connection(llm_config)
    result['role'] = role
    return jsonify(result), (200 if result.get('ok') else 400)


@app.route('/api/wiki/categories', methods=['GET'])
def api_wiki_categories():
    """获取知识目录分类配置。"""
    return jsonify(get_wiki_category_options())


# ==================== 孤立实体 / 孤立页面（P3） ====================

# ==================== 源文档预览（P4） ====================

def _resolve_safe_raw_path(rel_path: str) -> Optional[str]:
    """把前端传来的相对路径安全解析到 raw 目录内。

    规则：
      - 拒绝绝对路径、含 .. 的逃逸尝试
      - 解析后必须 commonpath 落在 raw 根（含 raw/sources 与 raw/inbox）
      - 必须是普通文件
    返回 abs path 或 None。
    """
    if not rel_path or not isinstance(rel_path, str):
        return None
    if os.path.isabs(rel_path) or '..' in Path(rel_path).parts:
        return None
    from config_store import get_raw_dir
    raw_root = os.path.realpath(get_raw_dir(PROJECT_DIR))
    candidate = os.path.realpath(os.path.join(raw_root, rel_path))
    try:
        if os.path.commonpath([raw_root, candidate]) != raw_root:
            return None
    except ValueError:
        return None
    if not os.path.isfile(candidate):
        return None
    return candidate


_RAW_MIME = {
    '.pdf': 'application/pdf',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.webp': 'image/webp',
    '.svg': 'image/svg+xml',
    '.txt': 'text/plain; charset=utf-8',
    '.md': 'text/markdown; charset=utf-8',
    '.html': 'text/html; charset=utf-8',
}


@app.route('/api/health', methods=['GET'])
def api_local_health():
    """本机 agent 健康检查 + 绑定状态披露（前端连接灯用）。

    设计为公开端点（不需要 JWT），让浏览器在"还没拿到 token"阶段就能探测本机存活。
    返回最少必要信息，避免暴露细节。
    """
    from user_data import current_bound_user, is_legacy_mode
    bound = current_bound_user()
    return jsonify({
        'status': 'ok',
        'service': 'mjq-agent',
        'phase': 'P5',
        'bound_user': bound,         # None 表示 legacy 模式
        'legacy_mode': is_legacy_mode(),
    })


@app.route('/api/source/preview', methods=['GET'])
def api_source_preview():
    """文本/解析形式预览源文档。

    query: path=<raw 内的相对路径>&format=text|info（默认 text）
      - text: 用 file_parser 解析；返回 {text, file_type, size}
      - info: 仅元数据，不读内容；返回 {file_type, size, mtime}
    """
    rel = request.args.get('path', '').strip()
    fmt = request.args.get('format', 'text').strip().lower()
    abs_path = _resolve_safe_raw_path(rel)
    if not abs_path:
        return jsonify({'error': 'path 非法或文件不存在'}), 400

    stat = os.stat(abs_path)
    base_info = {
        'path': rel.replace('\\', '/'),
        'size': stat.st_size,
        'mtime': int(stat.st_mtime),
        'file_type': Path(abs_path).suffix.lower(),
    }
    if fmt == 'info':
        return jsonify(base_info)

    # 文本/解析路径
    from file_parser import parse_file, FileParseError
    # 大文件保护：超过 10 MB 的解析很慢，前端应该改用 raw 流式预览
    if stat.st_size > 10 * 1024 * 1024:
        return jsonify({
            **base_info,
            'error': 'file_too_large',
            'message': f'文件 {stat.st_size // (1024*1024)} MB 超过 10 MB 解析上限，请使用 /api/source/raw 直接预览二进制',
        }), 413
    try:
        text = parse_file(abs_path)
    except FileParseError as exc:
        return jsonify({**base_info, 'error': str(exc)}), 422
    except Exception as exc:
        logger.exception('[preview] parse failed')
        return jsonify({**base_info, 'error': f'解析失败：{exc}'}), 500
    # 长文本截断给前端，避免一次发几兆 JSON
    truncated = False
    max_chars = 50000
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = True
    return jsonify({**base_info, 'text': text, 'truncated': truncated})


@app.route('/api/source/raw', methods=['GET'])
def api_source_raw():
    """流式返回源文档二进制，给浏览器内嵌（PDF / 图片）用。

    query: path=<rel>
    Content-Type 按扩展名映射；其他类型按 application/octet-stream + 强制下载。
    """
    rel = request.args.get('path', '').strip()
    abs_path = _resolve_safe_raw_path(rel)
    if not abs_path:
        return jsonify({'error': 'path 非法或文件不存在'}), 400
    ext = Path(abs_path).suffix.lower()
    mimetype = _RAW_MIME.get(ext, 'application/octet-stream')
    inline = ext in _RAW_MIME  # 已知类型可内嵌；其他强制下载
    return send_from_directory(
        os.path.dirname(abs_path),
        os.path.basename(abs_path),
        mimetype=mimetype,
        as_attachment=not inline,
        download_name=os.path.basename(abs_path),
    )


@app.route('/api/orphans/scan', methods=['GET'])
def api_orphans_scan():
    """扫描当前 wiki，返回 dangling links 与 orphan pages。"""
    from orphan_detector import scan_links
    try:
        return jsonify(scan_links(PROJECT_DIR))
    except Exception as exc:
        logger.exception("[orphan] scan failed")
        return jsonify({'error': str(exc)}), 500


@app.route('/api/orphans/dangling/auto-fill', methods=['POST'])
def api_orphans_auto_fill():
    """为所有 dangling links 自动生成占位页面。

    body: { use_llm?: bool=true, limit?: int }
    use_llm=false 时纯模板化（无 LLM 调用）。
    """
    from orphan_detector import auto_fill_dangling
    data = request.json or {}
    use_llm = bool(data.get('use_llm', True))
    limit = data.get('limit')
    try:
        result = auto_fill_dangling(PROJECT_DIR, use_llm=use_llm, limit=limit)
    except Exception as exc:
        logger.exception("[orphan] auto-fill failed")
        return jsonify({'error': str(exc)}), 500
    try:
        from activity_log import record
        record(PROJECT_DIR, 'orphan_auto_fill', None, {
            'created': len(result.get('created', [])),
            'skipped': len(result.get('skipped', [])),
        })
    except Exception:
        pass
    return jsonify(result)


@app.route('/api/orphans/index/refresh', methods=['POST'])
def api_orphans_index_refresh():
    """把当前孤立页面列表写入 wiki/index.md 的「待整理」区块。"""
    from orphan_detector import mark_orphans_in_index
    try:
        return jsonify(mark_orphans_in_index(PROJECT_DIR))
    except Exception as exc:
        logger.exception("[orphan] index refresh failed")
        return jsonify({'error': str(exc)}), 500


# ==================== 定时任务（P4） ====================

@app.route('/api/schedule/tasks', methods=['GET'])
def api_schedule_list():
    import scheduler as sched
    return jsonify({'tasks': sched.list_tasks(PROJECT_DIR), 'kinds': list(sched.TASK_KINDS.keys())})


@app.route('/api/schedule/tasks', methods=['POST'])
def api_schedule_create():
    import scheduler as sched
    data = request.json or {}
    try:
        task = sched.create_task(
            PROJECT_DIR,
            name=data.get('name', ''),
            kind=data.get('kind', ''),
            schedule=data.get('schedule') or {},
            enabled=bool(data.get('enabled', True)),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(task)


@app.route('/api/schedule/tasks/<task_id>', methods=['PUT'])
def api_schedule_update(task_id):
    import scheduler as sched
    data = request.json or {}
    try:
        task = sched.update_task(PROJECT_DIR, task_id, **data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    if not task:
        return jsonify({'error': 'task not found'}), 404
    return jsonify(task)


@app.route('/api/schedule/tasks/<task_id>', methods=['DELETE'])
def api_schedule_delete(task_id):
    import scheduler as sched
    if not sched.delete_task(PROJECT_DIR, task_id):
        return jsonify({'error': 'task not found'}), 404
    return jsonify({'status': 'ok'})


@app.route('/api/schedule/tasks/<task_id>/run-now', methods=['POST'])
def api_schedule_run_now(task_id):
    import scheduler as sched
    task = sched.run_now(PROJECT_DIR, task_id)
    if not task:
        return jsonify({'error': 'task not found'}), 404
    return jsonify(task)


# 进程启动时挂上 scheduler（依赖 PROJECT_DIR 已 resolve）
def _start_scheduler_once():
    try:
        import scheduler as sched
        sched.start(PROJECT_DIR)
    except Exception as exc:
        logger.warning(f"[scheduler] failed to start at boot: {exc}")


def _start_heartbeat_once():
    try:
        import heartbeat
        heartbeat.start(PROJECT_DIR)
    except Exception as exc:
        logger.warning(f"[heartbeat] failed to start at boot: {exc}")


_start_scheduler_once()
_start_heartbeat_once()


@app.route('/api/themes', methods=['GET'])
def api_themes():
    """获取所有知识库主题"""
    themes = []
    wiki_base = os.path.join(PROJECT_DIR, 'wiki')
    
    if os.path.exists(wiki_base):
        excluded = set(get_wiki_subdirs() + ['prompts'])
        for item in os.listdir(wiki_base):
            item_path = os.path.join(wiki_base, item)
            if os.path.isdir(item_path) and item not in excluded:
                themes.append({
                    'name': item,
                    'path': f'wiki/{item}',
                    'page_count': len([f for f in os.listdir(item_path) if f.endswith('.md')])
                })
    
    return jsonify(themes)


@app.route('/api/themes/<theme>', methods=['GET'])
def api_theme_pages(theme: str):
    """获取指定主题的所有页面"""
    theme_dir = os.path.join(PROJECT_DIR, 'wiki', theme)
    if not os.path.exists(theme_dir):
        return jsonify({'error': 'Theme not found'}), 404
    
    pages = []
    for filename in os.listdir(theme_dir):
        if filename.endswith('.md'):
            file_path = os.path.join(theme_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            meta, body = parse_frontmatter(content)
            slug = filename[:-3]
            pages.append({
                'slug': slug,
                'title': meta.get('title', slug),
                'type': theme,
                'path': f'wiki/{theme}/{filename}',
                'created': meta.get('created', ''),
                'updated': meta.get('updated', ''),
                'tags': meta.get('tags', []),
                'body_preview': body[:200] if body else ''
            })
    
    return jsonify(pages)


if __name__ == '__main__':
    init_wiki()
    # 启动时回填老 admin 用户的 role/unit/title/email 字段（idempotent）
    try:
        from auth import migrate_users
        migrated = migrate_users(PROJECT_DIR)
        if migrated:
            logger.info("auth: 已回填 %d 个老用户字段", migrated)
    except Exception:
        logger.exception("auth: 用户字段迁移失败")
    logger.info("知枢 Wiki 目录：%s", WIKI_DIR)
    logger.info("访问地址：http://localhost:5004")
    app.run(host='0.0.0.0', port=5004, debug=False, use_reloader=False)
