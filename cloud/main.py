#!/usr/bin/env python3
"""mjq-handynotes 云端控制面 —— Flask 服务（P1）。

启动：
    cd <project_root>
    python -m cloud.main           # 默认监听 0.0.0.0:5005
    # 或
    MJQ_CLOUD_PORT=8080 python -m cloud.main

数据存储：cloud/data/users.json + cloud/data/invite_codes.json
（直接复用根目录 auth.py 的逻辑，仅 project_dir 指向 cloud/）

P1 路由：
  GET    /api/cloud/health
  GET    /api/cloud/auth/status      （读 cookie / Bearer，返回登录态）
  POST   /api/cloud/auth/setup       （首位 admin）
  POST   /api/cloud/auth/login       → 返回 access + refresh JWT
  POST   /api/cloud/auth/register    （邀请码）
  POST   /api/cloud/auth/refresh     → 用 refresh 换新 access
  POST   /api/cloud/auth/change-password
  POST   /api/cloud/auth/logout      （客户端丢弃 token 即可，这里只记录）
  GET    /api/cloud/admin/invites
  POST   /api/cloud/admin/invites
  DELETE /api/cloud/admin/invites/<code>
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, request


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

# 让 `python -m cloud.main` 能 import 到根目录的 auth.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import auth as auth_lib  # noqa: E402  根目录 auth.py
from cloud import jwt_utils  # noqa: E402
from cloud import templates_service  # noqa: E402  P2 起：schema 模板
from cloud import schema_synth  # noqa: E402  P3 起：schema 合成 agent

CLOUD_DIR = os.path.dirname(os.path.abspath(__file__))


def _cors_origins() -> list[str]:
    """允许跨域的源列表。

    生产部署：MJQ_CLOUD_CORS_ORIGINS=https://app.example.com,http://localhost:5174
    P1 默认放行常见前端 dev 端口 + 本机 agent。
    """
    raw = os.environ.get("MJQ_CLOUD_CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4174",
        "http://127.0.0.1:4174",
    ]


def _bearer_token() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip() or None
    return None


def create_app() -> Flask:
    app = Flask(__name__)

    # JWT 共享密钥（与本机 agent 用同一份）
    secret = jwt_utils.load_or_create_secret(_PROJECT_ROOT)
    app.config["MJQ_JWT_SECRET"] = secret

    # 启动时给历史 users 回填 role/unit/title/email
    auth_lib.migrate_users(CLOUD_DIR)

    cors_origins = _cors_origins()

    @app.after_request
    def _apply_cors(resp):
        origin = request.headers.get("Origin", "")
        if origin and origin in cors_origins:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return resp

    @app.route("/api/cloud/health", methods=["GET"])
    def health():
        """健康检查 + 能力披露。前端用于亮云端连接状态灯。"""
        from cloud import templates_service, schema_synth as _ss, llm as _llm
        return jsonify({
            "status": "ok",
            "service": "mjq-cloud",
            "phase": "P5",
            "templates": templates_service.list_template_keys(),
            "schema_synth": {
                "available": True,
                "llm_configured": _llm.is_configured(),
            },
            "now": _now_iso(),
        })

    # OPTIONS 统一处理（CORS 预检）
    @app.route("/api/cloud/<path:_subpath>", methods=["OPTIONS"])
    def _cors_preflight(_subpath):
        return ("", 204)

    # ─── auth ────────────────────────────────────────────────
    @app.route("/api/cloud/auth/status", methods=["GET"])
    def api_auth_status():
        token = _bearer_token()
        username = None
        role = None
        profile = {}
        if token:
            try:
                claims = jwt_utils.verify_token(secret, token, expected_typ="access")
                username = claims.get("sub")
                role = claims.get("role")
                # 拿用户的 unit/title/email/template_key 给前端展示
                user = auth_lib.get_user(CLOUD_DIR, username) if username else None
                if user:
                    profile = {
                        "unit": user.get("unit", ""),
                        "title": user.get("title", ""),
                        "email": user.get("email", ""),
                        "template_key": user.get("template_key", ""),
                    }
            except jwt_utils.InvalidTokenError:
                pass
        return jsonify({
            "has_user": auth_lib.has_any_user(CLOUD_DIR),
            "logged_in": bool(username),
            "username": username,
            "role": role,
            **profile,
        })

    @app.route("/api/cloud/auth/setup", methods=["POST"])
    def api_auth_setup():
        if auth_lib.has_any_user(CLOUD_DIR):
            return jsonify({"error": "已存在用户,请使用登录"}), 400
        data = request.json or {}
        template_key = (data.get("template_key") or "").strip() or templates_service.DEFAULT_TEMPLATE_KEY
        if not templates_service.is_known_key(template_key):
            return jsonify({"error": f"未知的模板：{template_key}"}), 400
        try:
            user = auth_lib.setup_first_user(
                CLOUD_DIR,
                username=(data.get("username") or "").strip(),
                password=data.get("password") or "",
                unit=data.get("unit", ""),
                title=data.get("title", ""),
                email=data.get("email", ""),
            )
        except (ValueError, PermissionError) as exc:
            return jsonify({"error": str(exc)}), 400
        # admin 也存 template_key（即首位用户为本机选定的初始 schema）
        auth_lib.update_user_fields(CLOUD_DIR, user["username"], template_key=template_key)
        user["template_key"] = template_key
        access = jwt_utils.issue_access(secret, user["username"], user.get("role", "admin"))
        refresh = jwt_utils.issue_refresh(secret, user["username"], user.get("role", "admin"))
        return jsonify({
            "username": user["username"],
            "role": user.get("role"),
            "unit": user.get("unit", ""),
            "title": user.get("title", ""),
            "email": user.get("email", ""),
            "template_key": template_key,
            "access_token": access,
            "refresh_token": refresh,
        })

    @app.route("/api/cloud/auth/register", methods=["POST"])
    def api_auth_register():
        data = request.json or {}
        template_key = (data.get("template_key") or "").strip()
        if not template_key:
            return jsonify({"error": "请选择一个 schema 模板"}), 400
        if not templates_service.is_known_key(template_key):
            return jsonify({"error": f"未知的模板：{template_key}"}), 400
        try:
            user = auth_lib.register_user(
                CLOUD_DIR,
                invite_code=data.get("invite_code", ""),
                username=data.get("username", ""),
                password=data.get("password", ""),
                unit=data.get("unit", ""),
                title=data.get("title", ""),
                email=data.get("email", ""),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        # 写入用户选定的 template_key，本机 agent 启动时按此从云拉 schema
        auth_lib.update_user_fields(CLOUD_DIR, user["username"], template_key=template_key)
        user["template_key"] = template_key
        access = jwt_utils.issue_access(secret, user["username"], user.get("role", "member"))
        refresh = jwt_utils.issue_refresh(secret, user["username"], user.get("role", "member"))
        return jsonify({
            "username": user["username"],
            "role": user.get("role"),
            "unit": user.get("unit", ""),
            "title": user.get("title", ""),
            "email": user.get("email", ""),
            "template_key": template_key,
            "access_token": access,
            "refresh_token": refresh,
        })

    @app.route("/api/cloud/auth/login", methods=["POST"])
    def api_auth_login():
        data = request.json or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        user = auth_lib.verify_login(CLOUD_DIR, username, password)
        if not user:
            return jsonify({"error": "用户名或密码错误"}), 401
        access = jwt_utils.issue_access(secret, user["username"], user.get("role", "member"))
        refresh = jwt_utils.issue_refresh(secret, user["username"], user.get("role", "member"))
        return jsonify({
            "username": user["username"],
            "role": user.get("role"),
            "unit": user.get("unit", ""),
            "title": user.get("title", ""),
            "email": user.get("email", ""),
            "template_key": user.get("template_key", ""),
            "access_token": access,
            "refresh_token": refresh,
        })

    @app.route("/api/cloud/auth/refresh", methods=["POST"])
    def api_auth_refresh():
        data = request.json or {}
        refresh_token = (data.get("refresh_token") or "").strip()
        if not refresh_token:
            return jsonify({"error": "missing refresh_token"}), 400
        try:
            claims = jwt_utils.verify_token(secret, refresh_token, expected_typ="refresh")
        except jwt_utils.InvalidTokenError as exc:
            return jsonify({"error": f"refresh token invalid: {exc}"}), 401
        username = claims.get("sub")
        # 重新核对用户仍存在（可能已被 admin 删除——P2 才有删除入口，但先严谨）
        user = auth_lib.get_user(CLOUD_DIR, username)
        if not user:
            return jsonify({"error": "user no longer exists"}), 401
        access = jwt_utils.issue_access(secret, user["username"], user.get("role", "member"))
        return jsonify({"access_token": access, "username": user["username"], "role": user.get("role")})

    @app.route("/api/cloud/auth/logout", methods=["POST"])
    def api_auth_logout():
        # 无状态 JWT：客户端丢弃 token 即可。这里只是个语义占位，便于未来加黑名单。
        return jsonify({"status": "ok"})

    @app.route("/api/cloud/auth/change-password", methods=["POST"])
    def api_auth_change_password():
        token = _bearer_token()
        if not token:
            return jsonify({"error": "unauthorized"}), 401
        try:
            claims = jwt_utils.verify_token(secret, token, expected_typ="access")
        except jwt_utils.InvalidTokenError:
            return jsonify({"error": "unauthorized"}), 401
        username = claims.get("sub")
        data = request.json or {}
        try:
            ok = auth_lib.change_password(CLOUD_DIR, username, data.get("old") or "", data.get("new") or "")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if not ok:
            return jsonify({"error": "原密码错误"}), 400
        return jsonify({"status": "ok"})

    # ─── admin: invites ──────────────────────────────────────
    def _require_admin():
        token = _bearer_token()
        if not token:
            return None, (jsonify({"error": "unauthorized"}), 401)
        try:
            claims = jwt_utils.verify_token(secret, token, expected_typ="access")
        except jwt_utils.InvalidTokenError:
            return None, (jsonify({"error": "unauthorized"}), 401)
        if claims.get("role") != "admin":
            return None, (jsonify({"error": "forbidden", "message": "需要管理员权限"}), 403)
        return claims.get("sub"), None

    @app.route("/api/cloud/admin/invites", methods=["GET"])
    def api_admin_invites_list():
        _user, err = _require_admin()
        if err:
            return err
        return jsonify(auth_lib.list_invites(CLOUD_DIR))

    @app.route("/api/cloud/admin/invites", methods=["POST"])
    def api_admin_invites_create():
        user, err = _require_admin()
        if err:
            return err
        note = ((request.json or {}).get("note") or "").strip()
        invite = auth_lib.create_invite(CLOUD_DIR, created_by=user, note=note)
        return jsonify(invite)

    # ─── schema templates ────────────────────────────────────
    @app.route("/api/cloud/schema/templates", methods=["GET"])
    def api_schema_templates():
        """公开：列出所有可选 schema 模板的概览，给注册页选模板用。"""
        return jsonify({"templates": templates_service.list_template_summaries()})

    @app.route("/api/cloud/schema/template/<key>", methods=["GET"])
    def api_schema_template_detail(key):
        """公开：返回指定模板的完整 YAML 内容（注册前预览用）。

        不要求登录是因为模板是公共配置；放给浏览器看的卡片预览。
        """
        data = templates_service.load_template(key)
        if not data:
            return jsonify({"error": f"未知模板：{key}"}), 404
        return jsonify(data)

    @app.route("/api/cloud/schema/me", methods=["GET"])
    def api_schema_me():
        """登录用户的当前 schema 内容 —— 本机 agent 启动后用 Bearer token 拉。

        优先级：custom_schema（用户合成或上传） > template_key（官方模板）。
        """
        token = _bearer_token()
        if not token:
            return jsonify({"error": "unauthorized"}), 401
        try:
            claims = jwt_utils.verify_token(secret, token, expected_typ="access")
        except jwt_utils.InvalidTokenError:
            return jsonify({"error": "unauthorized"}), 401
        username = claims.get("sub")
        # 用 _load_users 拿原始记录（包含 custom_schema 字段），再 _public_user 过滤
        # 不要：我们需要保留 custom_schema，所以直接读
        users = auth_lib._load_users(CLOUD_DIR)
        user = next((u for u in users if u.get("username") == username), None)
        if not user:
            return jsonify({"error": "user not found"}), 404
        custom = user.get("custom_schema")
        if isinstance(custom, dict) and custom.get("wiki_dirs"):
            return jsonify({
                "username": username,
                "template_key": user.get("template_key") or "custom",
                "schema": custom,
                "source": "custom",
            })
        template_key = user.get("template_key") or templates_service.DEFAULT_TEMPLATE_KEY
        data = templates_service.load_template(template_key)
        if not data:
            data = templates_service.load_template(templates_service.DEFAULT_TEMPLATE_KEY)
        return jsonify({
            "username": username,
            "template_key": template_key,
            "schema": data,
            "source": "template",
        })

    # ─── P3：schema synth agent ─────────────────────────────
    def _require_user():
        """登录用户的 username + role；失败返回 (None, response)。"""
        token = _bearer_token()
        if not token:
            return None, (jsonify({"error": "unauthorized"}), 401)
        try:
            claims = jwt_utils.verify_token(secret, token, expected_typ="access")
        except jwt_utils.InvalidTokenError:
            return None, (jsonify({"error": "unauthorized"}), 401)
        return claims, None

    @app.route("/api/cloud/schema/synthesize", methods=["POST"])
    def api_schema_synthesize():
        """用 LLM 合成 schema（不持久化，仅返回预览）。

        body: { goal: str, objects: [str] }
        resp: { schema: {...}, derived_categories: [...], source: 'llm'|'mock' }
        """
        claims, err = _require_user()
        if err:
            return err
        data = request.json or {}
        goal = (data.get("goal") or "").strip()
        objects = data.get("objects") or []
        if not isinstance(objects, list):
            return jsonify({"error": "objects 必须是字符串数组"}), 400
        try:
            result = schema_synth.synthesize(goal, objects)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.route("/api/cloud/schema/apply-custom", methods=["POST"])
    def api_schema_apply_custom():
        """把合成产物（或用户编辑后的版本）持久化为该用户的 custom_schema。

        body: { schema: {...} }   schema 必须含 wiki_dirs（最低要求）
        持久化后下次本机 agent 调 /schema/me 即拿到这份 custom。
        """
        claims, err = _require_user()
        if err:
            return err
        username = claims.get("sub")
        data = request.json or {}
        schema = data.get("schema")
        if not isinstance(schema, dict) or not schema.get("wiki_dirs"):
            return jsonify({"error": "schema.wiki_dirs 缺失或不是 list"}), 400
        # 标记 template_key 为 custom（让前端知晓用户已脱离模板）
        auth_lib.update_user_fields(
            CLOUD_DIR, username,
            template_key="custom",
            custom_schema=schema,
        )
        return jsonify({"status": "ok", "template_key": "custom", "schema_key": schema.get("key")})

    @app.route("/api/cloud/schema/clear-custom", methods=["POST"])
    def api_schema_clear_custom():
        """清除自定义 schema，回退到 template_key 指向的官方模板。

        body: { template_key?: str }   不传则保留原 template_key
        """
        claims, err = _require_user()
        if err:
            return err
        username = claims.get("sub")
        data = request.json or {}
        new_key = (data.get("template_key") or "").strip()
        update = {"custom_schema": {}}  # 空 dict 表示清除
        if new_key and templates_service.is_known_key(new_key):
            update["template_key"] = new_key
        auth_lib.update_user_fields(CLOUD_DIR, username, **update)
        return jsonify({"status": "ok"})

    @app.route("/api/cloud/admin/invites/<code>", methods=["DELETE"])
    def api_admin_invites_revoke(code):
        _user, err = _require_admin()
        if err:
            return err
        try:
            ok = auth_lib.revoke_invite(CLOUD_DIR, code)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if not ok:
            return jsonify({"error": "邀请码不存在"}), 404
        return jsonify({"status": "ok"})

    # ─── P5: 心跳 + admin 控制台 ────────────────────────
    @app.route("/api/cloud/agent/heartbeat", methods=["POST"])
    def api_agent_heartbeat():
        """本机 agent 心跳上报。仅记录"曾连过" + 计数指标，不接收用户语料。"""
        token = _bearer_token()
        if not token:
            return jsonify({"error": "unauthorized"}), 401
        try:
            claims = jwt_utils.verify_token(secret, token, expected_typ="access")
        except jwt_utils.InvalidTokenError:
            return jsonify({"error": "unauthorized"}), 401
        username = claims.get("sub")
        body = request.json or {}
        # 防越权：JWT 的 sub 必须等于 body.username
        if body.get("username") and body["username"] != username:
            return jsonify({"error": "username mismatch"}), 403

        from cloud import heartbeat_store
        # 只接收白名单字段，丢掉客户端塞进来的其他东西
        record = {
            "username": username,
            "agent_version": str(body.get("agent_version") or "")[:32],
            "schema_key": str(body.get("schema_key") or "")[:64],
            "pages_total": int(body.get("pages_total") or 0),
            "last_ingest_at": body.get("last_ingest_at") or None,
            "scheduled_tasks_active": int(body.get("scheduled_tasks_active") or 0),
            "received_at": _now_iso(),
            "client_ip": (request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:45],
        }
        heartbeat_store.write(CLOUD_DIR, username, record)
        return jsonify({"status": "ok"})

    @app.route("/api/cloud/admin/users", methods=["GET"])
    def api_admin_users():
        """admin 控制台的核心数据：用户表 + 各自最近心跳。"""
        _user, err = _require_admin()
        if err:
            return err
        from cloud import heartbeat_store
        users = auth_lib._load_users(CLOUD_DIR)
        beats = heartbeat_store.read_all(CLOUD_DIR)
        out = []
        for u in users:
            uname = u.get("username")
            beat = beats.get(uname) or {}
            out.append({
                "username": uname,
                "role": u.get("role", "member"),
                "unit": u.get("unit", ""),
                "title": u.get("title", ""),
                "email": u.get("email", ""),
                "template_key": u.get("template_key", ""),
                "has_custom_schema": bool(u.get("custom_schema")),
                "created_at": u.get("created_at"),
                # heartbeat 字段（如有）
                "last_heartbeat_at": beat.get("received_at"),
                "agent_version": beat.get("agent_version"),
                "schema_key_runtime": beat.get("schema_key"),
                "pages_total": beat.get("pages_total"),
                "last_ingest_at": beat.get("last_ingest_at"),
                "scheduled_tasks_active": beat.get("scheduled_tasks_active"),
            })
        return jsonify({"users": out, "count": len(out)})

    return app


def main() -> None:
    app = create_app()
    host = os.environ.get("MJQ_CLOUD_HOST", "0.0.0.0")
    port = int(os.environ.get("MJQ_CLOUD_PORT", "5005"))
    debug = os.environ.get("MJQ_CLOUD_DEBUG", "").lower() in {"1", "true", "yes"}
    print(f"[mjq-cloud] listening on {host}:{port} (debug={debug})")
    print(f"[mjq-cloud] CORS origins: {_cors_origins()}")
    print(f"[mjq-cloud] data dir: {os.path.join(CLOUD_DIR, 'data')}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
