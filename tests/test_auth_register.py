"""auth.py 注册 + 邀请码 + 角色 + 字段迁移的单测。"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# 让 tests/ 能 import 项目根模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class AuthRegisterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "data"), exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── setup_first_user ─────────────────────────────────────────

    def test_setup_first_user_writes_admin_role_and_required_fields(self):
        from auth import setup_first_user, get_user

        user = setup_first_user(self.tmp, "alice", "password123",
                                unit="网安大队", title="队长", email="a@x.com")
        self.assertEqual(user["role"], "admin")
        self.assertEqual(user["unit"], "网安大队")
        self.assertEqual(user["title"], "队长")
        self.assertEqual(user["email"], "a@x.com")
        # 公共字段不含密码哈希
        self.assertNotIn("password_hash", user)
        # 落盘后再读
        loaded = get_user(self.tmp, "alice")
        self.assertEqual(loaded["role"], "admin")

    def test_setup_first_user_blocked_when_user_exists(self):
        from auth import setup_first_user

        setup_first_user(self.tmp, "alice", "password123", unit="x", title="y")
        with self.assertRaises(PermissionError):
            setup_first_user(self.tmp, "bob", "password123", unit="x", title="y")

    # ── register_user ────────────────────────────────────────────

    def test_register_requires_invite(self):
        from auth import setup_first_user, register_user

        setup_first_user(self.tmp, "admin", "password123", unit="x", title="y")
        with self.assertRaises(ValueError) as ctx:
            register_user(self.tmp, invite_code="ABCD1234",
                          username="bob", password="secretX1",
                          unit="刑警队", title="干警")
        self.assertIn("不存在", str(ctx.exception))

    def test_register_consumes_invite_and_creates_member(self):
        from auth import setup_first_user, create_invite, register_user, get_user, list_invites

        setup_first_user(self.tmp, "admin", "password123", unit="x", title="y")
        invite = create_invite(self.tmp, created_by="admin", note="给小张")
        new_user = register_user(self.tmp, invite_code=invite["code"],
                                 username="zhang", password="secretX1",
                                 unit="刑警队", title="干警")
        self.assertEqual(new_user["role"], "member")
        self.assertEqual(new_user["unit"], "刑警队")
        # 邀请码已标为已用
        invites = list_invites(self.tmp)
        used = next(iv for iv in invites if iv["code"] == invite["code"])
        self.assertEqual(used["used_by"], "zhang")
        self.assertIsNotNone(used["used_at"])
        # 用户落盘
        self.assertEqual(get_user(self.tmp, "zhang")["role"], "member")

    def test_register_rejects_used_invite(self):
        from auth import setup_first_user, create_invite, register_user

        setup_first_user(self.tmp, "admin", "password123", unit="x", title="y")
        invite = create_invite(self.tmp, created_by="admin")
        register_user(self.tmp, invite_code=invite["code"],
                      username="a", password="secretX1", unit="x", title="y")
        with self.assertRaises(ValueError) as ctx:
            register_user(self.tmp, invite_code=invite["code"],
                          username="b", password="secretX1", unit="x", title="y")
        self.assertIn("已被使用", str(ctx.exception))

    def test_register_rejects_duplicate_username(self):
        from auth import setup_first_user, create_invite, register_user

        setup_first_user(self.tmp, "admin", "password123", unit="x", title="y")
        invite = create_invite(self.tmp, created_by="admin")
        with self.assertRaises(ValueError) as ctx:
            register_user(self.tmp, invite_code=invite["code"],
                          username="admin", password="secretX1",
                          unit="x", title="y")
        self.assertIn("用户名已被占用", str(ctx.exception))

    def test_register_validates_required_unit_title(self):
        from auth import setup_first_user, create_invite, register_user

        setup_first_user(self.tmp, "admin", "password123", unit="x", title="y")
        invite = create_invite(self.tmp, created_by="admin")
        with self.assertRaises(ValueError):
            register_user(self.tmp, invite_code=invite["code"],
                          username="bob", password="secretX1", unit="", title="y")
        invite2 = create_invite(self.tmp, created_by="admin")
        with self.assertRaises(ValueError):
            register_user(self.tmp, invite_code=invite2["code"],
                          username="bob", password="secretX1", unit="x", title="")

    def test_register_validates_email_format_when_provided(self):
        from auth import setup_first_user, create_invite, register_user

        setup_first_user(self.tmp, "admin", "password123", unit="x", title="y")
        invite = create_invite(self.tmp, created_by="admin")
        with self.assertRaises(ValueError):
            register_user(self.tmp, invite_code=invite["code"],
                          username="bob", password="secretX1",
                          unit="x", title="y", email="not-an-email")

    # ── 邀请码 CRUD ───────────────────────────────────────────────

    def test_revoke_unused_invite_succeeds_and_used_invite_blocks(self):
        from auth import setup_first_user, create_invite, revoke_invite, register_user, list_invites

        setup_first_user(self.tmp, "admin", "password123", unit="x", title="y")
        unused = create_invite(self.tmp, created_by="admin", note="未用")
        used = create_invite(self.tmp, created_by="admin", note="将被用")
        register_user(self.tmp, invite_code=used["code"],
                      username="a", password="secretX1", unit="x", title="y")

        self.assertTrue(revoke_invite(self.tmp, unused["code"]))
        with self.assertRaises(ValueError):
            revoke_invite(self.tmp, used["code"])

        codes = {iv["code"] for iv in list_invites(self.tmp)}
        self.assertNotIn(unused["code"], codes)
        self.assertIn(used["code"], codes)

    # ── 角色判断 ─────────────────────────────────────────────────

    def test_is_admin_resolves_role(self):
        from auth import setup_first_user, create_invite, register_user, is_admin

        setup_first_user(self.tmp, "admin", "password123", unit="x", title="y")
        invite = create_invite(self.tmp, created_by="admin")
        register_user(self.tmp, invite_code=invite["code"],
                      username="bob", password="secretX1", unit="x", title="y")

        self.assertTrue(is_admin(self.tmp, "admin"))
        self.assertFalse(is_admin(self.tmp, "bob"))
        self.assertFalse(is_admin(self.tmp, "ghost"))
        self.assertFalse(is_admin(self.tmp, None))

    # ── 老用户字段迁移 ───────────────────────────────────────────

    def test_migrate_users_backfills_legacy_admin(self):
        """模拟老 users.json：只有 username/password_hash/created_at，无 role/unit/title/email。"""
        import json
        from werkzeug.security import generate_password_hash
        from auth import migrate_users, get_user, is_admin

        legacy = [{
            "username": "legacy_admin",
            "password_hash": generate_password_hash("password123"),
            "created_at": "2025-01-01T00:00:00",
        }]
        users_path = Path(self.tmp) / "data" / "users.json"
        users_path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")

        changed = migrate_users(self.tmp)
        self.assertGreater(changed, 0)
        u = get_user(self.tmp, "legacy_admin")
        self.assertEqual(u["role"], "admin")  # 第一个用户回填为 admin
        self.assertEqual(u["unit"], "")
        self.assertTrue(is_admin(self.tmp, "legacy_admin"))

        # 二次调用应该幂等（changed = 0）
        self.assertEqual(migrate_users(self.tmp), 0)


if __name__ == "__main__":
    unittest.main()
