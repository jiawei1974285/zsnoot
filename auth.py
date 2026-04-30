#!/usr/bin/env python3
"""本地多用户门禁 —— 用户 + 邀请码 + 中间件。

用户模型 (data/users.json)：
  username / password_hash / role: admin|member / unit / title / email / created_at

邀请码模型 (data/invite_codes.json)：
  code (8 位短码) / created_at / created_by / note / used_at / used_by

设计：首个 setup 出来的用户 role=admin；后续注册必须用 admin 生成的一次性邀请码，
注册成功后角色固定为 member。这是 plan 决策项 2「注册需邀请码」的落地。
"""
import json
import os
import re
import secrets
from datetime import datetime
from functools import wraps
from typing import Dict, List, Optional

from flask import jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 去掉易混 O/0/I/1


# ════════════════════════ users.json ════════════════════════

def _users_path(project_dir: str) -> str:
    return os.path.join(project_dir, "data", "users.json")


def _load_users(project_dir: str) -> List[Dict]:
    path = _users_path(project_dir)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except (json.JSONDecodeError, OSError):
        return []


def _save_users(project_dir: str, users: List[Dict]) -> None:
    path = _users_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def has_any_user(project_dir: str) -> bool:
    return len(_load_users(project_dir)) > 0


def migrate_users(project_dir: str) -> int:
    """启动时调用：给老用户记录回填 role/unit/title/email 字段。

    具体行为：
      - 没 role 的用户：第一个（按 created_at）→ admin，其余 → member
      - 没 unit/title/email 的用户：填空字符串
    返回回填的用户数（用于日志）。
    """
    users = _load_users(project_dir)
    if not users:
        return 0
    changed = 0
    sorted_users = sorted(users, key=lambda u: u.get("created_at", ""))
    first_username = sorted_users[0].get("username") if sorted_users else None
    for user in users:
        if "role" not in user or not user.get("role"):
            user["role"] = "admin" if user.get("username") == first_username else "member"
            changed += 1
        for k in ("unit", "title", "email"):
            if k not in user:
                user[k] = ""
                changed += 1
    if changed:
        _save_users(project_dir, users)
    return changed


def _public_user(user: Dict) -> Dict:
    """返回不含密码哈希的安全副本。"""
    return {
        "username": user.get("username"),
        "role": user.get("role", "member"),
        "unit": user.get("unit", ""),
        "title": user.get("title", ""),
        "email": user.get("email", ""),
        "created_at": user.get("created_at"),
    }


def _validate_required(unit: str, title: str, email: str) -> None:
    if not unit or not unit.strip():
        raise ValueError("单位不能为空")
    if not title or not title.strip():
        raise ValueError("职务不能为空")
    if email and not _EMAIL_RE.match(email.strip()):
        raise ValueError("邮箱格式不正确")


