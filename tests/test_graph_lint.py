import shutil
import unittest
import uuid
from pathlib import Path
from unittest import mock


class GraphLintTests(unittest.TestCase):
    def setUp(self):
        root = Path.cwd() / ".test-tmp"
        root.mkdir(parents=True, exist_ok=True)
        self.project_dir = root / f"graph-lint-{uuid.uuid4().hex[:8]}"
        self.project_dir.mkdir(parents=True, exist_ok=False)
        self.wiki_dir = self.project_dir / "wiki"

    def tearDown(self):
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def _write_page(self, subdir, slug, frontmatter, body):
        directory = self.wiki_dir / subdir
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{slug}.md").write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")

    def test_lint_api_reports_wiki_health_without_500(self):
        import app
        import graph

        for subdir in app.DEFAULT_WIKI_SUBDIRS:
            (self.wiki_dir / subdir).mkdir(parents=True, exist_ok=True)
        self._write_page(
            "notes",
            "source",
            "title: Source\nupdated: 2026-04-30\n",
            "# Source\n\nLinks to [[missing-target]].\n",
        )
        self._write_page("notes", "lonely", "title: Lonely\nupdated: 2024-01-01\n", "# Lonely\n")

        with mock.patch.object(app, "PROJECT_DIR", str(self.project_dir)), \
             mock.patch.object(app, "WIKI_DIR", str(self.wiki_dir)), \
             mock.patch.object(graph, "PROJECT_DIR", str(self.project_dir)), \
             mock.patch.object(graph, "WIKI_DIR", str(self.wiki_dir)), \
             mock.patch("auth.current_username", return_value="tester"):
            response = app.app.test_client().get("/api/lint")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["broken_links"], [{"from": "source", "to": "missing-target"}])
        self.assertEqual(payload["orphan_pages"], [{"slug": "lonely", "type": "notes", "title": "Lonely"}])
        self.assertEqual(payload["stale_pages"], [{"slug": "lonely", "type": "notes", "title": "Lonely", "updated": "2024-01-01"}])
        self.assertTrue(payload["suggestions"])

    def test_related_cases_api_returns_linked_cases_without_500(self):
        import app
        import graph

        for subdir in app.DEFAULT_WIKI_SUBDIRS:
            (self.wiki_dir / subdir).mkdir(parents=True, exist_ok=True)
        self._write_page("cases", "case-a", "title: Case A\nupdated: 2026-04-30\n", "# Case A\n\nRelated to [[case-b]].\n")
        self._write_page("cases", "case-b", "title: Case B\nupdated: 2026-04-30\n", "# Case B\n")

        with mock.patch.object(app, "PROJECT_DIR", str(self.project_dir)), \
             mock.patch.object(app, "WIKI_DIR", str(self.wiki_dir)), \
             mock.patch.object(graph, "PROJECT_DIR", str(self.project_dir)), \
             mock.patch.object(graph, "WIKI_DIR", str(self.wiki_dir)), \
             mock.patch("auth.current_username", return_value="tester"):
            response = app.app.test_client().get("/api/cases/case-a/related")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload[0]["slug"], "case-b")
        self.assertEqual(payload[0]["relation_count"], 1)


if __name__ == "__main__":
    unittest.main()
