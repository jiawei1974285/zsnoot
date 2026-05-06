"""thinking / reasoning_effort 配置注入 LLM 请求体的单元测试。"""
import unittest
from unittest import mock


class ApplyThinkingTests(unittest.TestCase):
    def test_off_does_not_modify_payload(self):
        import llm_client
        payload = {"model": "x", "messages": []}
        out = llm_client._apply_thinking(payload, {"thinking": False})
        self.assertNotIn("reasoning_effort", out)
        self.assertNotIn("thinking", out)

    def test_on_injects_reasoning_effort_and_thinking(self):
        import llm_client
        payload = {"model": "x", "messages": []}
        out = llm_client._apply_thinking(payload, {
            "thinking": True,
            "reasoning_effort": "high",
        })
        self.assertEqual(out["reasoning_effort"], "high")
        self.assertEqual(out["thinking"], {"type": "enabled"})

    def test_on_with_medium_effort(self):
        import llm_client
        payload = {"model": "x", "messages": []}
        out = llm_client._apply_thinking(payload, {"thinking": True, "reasoning_effort": "medium"})
        self.assertEqual(out["reasoning_effort"], "medium")

    def test_on_default_effort_is_high(self):
        import llm_client
        payload = {"model": "x", "messages": []}
        out = llm_client._apply_thinking(payload, {"thinking": True})
        self.assertEqual(out["reasoning_effort"], "high")


class CurrentLlmConfigThinkingTests(unittest.TestCase):
    """current_llm_config 应该把 yaml 里的 thinking / reasoning_effort 透传出来。"""

    def test_reads_thinking_from_yaml(self):
        import llm_client
        with mock.patch.object(llm_client, "load_yaml_config", return_value={
            "llm": {
                "provider": "openai",
                "model": "deepseek-v4-pro",
                "base_url": "https://api.deepseek.com",
                "api_key": "k",
                "thinking": True,
                "reasoning_effort": "medium",
            }
        }), mock.patch.object(llm_client, "current_env", return_value={}):
            cfg = llm_client.current_llm_config("llm")
        self.assertTrue(cfg["thinking"])
        self.assertEqual(cfg["reasoning_effort"], "medium")

    def test_invalid_effort_falls_back_to_high(self):
        import llm_client
        with mock.patch.object(llm_client, "load_yaml_config", return_value={
            "llm": {
                "provider": "openai", "model": "m", "base_url": "https://x", "api_key": "k",
                "thinking": True, "reasoning_effort": "extreme",
            }
        }), mock.patch.object(llm_client, "current_env", return_value={}):
            cfg = llm_client.current_llm_config("llm")
        self.assertEqual(cfg["reasoning_effort"], "high")

    def test_thinking_default_off_when_missing(self):
        import llm_client
        with mock.patch.object(llm_client, "load_yaml_config", return_value={
            "llm": {"provider": "openai", "model": "m", "base_url": "https://x", "api_key": "k"}
        }), mock.patch.object(llm_client, "current_env", return_value={}):
            cfg = llm_client.current_llm_config("llm")
        self.assertFalse(cfg["thinking"])


class ChatCompletionPayloadTests(unittest.TestCase):
    """chat_completion 在 thinking 启用时，对外发出的 HTTP body 包含正确字段。"""

    def test_thinking_payload_e2e(self):
        import llm_client

        captured = {}

        class FakeResp:
            ok = True
            text = ""
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured["json"] = json
            return FakeResp()

        with mock.patch.object(llm_client, "current_llm_config", return_value={
            "provider": "openai",
            "base_url": "https://api.deepseek.com",
            "api_key": "k",
            "model": "deepseek-v4-pro",
            "thinking": True,
            "reasoning_effort": "high",
        }), mock.patch.object(llm_client.requests, "post", side_effect=fake_post):
            llm_client.chat_completion([{"role": "user", "content": "hi"}])

        body = captured["json"]
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["model"], "deepseek-v4-pro")

    def test_thinking_off_payload_clean(self):
        import llm_client

        captured = {}

        class FakeResp:
            ok = True
            text = ""
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured["json"] = json
            return FakeResp()

        with mock.patch.object(llm_client, "current_llm_config", return_value={
            "provider": "openai",
            "base_url": "https://api.x.com",
            "api_key": "k",
            "model": "m",
            "thinking": False,
            "reasoning_effort": "high",
        }), mock.patch.object(llm_client.requests, "post", side_effect=fake_post):
            llm_client.chat_completion([{"role": "user", "content": "hi"}])

        body = captured["json"]
        self.assertNotIn("reasoning_effort", body)
        self.assertNotIn("thinking", body)


if __name__ == "__main__":
    unittest.main()
