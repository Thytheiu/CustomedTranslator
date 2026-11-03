import io
import json
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from settings import SettingsStore
from translator import ENDPOINT, make_body, translate_stream


def chunk(content=None, reason=None, finish=None):
    delta = {"content": content} if content is not None else {"reasoning_content": reason}
    return ("data: " + json.dumps({"choices": [{"delta": delta, "finish_reason": finish}]}) + "\n\n").encode()


class TranslationTests(unittest.TestCase):
    settings = {"api_key": "sk-local-test-only", "model": "custom-model", "thinking": "low"}

    def request(self, raw, cancel=None):
        events = []
        with patch("translator.urllib.request.urlopen", return_value=io.BytesIO(raw)) as mocked:
            result = translate_stream("你好\n世界", "zh-en", self.settings, cancel or threading.Event(), events.append)
        return result, events, mocked.call_args[0][0]

    def test_stream_preserves_paragraphs_and_ignores_reasoning(self):
        result, events, request = self.request(chunk(reason="private reasoning") + chunk("Hello\n") + chunk("world", finish="stop") + b"data: [DONE]\n")
        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "Hello\nworld")
        self.assertEqual(events[0], {"phase": "thinking"})
        self.assertNotIn("private reasoning", str(events))
        self.assertEqual(request.full_url, ENDPOINT)
        sent = json.loads(request.data)
        self.assertEqual(sent["model"], "custom-model")
        self.assertEqual(sent["messages"][1]["content"], "你好\n世界")

    def test_all_supported_efforts_and_both_directions(self):
        for effort in ("none", "low", "high", "max"):
            for direction in ("zh-en", "en-zh"):
                with self.subTest(effort=effort, direction=direction):
                    body = make_body("test", direction, {**self.settings, "thinking": effort})
                    self.assertEqual(body["reasoning_effort"], effort)
                    self.assertEqual(body["thinking"]["type"], "disabled" if effort == "none" else "enabled")
                    self.assertEqual("temperature" in body, effort == "none")
                    self.assertIn("英语" if direction == "zh-en" else "简体中文", body["messages"][0]["content"])

    def test_truncated_output_is_not_reported_as_success(self):
        result, _, _ = self.request(chunk("Partial", finish="length") + b"data: [DONE]\n")
        self.assertFalse(result["ok"])
        self.assertEqual(result["partial"], "Partial")

    def test_unfinished_stream_is_not_reported_as_success(self):
        self.assertFalse(self.request(chunk("Partial"))[0]["ok"])

    def test_empty_and_malformed_outputs(self):
        for data in (chunk(finish="stop"), b'data: not-json\n', b'data: []\n'):
            self.assertFalse(self.request(data)[0]["ok"])

    def test_cancel_discards_future_chunks(self):
        cancel = threading.Event()
        cancel.set()
        result, events, _ = self.request(chunk("ignored", finish="stop"), cancel)
        self.assertTrue(result["cancelled"])
        self.assertFalse(events)

    def test_auth_balance_and_network_errors(self):
        for code in (400, 401, 402, 429, 503):
            with self.subTest(code=code), patch("translator.urllib.request.urlopen", side_effect=urllib.error.HTTPError(ENDPOINT, code, "test", {}, None)):
                result = translate_stream("x", "zh-en", self.settings, threading.Event(), lambda _: None)
                self.assertFalse(result["ok"])
                self.assertNotIn(self.settings["api_key"], result["error"])
        with patch("translator.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            result = translate_stream("x", "zh-en", self.settings, threading.Event(), lambda _: None)
            self.assertIn("网络", result["error"])


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(".qa") / ("settings-" + uuid4().hex)
        self.store = SettingsStore(self.path)

    def test_save_reload_protects_key_and_keeps_custom_model(self):
        result = self.store.save({"api_key": "sk-local-test-only", "model": "my-model", "thinking": "max"})
        self.assertNotIn("api_key", result)
        self.assertNotIn("sk-local-test-only", self.store.path.read_text())
        reloaded = SettingsStore(self.path)
        self.assertEqual(reloaded.get()["api_key"], "sk-local-test-only")
        self.assertEqual(reloaded.get()["model"], "my-model")
        reloaded.save({"api_key": "", "model": "changed-model", "thinking": "none"})
        self.assertEqual(SettingsStore(self.path).get()["api_key"], "sk-local-test-only")

    def test_missing_key_or_invalid_effort_does_not_save(self):
        for payload in (None, {"api_key": "", "model": "x", "thinking": "low"}, {"api_key": "test", "model": "x", "thinking": "medium"}, {"api_key": "test", "model": "x", "thinking": []}):
            with self.assertRaises(ValueError): self.store.save(payload)
        self.assertFalse(self.store.path.exists())

    def test_invalid_saved_json_is_reported_and_preserved(self):
        self.store.path.write_text("broken", encoding="utf-8")
        reloaded = SettingsStore(self.path)
        self.assertTrue(reloaded.public()["notice"])
        self.assertEqual(self.store.path.read_text(), "broken")


if __name__ == "__main__":
    unittest.main()
