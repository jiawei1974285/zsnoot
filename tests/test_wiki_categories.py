import unittest
from unittest import mock


class WikiCategoryTests(unittest.TestCase):
    def test_custom_categories_extend_default_wiki_dirs(self):
        import app

        with mock.patch.object(app, "load_project_config", return_value={
            "wiki": {
                "custom_categories": [
                    {"key": "clues", "label": "线索"},
                    {"key": "units", "label": "单位"},
                ]
            }
        }):
            subdirs = app.get_wiki_subdirs()
            options = app.get_wiki_category_options()

        self.assertIn("clues", subdirs)
        self.assertIn("units", subdirs)
        self.assertTrue(any(item["key"] == "clues" and item["label"] == "线索" for item in options))


    def test_default_categories_include_case_intelligence_types(self):
        import app

        with mock.patch.object(app, "load_project_config", return_value={}):
            options = app.get_wiki_category_options()

        self.assertTrue(any(item["key"] == "events" for item in options))
        self.assertTrue(any(item["key"] == "evidence" for item in options))
        self.assertTrue(any(item["key"] == "conclusions" for item in options))


if __name__ == "__main__":
    unittest.main()
