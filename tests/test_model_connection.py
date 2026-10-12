"""本地 HTTP 模拟接口，验证真实网络流程；不会调用付费模型。"""
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QNetworkProxy

from config import ModelConfig, load_config, save_config
from services.chat_client import ChatClient, explain_http_error
from ui.settings_dialog import SettingsDialog
from ui.main_window import MainWindow

APP = QApplication.instance() or QApplication([])
APP.setOrganizationName("PyNiTests")
APP.setApplicationName("PyNiTests")


def wait_until(predicate, timeout=3000):
    deadline = time.monotonic() + timeout / 1000
    while not predicate() and time.monotonic() < deadline:
        APP.processEvents()
        time.sleep(0.002)
    if not predicate():
        raise AssertionError("Timed out waiting for Qt signal")


class Handler(BaseHTTPRequestHandler):
    records = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(size))
        Handler.records.append((self.path, request, self.headers.get("Authorization")))
        model = request["model"]
        if model == "slow":
            time.sleep(0.25)
        status = {"unauthorized": 401, "quota": 429, "missing": 404, "server": 503, "redirect": 307}.get(model, 200)
        self.send_response(status)
        if model == "redirect":
            self.send_header("Location", "/should-not-receive-key")
        streaming = request.get("stream") and status == 200 and model != "invalid"
        self.send_header("Content-Type", "text/event-stream" if streaming else "application/json")
        self.end_headers()
        try:
            if status != 200:
                self.wfile.write(json.dumps({"error": {"code": "insufficient_quota" if model == "quota" else "error", "message": "secret-key-must-not-leak"}}).encode())
            elif model == "invalid":
                self.wfile.write(b'<html>wrong endpoint</html>')
            elif streaming:
                for text in ("你好", "，Python"):
                    payload = "data: " + json.dumps({"choices": [{"delta": {"content": text}}]}, ensure_ascii=False) + "\r\n\r\n"
                    encoded = payload.encode("utf-8")
                    # 单字节分片，覆盖 UTF-8 与 CRLF 跨数据块的情况。
                    for byte in encoded:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                if model != "truncated":
                    self.wfile.write(b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
            else:
                message = {"content": "连接成功"}
                if request.get("tools") or model == "tool-only":
                    message = {"content": None, "tool_calls": [{"id": "probe", "type": "function", "function": {"name": "pyni_connection_probe", "arguments": '{"marker":"ok"}'}}]}
                self.wfile.write(json.dumps({"choices": [{"message": message, "finish_reason": "stop"}]}).encode())
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


class ModelConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def config(self, model="ok", stream=True):
        return ModelConfig("自定义服务", self.url, model, "test-key", stream)

    def client(self, timeout=1500):
        client = ChatClient(timeout_ms=timeout)
        client.manager.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        return client

    def request(self, model="ok", stream=True, timeout=1500, cancel=False):
        client = self.client(timeout)
        results, errors, deltas = [], [], []
        client.completed.connect(results.append)
        client.failed.connect(errors.append)
        client.delta.connect(deltas.append)
        client.send(self.config(model, stream), [{"role": "user", "content": "test"}])
        if cancel:
            QTimer.singleShot(20, client.cancel)
        wait_until(lambda: results or errors)
        self.assertFalse(client.busy)
        self.assertEqual(len(results) + len(errors), 1)
        return results, errors, deltas

    def test_stream_fragments_and_authorization(self):
        results, errors, deltas = self.request()
        self.assertFalse(errors)
        self.assertEqual(results[0]["content"], "你好，Python")
        self.assertEqual("".join(deltas), "你好，Python")
        path, payload, auth = Handler.records[-1]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(auth, "Bearer test-key")
        self.assertNotIn("api_key", payload)

    def test_non_streaming(self):
        results, errors, _ = self.request(stream=False)
        self.assertFalse(errors)
        self.assertEqual(results[0]["content"], "连接成功")

    def test_http_errors_are_helpful_without_secret_echo(self):
        self.assertIn("频率", explain_http_error(429, b'{"error":{"code":[]}}'))
        for model, expected in (("unauthorized", "密钥"), ("quota", "额度不足"), ("missing", "不存在"), ("server", "暂时异常")):
            with self.subTest(model=model):
                results, errors, _ = self.request(model)
                self.assertFalse(results)
                self.assertIn(expected, errors[0])
                self.assertNotIn("secret-key", errors[0])

    def test_redirect_does_not_forward_authorization(self):
        start = len(Handler.records)
        _, errors, _ = self.request("redirect")
        self.assertIn("跳转", errors[0])
        self.assertEqual(len(Handler.records), start + 1)

    def test_timeout_and_cancellation(self):
        _, errors, _ = self.request("slow", timeout=35)
        self.assertIn("超时", errors[0])
        _, errors, _ = self.request("slow", cancel=True)
        self.assertIn("取消", errors[0])

    def test_malformed_and_incomplete_responses(self):
        for model, expected, stream in (("invalid", "JSON", False), ("truncated", "提前结束", True), ("tool-only", "工具请求", False)):
            with self.subTest(model=model):
                results, errors, _ = self.request(model, stream)
                self.assertFalse(results)
                self.assertIn(expected, errors[0])

    def test_settings_apply_only_after_exact_config_tested(self):
        dialog = SettingsDialog(self.config(stream=False))
        dialog.client.manager.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        self.assertFalse(dialog.apply_button.isEnabled())
        dialog.test_connection()
        wait_until(lambda: not dialog.client.busy)
        self.assertTrue(dialog.apply_button.isEnabled())
        dialog.test_tools()
        wait_until(lambda: not dialog.client.busy)
        self.assertIn("检测通过", dialog.tool_status.text())
        dialog.model.setText("changed")
        self.assertFalse(dialog.apply_button.isEnabled())
        dialog.provider.setCurrentText("OpenAI")
        self.assertEqual(dialog.key.text(), "")
        dialog.provider.setCurrentText("自定义服务")
        self.assertEqual(dialog.key.text(), "test-key")
        dialog.reject()

    def test_main_chat_keeps_history_and_code_snapshot(self):
        with patch("ui.main_window.load_config", return_value=self.config()):
            window = MainWindow(store=False)
        window.connected = True
        window.client.manager.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        window.question.setText("为什么？")
        window.editor.setPlainText('print("你好")')
        window.send_question()
        self.assertFalse(window.lesson_list.isEnabled())
        window.editor.setPlainText("changed while waiting")
        wait_until(lambda: not window.client.busy)
        self.assertEqual(window.question.text(), "")
        self.assertIn('print("你好")', window.chats[0][0]["question"])
        self.assertEqual(window.chats[0][0]["status"], "success")
        window.question.setText("再解释一次")
        window.send_question()
        wait_until(lambda: not window.client.busy)
        self.assertEqual(len(Handler.records[-1][1]["messages"]), 4)
        window.lesson_list.setCurrentRow(1)
        window.question.setText("新的课")
        window.send_question()
        wait_until(lambda: not window.client.busy)
        self.assertEqual(len(Handler.records[-1][1]["messages"]), 2)
        window.model_config.model = "unauthorized"
        window.question.setText("保留这个问题")
        window.send_question()
        wait_until(lambda: not window.client.busy)
        self.assertEqual(window.question.text(), "保留这个问题")
        self.assertTrue(window.retry_button.isEnabled())
        window.model_config.model = "ok"
        window.retry_last()
        wait_until(lambda: not window.client.busy)
        self.assertEqual(window.question.text(), "")
        self.assertEqual(window.chats[1][-1]["status"], "success")
        window.deleteLater()


class ConfigTests(unittest.TestCase):
    def test_endpoint_validation(self):
        for url in ("https://example.com/v1", "https://example.com/v1/chat/completions/"):
            self.assertEqual(ModelConfig(base_url=url).endpoint(), "https://example.com/v1/chat/completions")
        for url in ("http://remote.example/v1", "https://user:password@example.com", "https://example.com?key=secret", "file:///etc/passwd", "https://example.com:bad", "https://exa mple.com"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                ModelConfig(base_url=url).endpoint()

    def test_secret_never_saved_or_loaded(self):
        directory = Path(__file__).resolve().parents[1] / "output"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temp:
            path = Path(temp) / "model.json"
            config = ModelConfig(api_key="test-secret")
            save_config(config, path)
            self.assertNotIn("test-secret", path.read_text(encoding="utf-8"))
            self.assertNotIn("api_key", path.read_text(encoding="utf-8"))
            self.assertEqual(load_config(path).api_key, "")
            self.assertNotIn("test-secret", repr(config))
            path.write_text('{"provider":"DeepSeek","base_url":"https://api.deepseek.com","model":"x","api_key":"untrusted"}', encoding="utf-8")
            self.assertEqual(load_config(path).api_key, "")
            path.write_text("broken", encoding="utf-8")
            self.assertEqual(load_config(path), ModelConfig())


if __name__ == "__main__":
    unittest.main()
