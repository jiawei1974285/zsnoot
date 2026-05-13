import unittest
from unittest import mock


class LLMTesterTests(unittest.TestCase):
    def test_test_llm_connection_posts_openai_compatible_payload(self):
        from llm_tester import test_llm_connection

        calls = []

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
            return FakeResponse()

        result = test_llm_connection(
            {
                "base_url": "http://model.local/v1",
                "api_key": "test-key",
                "model": "qwen-local",
            },
            post_func=fake_post,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(calls[0]["url"], "http://model.local/v1/chat/completions")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0]["json"]["model"], "qwen-local")
        self.assertEqual(calls[0]["timeout"], 20)

    def test_test_llm_connection_requires_model_and_base_url(self):
        from llm_tester import test_llm_connection

        result = test_llm_connection({"model": ""}, post_func=lambda **_: None)

        self.assertFalse(result["ok"])
        self.assertIn("接口地址", result["message"])

    def test_test_llm_connection_uses_ollama_tags_endpoint(self):
        from llm_tester import test_llm_connection

        class FakeGetResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"models": [{"name": "gemma4:e4b"}]}

        with mock.patch("llm_tester.requests.get", return_value=FakeGetResponse()):
            result = test_llm_connection(
                {
                    "provider": "ollama",
                    "base_url": "http://localhost:11434",
                    "model": "gemma4:e4b",
                    "api_key": "",
                },
                post_func=lambda **_: None,
            )

        self.assertTrue(result["ok"])
        self.assertIn("Ollama", result["message"])


if __name__ == "__main__":
    unittest.main()
