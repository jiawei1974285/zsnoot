"""SHA256 增量缓存与 rollback 引用计数保护的单元测试。

覆盖：
  - build_sha256_cache_index 在批次干净/回滚/失败/产物丢失等状态下的取舍
  - _is_referenced_by_other_batches 的判定
  - rollback_batch 不删除被其他批次引用的共享 wiki 页
"""
import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path


def make_tmp_dir(name: str) -> Path:
    root = Path(os.environ.get("CODEX_TEST_TMP", Path.cwd() / ".test-tmp"))
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class CacheIndexTests(unittest.TestCase):
    def setUp(self):
        from ingest_batches import IngestBatchStore
        self.tmp = make_tmp_dir("cache-index")
        (self.tmp / "wiki" / "notes").mkdir(parents=True)
        # 写两个真实存在的 wiki 页
        (self.tmp / "wiki" / "notes" / "page-a.md").write_text("a", encoding="utf-8")
        (self.tmp / "wiki" / "notes" / "page-b.md").write_text("b", encoding="utf-8")
        self.store = IngestBatchStore(str(self.tmp / "data"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed(self, batch_id, sha, generated, status="completed"):
        from ingest_batches import IngestBatchStore
        # 直接写底层 JSON 模拟历史批次
        batches = self.store.list_batches()
        batches.insert(0, {
            "id": batch_id,
            "status": status,
            "original_files": [{"name": f"f-{batch_id}", "path": "raw/x", "sha256": sha}],
            "generated_files": generated,
            "entities": [{"name": "ent", "type": "person"}],
        })
        self.store._write(batches)

    def test_index_picks_up_completed_batch(self):
        from ingest_service import build_sha256_cache_index
        self._seed("b1", "sha-1", ["wiki/notes/page-a.md"])
        index = build_sha256_cache_index(self.store, str(self.tmp))
        self.assertIn("sha-1", index)
        self.assertEqual(index["sha-1"]["batch_id"], "b1")

    def test_index_skips_rolled_back_batch(self):
        from ingest_service import build_sha256_cache_index
        self._seed("b1", "sha-1", ["wiki/notes/page-a.md"], status="rolled_back")
        index = build_sha256_cache_index(self.store, str(self.tmp))
        self.assertNotIn("sha-1", index)

    def test_index_skips_when_all_pages_deleted(self):
        from ingest_service import build_sha256_cache_index
        self._seed("b1", "sha-1", ["wiki/notes/missing.md"])
        index = build_sha256_cache_index(self.store, str(self.tmp))
        self.assertNotIn("sha-1", index)

    def test_index_keeps_alive_subset_when_some_pages_deleted(self):
        from ingest_service import build_sha256_cache_index
        self._seed("b1", "sha-1", ["wiki/notes/page-a.md", "wiki/notes/missing.md"])
        index = build_sha256_cache_index(self.store, str(self.tmp))
        self.assertEqual(index["sha-1"]["generated_files"], ["wiki/notes/page-a.md"])

    def test_index_excludes_failed_files_within_completed_batch(self):
        """部分文件失败的批次：失败文件的 sha256 不应进入缓存（防止 fallback 被复用）"""
        from ingest_service import build_sha256_cache_index
        # 模拟：批次成功了 1 个，失败了 1 个（fallback 到"待精炼"）
        batches = self.store.list_batches()
        batches.insert(0, {
            "id": "b-mixed",
            "status": "completed_with_warnings",
            "original_files": [
                {"name": "good.docx", "path": "raw/x", "sha256": "sha-good"},
                {"name": "bad.png",   "path": "raw/y", "sha256": "sha-bad"},
            ],
            "generated_files": ["wiki/notes/page-a.md", "wiki/notes/page-b.md"],
            "entities": [],
            "errors": [{"file": "bad.png", "error": "OCR 不可用"}],
        })
        self.store._write(batches)
        index = build_sha256_cache_index(self.store, str(self.tmp))
        self.assertIn("sha-good", index)
        self.assertNotIn("sha-bad", index, "失败文件的 sha256 不应被缓存")

    def test_first_batch_wins_on_duplicate_sha(self):
        from ingest_service import build_sha256_cache_index
        # list_batches 返回 insert 顺序，最新的在前面 → 最新的应该胜出（first hit）
        self._seed("b1-old", "sha-1", ["wiki/notes/page-a.md"])
        self._seed("b2-new", "sha-1", ["wiki/notes/page-b.md"])
        index = build_sha256_cache_index(self.store, str(self.tmp))
        self.assertEqual(index["sha-1"]["batch_id"], "b2-new")


class ReferenceProtectionTests(unittest.TestCase):
    def setUp(self):
        from ingest_batches import IngestBatchStore
        self.tmp = make_tmp_dir("ref-protect")
        (self.tmp / "wiki" / "notes").mkdir(parents=True)
        (self.tmp / "wiki" / "notes" / "shared.md").write_text("shared", encoding="utf-8")
        (self.tmp / "wiki" / "notes" / "exclusive.md").write_text("exclusive", encoding="utf-8")
        self.store = IngestBatchStore(str(self.tmp / "data"))
        # b1 拥有 shared + exclusive；b2 通过 sha256 缓存共享了 shared
        batches = [
            {
                "id": "b1",
                "status": "completed",
                "original_files": [{"sha256": "sha-1"}],
                "generated_files": ["wiki/notes/shared.md", "wiki/notes/exclusive.md"],
                "entities": [],
            },
            {
                "id": "b2",
                "status": "completed",
                "original_files": [{"sha256": "sha-1"}],
                "generated_files": ["wiki/notes/shared.md"],
                "entities": [],
            },
        ]
        self.store._write(batches)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rollback_b1_keeps_shared_page(self):
        from ingest_service import rollback_batch
        rollback_batch("b1", str(self.tmp), self.store)
        self.assertTrue((self.tmp / "wiki" / "notes" / "shared.md").exists(),
                        "被 b2 引用的 shared.md 不应被删除")
        self.assertFalse((self.tmp / "wiki" / "notes" / "exclusive.md").exists(),
                         "未被其他批次引用的 exclusive.md 应被删除")
        b1 = self.store.get_batch("b1")
        self.assertEqual(b1["removed_files"], ["wiki/notes/exclusive.md"])

    def test_rollback_both_eventually_removes_shared(self):
        from ingest_service import rollback_batch
        rollback_batch("b1", str(self.tmp), self.store)
        # 此时 shared 仅被 b2 引用；再 rollback b2 → b1 已 rolled_back 不计入引用 → 删除
        rollback_batch("b2", str(self.tmp), self.store)
        self.assertFalse((self.tmp / "wiki" / "notes" / "shared.md").exists())


if __name__ == "__main__":
    unittest.main()
