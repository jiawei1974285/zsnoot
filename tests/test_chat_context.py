"""聊天上下文构建：图谱二跳扩展 + 字符预算分配 单元测试。"""
import unittest
from unittest import mock


class GraphExpandTests(unittest.TestCase):
    def _fake_graph(self):
        return {
            "nodes": [
                {"id": "case-a", "type": "cases"},
                {"id": "person-x", "type": "persons"},
                {"id": "case-b", "type": "cases"},
                {"id": "stranger", "type": "notes"},
            ],
            "edges": [
                {"source": "case-a", "target": "person-x"},
                {"source": "person-x", "target": "case-b"},
            ],
        }

    def test_disabled_returns_empty(self):
        import app
        seeds = [{"slug": "case-a"}]
        with mock.patch("graph.build_graph", return_value=self._fake_graph()):
            out = app._expand_via_graph(seeds, [], enable=False, hops=2, max_added=5)
        self.assertEqual(out, [])

    def test_one_hop_finds_direct_neighbor(self):
        import app
        seeds = [{"slug": "case-a"}]
        all_pages = [
            {"slug": "person-x", "type": "persons", "title": "X", "body_preview": "bio"},
            {"slug": "case-b", "type": "cases", "title": "B", "body_preview": "case"},
        ]
        with mock.patch("graph.build_graph", return_value=self._fake_graph()), \
             mock.patch.object(app, "get_wiki_page", return_value={"body": "full body"}):
            out = app._expand_via_graph(seeds, all_pages, enable=True, hops=1, max_added=5)
        self.assertEqual([p["slug"] for p in out], ["person-x"])
        self.assertTrue(all(p["_graph_expanded"] for p in out))

    def test_two_hop_finds_indirect_neighbor(self):
        import app
        seeds = [{"slug": "case-a"}]
        all_pages = [
            {"slug": "person-x", "type": "persons", "title": "X", "body_preview": ""},
            {"slug": "case-b", "type": "cases", "title": "B", "body_preview": ""},
        ]
        with mock.patch("graph.build_graph", return_value=self._fake_graph()), \
             mock.patch.object(app, "get_wiki_page", return_value={"body": ""}):
            out = app._expand_via_graph(seeds, all_pages, enable=True, hops=2, max_added=5)
        slugs = {p["slug"] for p in out}
        self.assertEqual(slugs, {"person-x", "case-b"})

    def test_max_added_caps_result(self):
        import app
        seeds = [{"slug": "case-a"}]
        all_pages = [
            {"slug": "person-x", "type": "persons", "title": "X", "body_preview": ""},
            {"slug": "case-b", "type": "cases", "title": "B", "body_preview": ""},
        ]
        with mock.patch("graph.build_graph", return_value=self._fake_graph()), \
             mock.patch.object(app, "get_wiki_page", return_value={"body": ""}):
            out = app._expand_via_graph(seeds, all_pages, enable=True, hops=2, max_added=1)
        self.assertEqual(len(out), 1)

    def test_excludes_seed_slugs(self):
        import app
        seeds = [{"slug": "case-a"}, {"slug": "person-x"}]
        all_pages = [
            {"slug": "case-b", "type": "cases", "title": "B", "body_preview": ""},
        ]
        with mock.patch("graph.build_graph", return_value=self._fake_graph()), \
             mock.patch.object(app, "get_wiki_page", return_value={"body": ""}):
            out = app._expand_via_graph(seeds, all_pages, enable=True, hops=2, max_added=5)
        self.assertEqual([p["slug"] for p in out], ["case-b"])

    def test_graph_failure_safe_fallback(self):
        import app
        seeds = [{"slug": "case-a"}]
        with mock.patch("graph.build_graph", side_effect=RuntimeError("boom")):
            out = app._expand_via_graph(seeds, [], enable=True, hops=1, max_added=5)
        self.assertEqual(out, [])


class ContextBudgetTests(unittest.TestCase):
    def test_budget_caps_per_page(self):
        import app
        long_body = "x" * 5000
        primary = [
            {"slug": "p1", "title": "P1", "full_content": long_body},
            {"slug": "p2", "title": "P2", "full_content": long_body},
        ]
        parts = app._build_chat_context(primary, [], budget_chars=10000, max_chars_per_page=1000)
        # 单页上限 1000，实际正文应 ≤ 1000 字符（不含标题/截断标记）
        for part in parts:
            self.assertLess(len(part), 1200)

    def test_per_page_ceiling_is_configurable(self):
        import app
        primary = [{"slug": "p1", "title": "P1", "full_content": "x" * 5000}]
        parts_short = app._build_chat_context(primary, [], budget_chars=10000, max_chars_per_page=500)
        parts_long = app._build_chat_context(primary, [], budget_chars=10000, max_chars_per_page=2000)
        self.assertLess(len(parts_short[0]), len(parts_long[0]))

    def test_truncation_marker_added_for_long_content(self):
        import app
        primary = [{"slug": "p1", "title": "P1", "full_content": "x" * 10000}]
        parts = app._build_chat_context(primary, [], budget_chars=2000, max_chars_per_page=1000)
        self.assertIn("……（内容较长", parts[0])

    def test_short_content_not_truncated(self):
        import app
        primary = [{"slug": "p1", "title": "P1", "full_content": "短内容"}]
        parts = app._build_chat_context(primary, [], budget_chars=2000, max_chars_per_page=1000)
        self.assertNotIn("……", parts[0])
        self.assertIn("短内容", parts[0])

    def test_expanded_pages_labeled(self):
        import app
        primary = [{"slug": "p1", "title": "P1", "full_content": "main"}]
        expanded = [{"slug": "e1", "title": "E1", "full_content": "extra"}]
        parts = app._build_chat_context(primary, expanded, budget_chars=2000, max_chars_per_page=1000)
        self.assertEqual(len(parts), 2)
        self.assertIn("图谱关联页", parts[1])
        self.assertNotIn("图谱关联页", parts[0])

    def test_empty_inputs_return_empty(self):
        import app
        self.assertEqual(app._build_chat_context([], [], budget_chars=2000, max_chars_per_page=1000), [])


class ChatConfigTests(unittest.TestCase):
    def test_defaults_when_section_missing(self):
        import app
        with mock.patch("config_store.load_config", return_value={}):
            cfg = app._load_chat_runtime_config()
        self.assertTrue(cfg["graph_expand"])
        self.assertEqual(cfg["graph_hops"], 1)
        self.assertEqual(cfg["graph_max_added"], 5)
        self.assertEqual(cfg["context_budget_chars"], 150000)
        self.assertEqual(cfg["max_chars_per_page"], 10000)

    def test_clamps_out_of_range_values(self):
        import app
        with mock.patch("config_store.load_config", return_value={
            "chat": {
                "graph_hops": 99,
                "graph_max_added": -5,
                "context_budget_chars": 9999999,
                "wiki_share": 5.0,
                "max_chars_per_page": 999999,
            }
        }):
            cfg = app._load_chat_runtime_config()
        self.assertLessEqual(cfg["graph_hops"], 2)
        self.assertGreaterEqual(cfg["graph_max_added"], 0)
        self.assertLessEqual(cfg["context_budget_chars"], 500000)
        self.assertLessEqual(cfg["wiki_share"], 0.95)
        self.assertLessEqual(cfg["max_chars_per_page"], 30000)


if __name__ == "__main__":
    unittest.main()
