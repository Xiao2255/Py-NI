"""Qt 异步网络客户端：请求期间不阻塞窗口，支持流式输出、取消和总超时。"""
import json

from PySide6.QtCore import QObject, Signal, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


def explain_http_error(status, body=b""):
    """只展示可控错误文案，避免服务商回显密钥或用户代码。"""
    try:
        data = json.loads(body)
        code = data.get("error", {}).get("code", "") if isinstance(data, dict) else ""
    except (ValueError, AttributeError, TypeError):
        code = ""
    if not isinstance(code, str):
        code = ""
    if code in {"insufficient_quota", "billing_hard_limit_reached"} or status == 402:
        return "API 额度不足，请在服务商平台检查余额或使用额度。"
    messages = {
        400: "请求不被服务接受，请检查模型名称、接口格式和流式选项。",
        401: "密钥验证失败，请检查 API Key。",
        403: "没有访问权限，请检查模型权限或账号状态。",
        404: "模型或接口不存在，请检查 API 地址和模型名称。",
        408: "服务端等待超时，请稍后重试。",
        413: "请求内容过长，请缩短代码或问题。",
        422: "服务不接受当前参数，请检查接口兼容性与模型。",
        429: "请求频率或额度受限，请检查服务商额度，或稍后重试。",
    }
    if 300 <= status < 400:
        return "服务要求跳转地址。为避免密钥发往其他地址，请手动核对 API 地址。"
    if status >= 500:
        return "模型服务暂时异常，请稍后重试。"
    return messages.get(status, f"请求失败（HTTP {status}），请检查服务配置。")


def read_message(data):
    try:
        message = data["choices"][0]["message"]
        content = message.get("content") or message.get("refusal") or ""
        calls = message.get("tool_calls") or []
        if not isinstance(content, str) or not isinstance(calls, list):
            raise ValueError
        if not content.strip() and not calls:
            raise ValueError
        result = {"content": content, "tool_calls": calls}
        if isinstance(message.get("reasoning_content"), str):
            result["reasoning_content"] = message["reasoning_content"]
        return result
    except (KeyError, IndexError, TypeError, AttributeError, ValueError):
        raise ValueError("服务未返回有效回复，请检查模型和 Chat Completions 兼容性。") from None


class ChatClient(QObject):
    delta = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, parent=None, timeout_ms=120_000):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.cancel("请求超时，请检查网络或稍后重试。"))
        self.timeout_ms = timeout_ms
        self.reply = None

    @property
    def busy(self):
        return self.reply is not None

    def send(self, config, messages, *, stream=None, tools=None):
        if self.busy:
            raise ValueError("请等待当前请求完成，或先取消。")
        config.validate()
        self.buffer = b""
        self.lines = []
        self.raw = b""
        self.total_bytes = 0
        self.text = ""
        self.reason = ""
        self.is_sse = False
        self.stream_end = False
        self.finished_reason = None
        self.allow_tools = bool(tools)
        payload = {"model": config.model.strip(), "messages": messages,
                   "stream": config.stream if stream is None else stream}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        request = QNetworkRequest(QUrl(config.endpoint()))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        if config.api_key:
            request.setRawHeader(b"Authorization", ("Bearer " + config.api_key).encode("ascii"))
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        request.setTransferTimeout(self.timeout_ms)
        self.reply = self.manager.post(request, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        self.reply.readyRead.connect(self._read)
        self.reply.finished.connect(self._finished)
        self.timer.start(self.timeout_ms)

    def cancel(self, reason="已取消请求。输入和代码仍保留，可以重试。"):
        if self.reply:
            self.reason = reason
            self.reply.abort()

    def _read(self):
        if not self.reply or not self.reply.isOpen():
            return
        chunk = bytes(self.reply.readAll())
        self.total_bytes += len(chunk)
        if self.total_bytes > 2_000_000:
            self.cancel("回复过长，已停止接收。请缩小问题范围后重试。")
            return
        status = self.reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0
        content_type = self.reply.header(QNetworkRequest.KnownHeaders.ContentTypeHeader) or ""
        self.is_sse = "text/event-stream" in str(content_type).lower()
        if not self.is_sse or status >= 300:
            self.raw += chunk
            return
        self.buffer += chunk
        try:
            while b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                line = line.rstrip(b"\r")
                if not line:
                    self._event()
                elif line.startswith(b"data:"):
                    self.lines.append(line[5:].lstrip(b" "))
        except (ValueError, KeyError, TypeError, AttributeError, IndexError, UnicodeError, RecursionError):
            self.cancel("流式回复格式异常，请关闭流式选项后重试。")

    def _event(self):
        if not self.lines:
            return
        data = b"\n".join(self.lines)
        self.lines = []
        if data.strip() == b"[DONE]":
            self.stream_end = True
            return
        event = json.loads(data)
        if "error" in event:
            raise ValueError("stream error")
        choices = event.get("choices", [])
        if not choices:
            return
        choice = choices[0]
        piece = choice.get("delta", {}).get("content") or choice.get("delta", {}).get("refusal") or ""
        if not isinstance(piece, str):
            raise ValueError("invalid content")
        if piece:
            self.text += piece
            self.delta.emit(piece)
        if choice.get("finish_reason"):
            self.finished_reason = choice["finish_reason"]

    def _finished(self):
        self._read()
        reply = self.reply
        if reply is None:
            return
        self.timer.stop()
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0
        error = reply.error()
        self.reply = None
        reply.deleteLater()
        if self.reason:
            self.failed.emit(self.reason)
            return
        if status and not 200 <= status < 300:
            self.failed.emit(explain_http_error(status, self.raw))
            return
        if error == QNetworkReply.NetworkError.TimeoutError:
            self.failed.emit("请求超时，请检查网络或稍后重试。")
            return
        if error != QNetworkReply.NetworkError.NoError:
            self.failed.emit("网络连接失败，请检查网络、代理、证书和 API 地址。")
            return
        try:
            if self.is_sse:
                if self.buffer.strip() or self.lines or not (self.stream_end or self.finished_reason):
                    raise ValueError("连接提前结束，回复可能不完整，请重试。")
                if not self.text.strip():
                    raise ValueError("模型没有返回文字，请检查模型是否支持对话。")
                if self.finished_reason in {"length", "content_filter"}:
                    raise ValueError("回复被服务截断，已保留收到的内容，请缩小问题范围后重试。")
                result = {"content": self.text, "tool_calls": []}
            else:
                try:
                    data = json.loads(self.raw)
                except (ValueError, UnicodeError, RecursionError):
                    raise ValueError("服务返回的不是有效 JSON，请检查 API 地址和接口格式。") from None
                result = read_message(data)
                if not self.allow_tools and not result["content"].strip():
                    raise ValueError("模型只返回了工具请求，没有文字回复；当前对话尚未执行工具。")
                if data["choices"][0].get("finish_reason") in {"length", "content_filter"}:
                    raise ValueError("回复被服务截断，请缩小问题范围后重试。")
            self.completed.emit(result)
        except ValueError as exc:
            self.failed.emit(str(exc))