def setup_first_user(project_dir: str, username: str, password: str,
                     unit: str = "", title: str = "", email: str = "") -> Dict:
    """仅当 users.json 为空时允许首次注册。首位用户 role=admin。

    旧调用方（不传 unit/title/email）保持兼容：留空字段，admin 可后续在
    「个人资料」补填（TODO 待实现）。
    """
    if has_any_user(project_dir):
        raise PermissionError("已存在用户,无法重复初始化")
    if not username or not password:
        raise ValueError("用户名和密码不能为空")
    if len(password) < 6:
        raise ValueError("密码至少 6 位")
    user = {
        "username": username.strip(),
        "password_hash": generate_password_hash(password),
        "role": "admin",
        "unit": (unit or "").strip(),
        "title": (title or "").strip(),
        "email": (email or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save_users(project_dir, [user])
    return _public_user(user)


def register_user(project_dir: str, invite_code: str, username: str, password: str,
                  unit: str, title: str, email: str = "") -> Dict:
    """凭邀请码注册新成员。原子性：先校验、后写、再标记码为已用。"""
    if not username or not username.strip():
        raise ValueError("用户名不能为空")
    if len(password) < 6:
        raise ValueError("密码至少 6 位")
    _validate_required(unit, title, email)

    code = (invite_code or "").strip().upper()
    if not code:
        raise ValueError("缺少邀请码")

    invites = _load_invites(project_dir)
    invite = next((iv for iv in invites if iv.get("code") == code), None)
    if not invite:
        raise ValueError("邀请码不存在")
    if invite.get("used_at"):
        raise ValueError("邀请码已被使用")

    users = _load_users(project_dir)
    uname = username.strip()
    if any(u.get("username") == uname for u in users):
        raise ValueError("用户名已被占用")

    user = {
        "username": uname,
        "password_hash": generate_password_hash(password),
        "role": "member",
        "unit": unit.strip(),
        "title": title.strip(),
        "email": (email or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    users.append(user)
    _save_users(project_dir, users)

    # 标记邀请码为已用
    invite["used_at"] = user["created_at"]
    invite["used_by"] = uname
    _save_invites(project_dir, invites)

    return _public_user(user)


def verify_login(project_dir: str, username: str, password: str) -> Optional[Dict]:
    users = _load_users(project_dir)
    for user in users:
        if user.get("username") == username and check_password_hash(
            user.get("password_hash", ""), password
        ):
            return _public_user(user)
    return None


def get_user(project_dir: str, username: str) -> Optional[Dict]:
    """读取 user 公共字段（不含密码哈希）。"""
    users = _load_users(project_dir)
    for user in users:
        if user.get("username") == username:
            return _public_user(user)
    return None


def is_admin(project_dir: str, username: Optional[str]) -> bool:
    if not username:
        return False
    user = get_user(project_dir, username)
    return bool(user and user.get("role") == "admin")


def change_password(project_dir: str, username: str, old_password: str, new_password: str) -> bool:
    users = _load_users(project_dir)
    if len(new_password) < 6:
        raise ValueError("新密码至少 6 位")
    for user in users:
        if user.get("username") == username:
            if not check_password_hash(user.get("password_hash", ""), old_password):
                return False
            user["password_hash"] = generate_password_hash(new_password)
            user["password_changed_at"] = datetime.now().isoformat(timespec="seconds")
            _save_users(project_dir, users)
            return True
    return False


def current_username() -> Optional[str]:
    return session.get("user")


# ════════════════════════ invite_codes.json ════════════════════════

def _invites_path(project_dir: str) -> str:
    return os.path.join(project_dir, "data", "invite_codes.json")


def _load_invites(project_dir: str) -> List[Dict]:
    path = _invites_path(project_dir)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except (json.JSONDecodeError, OSError):
        return []


def _save_invites(project_dir: str, invites: List[Dict]) -> None:
    path = _invites_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(invites, f, ensure_ascii=False, indent=2)


def _generate_code() -> str:
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))


def list_invites(project_dir: str) -> List[Dict]:
    """admin 用，列出所有邀请码（最新在前）。"""
    invites = _load_invites(project_dir)
    return sorted(invites, key=lambda x: x.get("created_at", ""), reverse=True)


def create_invite(project_dir: str, created_by: str, note: str = "") -> Dict:
    """生成新邀请码。重复几乎不可能（8 位 32^8 ≈ 1e12），但为保险起见检测并重试。"""
    invites = _load_invites(project_dir)
    existing = {iv.get("code") for iv in invites}
    for _ in range(10):
        code = _generate_code()
        if code not in existing:
            break
    else:
        raise RuntimeError("生成邀请码失败，请重试")
    invite = {
        "code": code,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "created_by": created_by,
        "note": (note or "").strip(),
        "used_at": None,
        "used_by": None,
    }
    invites.append(invite)
    _save_invites(project_dir, invites)
    return invite


def revoke_invite(project_dir: str, code: str) -> bool:
    """撤销未使用的邀请码。已用过的不可撤（要保留审计痕迹）。"""
    code = (code or "").strip().upper()
    invites = _load_invites(project_dir)
    new_list = []
    removed = False
    for iv in invites:
        if iv.get("code") == code:
            if iv.get("used_at"):
                raise ValueError("邀请码已被使用，不能撤销")
            removed = True
            continue
        new_list.append(iv)
    if removed:
        _save_invites(project_dir, new_list)
    return removed


# ════════════════════════ Flask 中间件 ════════════════════════

def login_required(fn):
    """装饰器：未登录返回 401。"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(project_dir_provider):
    """装饰器工厂：要求当前用户是 admin。

    用法：
        @admin_required(lambda: PROJECT_DIR)
        def view(): ...

    project_dir_provider 是 callable，让单测能注入临时项目目录。
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user:
                return jsonify({"error": "unauthorized"}), 401
            if not is_admin(project_dir_provider(), user):
                return jsonify({"error": "forbidden", "message": "需要管理员权限"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
