#!/usr/bin/env python3
"""把本机 agent 绑定到某 cloud 用户（P2-B）。

使用：
    python -m scripts.bind_user status              # 查看当前绑定
    python -m scripts.bind_user bind <username>     # 绑定到指定用户名
    python -m scripts.bind_user unbind              # 解除绑定（恢复 legacy 模式）

注意：
  1. 绑定生效需要重启本机 agent（Flask 进程）。
  2. 本工具不验证 cloud 端是否存在该用户——它只在本机写绑定。
     真正的安全闸门在 agent 中：JWT 解码后必须 sub == 绑定的 username，
     否则 403。
  3. `~/.handynotes/<username>/` 会在绑定时创建并补齐子目录。
"""
from __future__ import annotations

import os
import sys


# 让脚本能 import 项目根的 user_data
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from user_data import (  # noqa: E402
    bind_machine_to,
    current_bound_user,
    get_install_dir,
    get_user_data_dir,
    is_legacy_mode,
    unbind_machine,
)


def cmd_status() -> int:
    user = current_bound_user()
    print(f"install dir : {get_install_dir()}")
    print(f"user data   : {get_user_data_dir()}")
    if user:
        print(f"bound user  : {user}")
        print("mode        : per-user (P2-B)")
    else:
        print("bound user  : (none)")
        print("mode        : legacy (data == install dir)")
    return 0


def cmd_bind(username: str) -> int:
    if not username:
        print("usage: python -m scripts.bind_user bind <username>", file=sys.stderr)
        return 2
    user_dir = bind_machine_to(username)
    print(f"OK. bound to '{username}'")
    print(f"   user data dir: {user_dir}")
    print("   restart the agent (python app.py) for the binding to take effect.")
    return 0


def cmd_unbind() -> int:
    if is_legacy_mode():
        print("not bound; nothing to do.")
        return 0
    user = current_bound_user()
    unbind_machine()
    print(f"OK. unbound from '{user}'. agent will fall back to legacy mode after restart.")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return 0
    cmd, *rest = argv
    if cmd == "status":
        return cmd_status()
    if cmd == "bind":
        return cmd_bind((rest[0] if rest else "").strip())
    if cmd == "unbind":
        return cmd_unbind()
    print(f"unknown command: {cmd}", file=sys.stderr)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
