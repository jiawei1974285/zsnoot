import os
import tempfile
import unittest
from pathlib import Path


class IngestBatchTests(unittest.TestCase):
    def test_record_batch_persists_files_and_generated_outputs(self):
        from ingest_batches import IngestBatchStore

        with tempfile.TemporaryDirectory() as tmp:
            store = IngestBatchStore(tmp)
            batch = store.create_batch(["case.docx"])
            store.update_batch(
                batch["id"],
                status="completed",
                original_files=[{"name": "case.docx", "path": "raw/sources/b1/case.docx"}],
                generated_files=["wiki/cases/case-a.md", "wiki/persons/person-a.md"],
                entities=[{"name": "张某", "type": "person"}],
                links=[{"from": "case-a", "to": "person-a"}],
            )

            batches = store.list_batches()
            detail = store.get_batch(batch["id"])

            self.assertEqual(len(batches), 1)
            self.assertEqual(detail["status"], "completed")
            self.assertEqual(detail["original_files"][0]["name"], "case.docx")
            self.assertEqual(detail["generated_files"], ["wiki/cases/case-a.md", "wiki/persons/person-a.md"])

    def test_delete_batch_removes_only_batch_record(self):
        from ingest_batches import IngestBatchStore

        with tempfile.TemporaryDirectory() as tmp:
            store = IngestBatchStore(tmp)
            first = store.create_batch(["case-a.docx"])
            second = store.create_batch(["case-b.docx"])

            deleted = store.delete_batch(first["id"])

            self.assertEqual(deleted["id"], first["id"])
            self.assertIsNone(store.get_batch(first["id"]))
            self.assertEqual(store.get_batch(second["id"])["id"], second["id"])

    def test_delete_batches_removes_multiple_records(self):
        from ingest_batches import IngestBatchStore

        with tempfile.TemporaryDirectory() as tmp:
            store = IngestBatchStore(tmp)
            first = store.create_batch(["case-a.docx"])
            second = store.create_batch(["case-b.docx"])
            third = store.create_batch(["case-c.docx"])

            deleted = store.delete_batches([first["id"], third["id"]])

            self.assertEqual({item["id"] for item in deleted}, {first["id"], third["id"]})
            self.assertEqual([item["id"] for item in store.list_batches()], [second["id"]])

    def test_rollback_removes_generated_files_but_keeps_original_files(self):
        from ingest_batches import IngestBatchStore
        from ingest_service import rollback_batch

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            original = project_dir / "raw" / "sources" / "batch-1" / "case.md"
            generated = project_dir / "wiki" / "cases" / "case-a.md"
            original.parent.mkdir(parents=True)
            generated.parent.mkdir(parents=True)
            original.write_text("source", encoding="utf-8")
            generated.write_text("---\ntype: case\n---\n# Case", encoding="utf-8")

            store = IngestBatchStore(project_dir / "data")
            batch = store.create_batch(["case.md"])
            store.update_batch(
                batch["id"],
                status="completed",
                original_files=[{"name": "case.md", "path": os.path.relpath(original, project_dir)}],
                generated_files=[os.path.relpath(generated, project_dir)],
            )

            result = rollback_batch(batch["id"], project_dir=str(project_dir), store=store)

            self.assertEqual(result["status"], "rolled_back")
            self.assertTrue(original.exists())
            self.assertFalse(generated.exists())
            self.assertEqual(store.get_batch(batch["id"])["status"], "rolled_back")

    def test_fallback_ingest_creates_note_page_when_llm_fails(self):
        from ingest_service import fallback_generate_wiki_page

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            original = project_dir / "raw" / "sources" / "batch-1" / "source.md"
            original.parent.mkdir(parents=True)
            original.write_text("公安基层智能化应用材料", encoding="utf-8")

            result = fallback_generate_wiki_page(
                project_dir=str(project_dir),
                original={"name": "source.md", "path": "raw/sources/batch-1/source.md"},
                file_content="公安基层智能化应用材料\n用于测试基础入库。",
            )

            generated = project_dir / result["path"]
            self.assertTrue(generated.exists())
            content = generated.read_text(encoding="utf-8")
            self.assertIn("待精炼", content)
            self.assertIn("raw/sources/batch-1/source.md", content)


    def test_generated_intelligence_types_route_to_case_directories(self):
        from auto_ingest import normalize_generated_file_path

        organization = normalize_generated_file_path({
            "path": "wiki/notes/团伙A.md",
            "meta": {"type": "organization", "title": "团伙A"},
        })
        event = normalize_generated_file_path({
            "path": "wiki/notes/凌晨入室盗窃.md",
            "meta": {"type": "event", "title": "凌晨入室盗窃"},
        })

        self.assertEqual(organization, "wiki/organizations/团伙A.md")
        self.assertEqual(event, "wiki/events/凌晨入室盗窃.md")

    def test_intelligence_template_sections_are_injected(self):
        from auto_ingest import apply_intelligence_template

        content = apply_intelligence_template({
            "path": "wiki/persons/person-a.md",
            "meta": {"type": "person", "title": "张某"},
            "content": "---\ntype: person\ntitle: 张某\n---\n# 张某\n\n## 基本情况\n\n待补充\n",
        })

        self.assertIn("## 关联案件", content)
        self.assertIn("## 关联实体", content)
        self.assertIn("## 来源与证据", content)


if __name__ == "__main__":
    unittest.main()
