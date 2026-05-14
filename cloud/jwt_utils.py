"""云端 → 本机 agent 的 JWT 工具。

设计：云端用 HS256 + 共享密钥签发；本机 agent 用同一密钥验签。
密钥来源（优先级）：
  1. 环境变量 MJQ_JWT_SECRET
  2. <project_dir>/config/jwt.secret 文件（启动时自动生成）

Token claims：
  sub:  用户名
  role: admin | member
  iat:  签发时间
  exp:  过期时间（默认 30 分钟）
  typ:  access | refresh

为什么共享密钥而不是非对称：P1 阶段云和本机都是用户自己的环境，部署一次就能把同一密钥同时分发到云端配置和本机 agent；非对称（RS256）等 P2 多机器场景再升级。
"""
from __future__ import annotations

import os
import secrets
import time
from typing import Dict, Optional

import jwt as _jwt


_DEFAULT_TTL_ACCESS = 30 * 60          # 30 min
_DEFAULT_TTL_REFRESH = 30 * 24 * 3600  # 30 day


def _secret_path(project_dir: str) -> str:
    return os.path.join(project_dir, "config", "jwt.secret")


def load_or_create_secret(project_dir: str) -> str:
    """读取或创建 JWT 共享密钥。

    优先环境变量 MJQ_JWT_SECRET，其次 config/jwt.secret 文件，最后随机生成并落盘。
    """
    env = os.environ.get("MJQ_JWT_SECRET", "").strip()
    if env:
        return env
    path = _secret_path(project_dir)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = f.read().strip()
        if len(data) >= 32:
            return data
    os.makedirs(os.path.dirname(path), exist_ok=True)
    secret = secrets.token_hex(32)
    with open(path, "w", encoding="utf-8") as f:
        f.write(secret)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # Windows 可能不支持 chmod
    return secret


def issue_token(secret: str, username: str, role: str, *,
                ttl_seconds: int = _DEFAULT_TTL_ACCESS, typ: str = "access") -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + ttl_seconds,
        "typ": typ,
    }
    return _jwt.encode(payload, secret, algorithm="HS256")


def issue_access(secret: str, username: str, role: str) -> str:
    return issue_token(secret, username, role, ttl_seconds=_DEFAULT_TTL_ACCESS, typ="access")


def issue_refresh(secret: str, username: str, role: str) -> str:
    return issue_token(secret, username, role, ttl_seconds=_DEFAULT_TTL_REFRESH, typ="refresh")


def verify_token(secret: str, token: str, *, expected_typ: Optional[str] = None) -> Dict:
    """验签并返回 claims。失败抛 jwt.InvalidTokenError 子类。

    leeway=60：容许签发方时钟比本机快 60 秒。云端公有云 NTP 准，用户本机
    Windows 时钟常慢几秒到几十秒；没这个 leeway 会被 ImmatureSignatureError
    "token not yet valid (iat)" 拦下——症状是登录成功但所有 API 都 401。
    """
    claims = _jwt.decode(token, secret, algorithms=["HS256"], leeway=60)
    if expected_typ and claims.get("typ") != expected_typ:
        raise _jwt.InvalidTokenError(f"token typ mismatch: expected {expected_typ}, got {claims.get('typ')}")
    return claims


# 为方便上层 try/except，重新导出常用异常
InvalidTokenError = _jwt.InvalidTokenError
ExpiredSignatureError = _jwt.ExpiredSignatureError
