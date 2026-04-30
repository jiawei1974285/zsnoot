import tempfile
import unittest
from pathlib import Path


class ConfigStoreTests(unittest.TestCase):
    def test_deep_merge_preserves_existing_nested_settings(self):
        from config_store import load_config, update_config

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                """
llm:
  provider: dashscope
  model: qwen3.5-plus
  base_url: http://old.local/v1
  temperature: 0.1
server:
  port: 5004
""".strip(),
                encoding="utf-8",
            )

            updated = update_config(str(config_path), {"llm": {"model": "local-qwen"}})
            reloaded = load_config(str(config_path))

            self.assertEqual(updated["llm"]["model"], "local-qwen")
            self.assertEqual(reloaded["llm"]["provider"], "dashscope")
            self.assertEqual(reloaded["llm"]["base_url"], "http://old.local/v1")
            self.assertEqual(reloaded["server"]["port"], 5004)


if __name__ == "__main__":
    unittest.main()
