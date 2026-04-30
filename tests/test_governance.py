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

    def test_agent_owned_wiki_pages_can_still_be_deleted_from_cards(self):
        import app

        self._tmp = make_tmp_dir("wiki-delete")
        wiki_dir = self._tmp / "wiki"
        notes_dir = wiki_dir / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        page_path = notes_dir / "delete-me.md"
        page_path.write_text("---\ntitle: Delete Me\n---\n# Delete Me\n", encoding="utf-8")

        with mock.patch.object(app, "PROJECT_DIR", str(self._tmp)), \
             mock.patch.object(app, "WIKI_DIR", str(wiki_dir)), \
             mock.patch("auth.current_username", return_value="tester"):
            response = app.app.test_client().delete("/api/wiki/pages/delete-me?type=notes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["deleted"], "delete-me")
        self.assertFalse(page_path.exists())

    def test_wiki_pages_include_last_import_time_and_sort_by_it(self):
        import app

        self._tmp = make_tmp_dir("wiki-import-sort")
        wiki_dir = self._tmp / "wiki"
        notes_dir = wiki_dir / "notes"
        data_dir = self._tmp / "data"
        notes_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        (notes_dir / "older.md").write_text("---\ntitle: Older\nupdated: 2026-04-30\n---\n# Older\n", encoding="utf-8")
        (notes_dir / "newer.md").write_text("---\ntitle: Newer\nupdated: 2026-04-29\n---\n# Newer\n", encoding="utf-8")
        (data_dir / "ingest_batches.json").write_text(
            """[
  {
    "id": "batch-new",
    "created_at": "2026-04-30T10:00:00",
    "updated_at": "2026-04-30T10:05:00",
    "generated_files": ["wiki/notes/newer.md"]
  },
  {
    "id": "batch-old",
    "created_at": "2026-04-29T10:00:00",
    "updated_at": "2026-04-29T10:05:00",
    "generated_files": ["wiki/notes/older.md"]
  }
]""",
            encoding="utf-8",
        )

        with mock.patch.object(app, "PROJECT_DIR", str(self._tmp)), mock.patch.object(app, "WIKI_DIR", str(wiki_dir)):
            pages = app.get_wiki_pages("notes")

        self.assertEqual([page["slug"] for page in pages], ["newer", "older"])
        self.assertEqual(pages[0]["last_imported_at"], "2026-04-30T10:05:00")
        self.assertEqual(pages[0]["last_import_batch_id"], "batch-new")

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

    def test_manual_note_creation_extracts_relations_and_links_into_graph(self):
        import app
        import graph
        import note_intake

        self._tmp = make_tmp_dir("note-intake")
        wiki_dir = self._tmp / "wiki"
        for subdir in app.DEFAULT_WIKI_SUBDIRS:
            (wiki_dir / subdir).mkdir(parents=True, exist_ok=True)
        (wiki_dir / "log.md").write_text("# log\n", encoding="utf-8")

        with mock.patch.object(app, "PROJECT_DIR", str(self._tmp)), \
             mock.patch.object(app, "WIKI_DIR", str(wiki_dir)), \
             mock.patch.object(graph, "PROJECT_DIR", str(self._tmp)), \
             mock.patch.object(graph, "WIKI_DIR", str(wiki_dir)):
            result = note_intake.build_note_pages(
                str(self._tmp),
                "关系记录",
                "黄超和何思雨是夫妻。",
                tags=["手工笔记"],
            )
            graph_data = graph.build_graph(force_refresh=True)

        self.assertEqual(len(result["relations"]), 1)
        self.assertEqual(result["relations"][0]["relation"], "夫妻")
        self.assertTrue((wiki_dir / "persons" / "黄超.md").exists())
        self.assertTrue((wiki_dir / "persons" / "何思雨.md").exists())
        self.assertTrue(any(node["id"] == "黄超" for node in graph_data["nodes"]))
        self.assertTrue(any(node["id"] == "何思雨" for node in graph_data["nodes"]))
        self.assertTrue(
            any(
                {
                    edge["source"],
                    edge["target"],
                } == {"黄超", "何思雨"} and edge.get("relation") == "夫妻"
                for edge in graph_data["edges"]
            )
        )

    def test_notes_api_uses_agent_owned_creation_flow(self):
        import app

        self._tmp = make_tmp_dir("notes-api")
        wiki_dir = self._tmp / "wiki"
        for subdir in app.DEFAULT_WIKI_SUBDIRS:
            (wiki_dir / subdir).mkdir(parents=True, exist_ok=True)
        (wiki_dir / "log.md").write_text("# log\n", encoding="utf-8")

        with mock.patch.object(app, "PROJECT_DIR", str(self._tmp)), \
             mock.patch.object(app, "WIKI_DIR", str(wiki_dir)), \
             mock.patch("auth.current_username", return_value="tester"):
            response = app.app.test_client().post(
                "/api/notes",
                json={"title": "关系备注", "content": "黄超和何思雨是夫妻。", "tags": ["手工"]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["relations"][0]["relation"], "夫妻")
        self.assertTrue((wiki_dir / "notes" / f"{payload['slug']}.md").exists())

    def test_chat_sources_include_page_links(self):
        import app

        local_answer = {
            "response": "found",
            "sources": [
                {"slug": "case-a", "type": "cases", "title": "Case A"},
            ],
        }

        with mock.patch("auth.current_username", return_value="tester"), \
             mock.patch.object(app, "answer_structured_local_query", return_value=local_answer), \
             mock.patch.object(app, "auto_save_qa", return_value=None):
            response = app.app.test_client().post("/api/chat", json={"query": "case a"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["sources"], [{"slug": "case-a", "type": "cases", "title": "Case A"}])

    def test_reparse_merges_generated_page_with_existing_content(self):
        import auto_ingest

        self._tmp = make_tmp_dir("reparse-merge")
        page_path = self._tmp / "wiki" / "persons" / "person-a.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(
            "---\ntype: person\ntitle: Person A\ntags:\n- old\nrelations:\n- source: Person A\n  target: Person B\n  relation: friend\n---\n# Person A\n\nold fact\n",
            encoding="utf-8",
        )

        with mock.patch.object(auto_ingest, "PROJECT_DIR", str(self._tmp)), \
             mock.patch.object(auto_ingest, "WIKI_DIR", str(self._tmp / "wiki")):
            generated = auto_ingest._write_blocks_to_disk([
                {
                    "path": "wiki/persons/person-a.md",
                    "meta": {
                        "type": "person",
                        "title": "Person A",
                        "tags": ["new"],
                        "relations": [
                            {"source": "Person A", "target": "Person B", "relation": "friend"},
                            {"source": "Person A", "target": "Person C", "relation": "colleague"},
                        ],
                    },
                    "content": "---\ntype: person\ntitle: Person A\n---\n# Person A\n\nnew fact\n",
                }
            ])

        self.assertEqual(generated, ["wiki/persons/person-a.md"])
        content = page_path.read_text(encoding="utf-8")
        self.assertIn("old fact", content)
        self.assertIn("new fact", content)
        meta, _ = auto_ingest.parse_frontmatter(content)
        self.assertEqual(meta["tags"], ["old", "new"])
        self.assertEqual(
            meta["relations"],
            [
                {"source": "Person A", "target": "Person B", "relation": "friend"},
                {"source": "Person A", "target": "Person C", "relation": "colleague"},
            ],
        )

    def test_reparse_batch_reuses_archived_files_and_merges_batch_results(self):
        import app
        import ingest_service
        from ingest_batches import IngestBatchStore

        self._tmp = make_tmp_dir("reparse-batch")
        raw = self._tmp / "raw" / "sources" / "batch-1" / "case.md"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text("source", encoding="utf-8")
        store = IngestBatchStore(self._tmp / "data")
        batch = store.create_batch(["case.md"])
        store.update_batch(
            batch["id"],
            status="completed",
            original_files=[{"name": "case.md", "path": "raw/sources/batch-1/case.md"}],
            generated_files=["wiki/cases/old.md"],
            entities=[{"name": "Old", "type": "case"}],
            links=[{"from": "Old", "to": "Known"}],
        )

        calls = []

        def fake_process(project_dir, original, **kwargs):
            calls.append({"original": original, "kwargs": {}})
            return {
                "file_name": original["name"],
                "generated_files": ["wiki/cases/old.md", "wiki/persons/new.md"],
                "entities": [{"name": "Old", "type": "case"}, {"name": "New", "type": "person"}],
                "error": None,
                "log_message": "reparsed",
                "elapsed_ms": 1,
            }

        with mock.patch.object(app, "PROJECT_DIR", str(self._tmp)), \
             mock.patch("auth.current_username", return_value="tester"), \
             mock.patch.object(ingest_service, "_process_one_file", side_effect=fake_process), \
             mock.patch("agent_status.set_status", return_value=None):
            response = app.app.test_client().post(f"/api/ingest/batches/{batch['id']}/reparse")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["generated_files"], ["wiki/cases/old.md", "wiki/persons/new.md"])
        self.assertEqual(payload["entities"], [{"name": "Old", "type": "case"}, {"name": "New", "type": "person"}])

    def test_reparse_batch_passes_prior_context_to_llm_processing(self):
        import ingest_service
        from ingest_batches import IngestBatchStore

        self._tmp = make_tmp_dir("reparse-context")
        raw = self._tmp / "raw" / "sources" / "batch-1" / "case.md"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text("source", encoding="utf-8")
        store = IngestBatchStore(self._tmp / "data")
        batch = store.create_batch(["case.md"])
        store.update_batch(
            batch["id"],
            status="completed",
            original_files=[{"name": "case.md", "path": "raw/sources/batch-1/case.md"}],
            generated_files=["wiki/cases/old.md"],
            entities=[{"name": "Old", "type": "case"}],
            links=[{"from": "Old", "to": "Known"}],
        )

        calls = []

        def fake_process(project_dir, original, **kwargs):
            calls.append(kwargs)
            return {
                "file_name": original["name"],
                "generated_files": ["wiki/persons/new.md"],
                "entities": [{"name": "New", "type": "person"}],
                "error": None,
                "log_message": "deep reparse",
                "elapsed_ms": 1,
            }

        with mock.patch.object(ingest_service, "_process_one_file", side_effect=fake_process), \
             mock.patch("agent_status.set_status", return_value=None):
            result = ingest_service.reparse_batch(batch["id"], str(self._tmp), store=store)

        self.assertEqual(result["generated_files"], ["wiki/cases/old.md", "wiki/persons/new.md"])
        self.assertEqual(calls[0]["mode"], "reparse")
        self.assertIn("wiki/cases/old.md", calls[0]["reparse_context"])
        self.assertIn("Old", calls[0]["reparse_context"])

    def test_reparse_context_changes_auto_ingest_prompt(self):
        import auto_ingest

        prompt = auto_ingest.build_unified_prompt(
            "schema",
            "purpose",
            "source text",
            ".pdf",
            '{"existing_entities": [{"name": "Old"}]}',
        )

        self.assertIn("再次解析补充模式", prompt)
        self.assertIn("不要只复刻上一次的概要", prompt)
        self.assertIn("Old", prompt)

    def test_ingest_runtime_defaults_to_five_workers(self):
        import ingest_service

        self._tmp = make_tmp_dir("ingest-config")
        config_dir = self._tmp / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        runtime = ingest_service._ingest_runtime_config(str(self._tmp))
        self.assertEqual(runtime["max_workers"], 5)

        (config_dir / "config.yaml").write_text("ingest:\n  max_workers: 7\n", encoding="utf-8")
        runtime = ingest_service._ingest_runtime_config(str(self._tmp))
        self.assertEqual(runtime["max_workers"], 7)


if __name__ == "__main__":
    unittest.main()
