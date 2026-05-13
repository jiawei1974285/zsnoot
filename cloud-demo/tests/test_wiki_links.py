import tempfile
import unittest
from pathlib import Path


class WikiLinkTests(unittest.TestCase):
    def test_ensure_bidirectional_links_adds_backlink_to_target_page(self):
        from wiki_links import ensure_bidirectional_links

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "wiki" / "cases" / "case-a.md"
            target = root / "wiki" / "persons" / "person-a.md"
            source.parent.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            source.write_text("---\ntype: case\n---\n# A\n\n- [[person-a]]\n", encoding="utf-8")
            target.write_text("---\ntype: person\n---\n# Person A\n", encoding="utf-8")

            result = ensure_bidirectional_links(str(root), ["wiki/cases/case-a.md"])
            updated_target = target.read_text(encoding="utf-8")

            self.assertEqual(result["added"], 1)
            self.assertIn("[[case-a]]", updated_target)
            self.assertIn("## 反向关联", updated_target)

    def test_collect_backlinks_finds_pages_linking_to_slug(self):
        from wiki_links import collect_backlinks

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "wiki" / "cases" / "case-a.md"
            target = root / "wiki" / "persons" / "person-a.md"
            source.parent.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            source.write_text("---\ntitle: Case A\n---\n# A\n\n[[person-a]]\n", encoding="utf-8")
            target.write_text("---\ntitle: Person A\n---\n# Person A\n", encoding="utf-8")

            backlinks = collect_backlinks(str(root), "person-a")

            self.assertEqual(backlinks[0]["slug"], "case-a")
            self.assertEqual(backlinks[0]["title"], "Case A")


if __name__ == "__main__":
    unittest.main()
