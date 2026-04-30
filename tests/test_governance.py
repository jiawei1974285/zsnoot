import os
import shutil
import tempfile
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


class GovernanceTests(unittest.TestCase):
    def tearDown(self):
        tmp = getattr(self, "_tmp", None)
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_manual_wiki_write_routes_are_forbidden(self):
        import app

        with mock.patch("auth.current_username", return_value="tester"):
            response = app.app.test_client().post(
                "/api/wiki/pages",
                json={"slug": "manual-note", "type": "notes", "meta": {"title": "Manual"}, "body": "body"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "Wiki pages are agent-owned and read-only")

    def test_auto_saved_qa_uses_unique_output_files(self):
        import app

        self._tmp = make_tmp_dir("qa-output")
        wiki_dir = self._tmp / "wiki"
        with mock.patch.object(app, "PROJECT_DIR", str(self._tmp)), mock.patch.object(app, "WIKI_DIR", str(wiki_dir)):
            first = app.auto_save_qa("same question", "first answer", [])
            second = app.auto_save_qa("same question", "second answer", [])

        output_files = sorted((wiki_dir / "outputs").glob("*.md"))
        self.assertEqual(len(output_files), 2)
        self.assertNotEqual(first["slug"], second["slug"])

    def test_raw_archive_records_checksum_and_detects_changes(self):
        from ingest_service import RawIntegrityError, archive_uploads, verify_archived_files

        class FakeUpload:
            filename = "source.txt"

            def save(self, target):
                Path(target).write_text("original", encoding="utf-8")

        self._tmp = make_tmp_dir("raw-archive")
        archived = archive_uploads([FakeUpload()], "batch-1", str(self._tmp))
        item = archived[0]

        self.assertIn("sha256", item)
        self.assertEqual(item["size"], len("original".encode("utf-8")))
        verify_archived_files(archived, str(self._tmp))

        source = self._tmp / item["path"]
        source.write_text("changed", encoding="utf-8")
        with self.assertRaises(RawIntegrityError):
            verify_archived_files(archived, str(self._tmp))

    def test_agent_generated_wiki_pages_are_logged(self):
        import auto_ingest

        self._tmp = make_tmp_dir("agent-log")
        with mock.patch.object(auto_ingest, "PROJECT_DIR", str(self._tmp)), mock.patch.object(auto_ingest, "WIKI_DIR", str(self._tmp / "wiki")):
            generated = auto_ingest._write_blocks_to_disk([
                {
                    "path": "wiki/notes/generated.md",
                    "meta": {"type": "note", "title": "Generated"},
                    "content": "---\ntype: note\ntitle: Generated\n---\n# Generated\n",
                }
            ])

        log_text = (self._tmp / "wiki" / "log.md").read_text(encoding="utf-8")
        self.assertEqual(generated, ["wiki/notes/generated.md"])
        self.assertIn("agent_generate_page", log_text)


if __name__ == "__main__":
    unittest.main()
