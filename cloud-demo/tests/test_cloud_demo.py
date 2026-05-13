import io
import json
import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest import mock


def make_tmp_dir(name: str) -> Path:
    root = Path(os.environ.get("CODEX_TEST_TMP", Path.cwd() / ".test-tmp"))
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class CloudDemoTests(unittest.TestCase):
    def setUp(self):
        import app

        self.tmp = make_tmp_dir("cloud-demo-test")
        self.system_dir = self.tmp / "system"
        self.runtime_dir = self.tmp / "runtime"
        self.system_dir.mkdir(parents=True)
        (self.system_dir / "config").mkdir()
        (self.system_dir / "wiki" / "templates").mkdir(parents=True)
        (self.system_dir / "schema.md").write_text("# schema\n", encoding="utf-8")
        (self.system_dir / "purpose.md").write_text("# purpose\n", encoding="utf-8")
        (self.system_dir / "config" / "config.yaml").write_text("wiki:\n  categories: []\n", encoding="utf-8")

        self.patches = [
            mock.patch.object(app, "SYSTEM_PROJECT_DIR", str(self.system_dir)),
            mock.patch.object(app, "DEMO_RUNTIME_DIR", str(self.runtime_dir)),
            mock.patch.object(app, "DEMO_MODE", True),
            mock.patch.object(app, "DEMO_ALLOW_SETUP", False),
            mock.patch.object(app, "DEMO_MAX_USERS", 2),
            mock.patch.object(app, "DEMO_MAX_UPLOAD_FILES_PER_USER", 20),
        ]
        for patch in self.patches:
            patch.start()
        app._set_active_project_dir(str(self.system_dir))
        self.app = app

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _login_as(self, client, username="alice"):
        from auth import setup_first_user

        setup_first_user(str(self.system_dir), username, "secret123")
        with client.session_transaction() as session:
            session["user"] = username

    def test_cloud_demo_disables_public_setup(self):
        client = self.app.app.test_client()

        response = client.post("/api/auth/setup", json={"username": "admin", "password": "secret123"})

        self.assertEqual(response.status_code, 403)
        self.assertIn("云端体验版", response.get_json()["error"])

    def test_cloud_demo_uses_isolated_user_workspace(self):
        client = self.app.app.test_client()
        self._login_as(client, "alice")

        response = client.get("/api/demo/quota")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["limit"], 20)
        self.assertEqual(payload["used"], 0)
        self.assertTrue((self.runtime_dir / "users" / "alice" / "wiki").exists())
        self.assertTrue((self.runtime_dir / "users" / "alice" / "schema.md").exists())

    def test_cloud_demo_blocks_uploads_over_per_user_limit(self):
        client = self.app.app.test_client()
        self._login_as(client, "alice")
        user_dir = Path(self.app._ensure_demo_workspace("alice"))
        data_dir = user_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        existing = [{"original_files": [{"path": f"raw/sources/batch/file-{idx}.txt"} for idx in range(19)]}]
        (data_dir / "ingest_batches.json").write_text(json.dumps(existing), encoding="utf-8")

        response = client.post(
            "/api/ingest/upload",
            data={
                "files": [
                    (io.BytesIO(b"one"), "one.txt"),
                    (io.BytesIO(b"two"), "two.txt"),
                ]
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 403)
        payload = response.get_json()
        self.assertEqual(payload["demo_quota"]["remaining"], 1)
        self.assertIn("最多上传 20 个文件", payload["error"])

    def test_missing_secret_key_does_not_write_during_import_path(self):
        with mock.patch.object(self.app, "PROJECT_DIR", str(self.system_dir)):
            key = self.app._load_or_create_secret_key()

        self.assertGreaterEqual(len(key), 32)
        self.assertFalse((self.system_dir / "config" / "secret.key").exists())

    def test_agent_status_expires_stale_active_state(self):
        import agent_status

        data_dir = self.system_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "agent_status.json").write_text(
            '{"state":"generating","message":"正在生成知识页面 old.md","detail":{},"updated_at":"2026-05-01T08:53:54"}',
            encoding="utf-8",
        )

        status = agent_status.get_status(str(self.system_dir))

        self.assertEqual(status["state"], "idle")
        self.assertEqual(status["message"], "空闲")
        self.assertEqual(status["detail"]["expired_state"], "generating")

    def test_stats_include_recent_notes(self):
        wiki_dir = self.system_dir / "wiki"
        notes_dir = wiki_dir / "notes"
        data_dir = self.system_dir / "data"
        notes_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        (notes_dir / "older-note.md").write_text(
            "---\ntitle: Older Note\ncreated: 2026-05-01\n---\n# Older Note\n\nold body",
            encoding="utf-8",
        )
        (notes_dir / "new-note.md").write_text(
            "---\ntitle: New Note\ncreated: 2026-05-03\n---\n# New Note\n\nnew body",
            encoding="utf-8",
        )

        with mock.patch.object(self.app, "PROJECT_DIR", str(self.system_dir)), \
             mock.patch.object(self.app, "WIKI_DIR", str(wiki_dir)), \
             self.app.app.app_context():
            response = self.app.api_stats()

        payload = response.get_json()
        self.assertEqual(payload["recent_notes"][0]["slug"], "new-note")
        self.assertEqual(payload["recent_notes"][0]["title"], "New Note")


if __name__ == "__main__":
    unittest.main()
