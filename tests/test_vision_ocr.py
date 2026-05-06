"""视觉 LLM OCR + parse_image 降级链 单元测试。"""
import os
import tempfile
import unittest
from unittest import mock


def _make_tiny_png(path: str) -> None:
    # 1x1 透明 PNG（不依赖 Pillow，用最小 PNG 字节）
    data = bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4"
        "890000000D49444154789C636001000000050001E221BC330000000049454E44"
        "AE426082"
    )
    with open(path, "wb") as f:
        f.write(data)


class VisionExtractTextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.img = os.path.join(self.tmp, "x.png")
        _make_tiny_png(self.img)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_returns_none_when_no_model_configured(self):
        import llm_client
        with mock.patch.object(llm_client, "current_llm_config", return_value={
            "model": "", "api_key": "", "base_url": "https://x", "provider": ""
        }):
            out = llm_client.vision_extract_text(self.img)
        self.assertIsNone(out)

    def test_falls_back_from_ocr_to_vision_when_ocr_unset(self):
        import llm_client
        configs = {
            "ocr_model": {"model": "", "api_key": "", "base_url": "x", "provider": ""},
            "vision_model": {"model": "qwen-vl", "api_key": "k", "base_url": "https://x.com", "provider": ""},
        }

        class FakeResp:
            ok = True
            text = ""
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "图中文字内容"}}]}

        with mock.patch.object(llm_client, "current_llm_config",
                               side_effect=lambda r: configs[r]), \
             mock.patch.object(llm_client.requests, "post", return_value=FakeResp()):
            out = llm_client.vision_extract_text(self.img, role="ocr_model")
        self.assertEqual(out, "图中文字内容")

    def test_returns_empty_string_when_model_says_no_text(self):
        import llm_client

        class FakeResp:
            ok = True
            text = ""
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "无文字"}}]}

        with mock.patch.object(llm_client, "current_llm_config", return_value={
            "model": "m", "api_key": "k", "base_url": "https://x", "provider": ""
        }), mock.patch.object(llm_client.requests, "post", return_value=FakeResp()):
            out = llm_client.vision_extract_text(self.img)
        self.assertEqual(out, "")

    def test_returns_none_on_http_error(self):
        import llm_client

        class FakeResp:
            ok = False
            status_code = 500
            text = "boom"

        with mock.patch.object(llm_client, "current_llm_config", return_value={
            "model": "m", "api_key": "k", "base_url": "https://x", "provider": ""
        }), mock.patch.object(llm_client.requests, "post", return_value=FakeResp()):
            out = llm_client.vision_extract_text(self.img)
        self.assertIsNone(out)


class ParseImageFallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.img = os.path.join(self.tmp, "x.png")
        _make_tiny_png(self.img)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_uses_vision_llm_when_available(self):
        import file_parser
        with mock.patch("llm_client.vision_extract_text", return_value="抽到的文字"):
            text = file_parser.parse_image(self.img)
        self.assertEqual(text, "抽到的文字")

    def test_empty_vision_result_raises_clear_error(self):
        import file_parser
        with mock.patch("llm_client.vision_extract_text", return_value=""):
            with self.assertRaises(file_parser.FileParseError) as ctx:
                file_parser.parse_image(self.img)
        self.assertIn("未识别到文字", str(ctx.exception))

    def test_no_vision_no_tesseract_gives_helpful_error(self):
        import file_parser
        # 视觉 LLM 返回 None（未配置）；pytesseract import 失败
        with mock.patch("llm_client.vision_extract_text", return_value=None), \
             mock.patch.dict("sys.modules", {"pytesseract": None}):
            with self.assertRaises(file_parser.FileParseError) as ctx:
                file_parser.parse_image(self.img)
        msg = str(ctx.exception)
        self.assertIn("OCR 模型", msg)
        self.assertIn("视觉", msg)


if __name__ == "__main__":
    unittest.main()
