"""有界工具循环；网络与工具结果均使用可见状态，不执行用户代码。"""
import json
from PySide6.QtCore import QObject, Signal, QTimer
from .chat_client import ChatClient


class AgentClient(QObject):
    delta = Signal(str)
    completed = Signal(object)
    failed = Signal(str)
    activity = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = ChatClient(self)
        self.manager = self.network.manager
        self.network.delta.connect(self.delta)
        self.network.completed.connect(self._receive)
        self.network.failed.connect(self._fail)
        self.active = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.cancel("本次 Agent 请求已超时，请缩小问题范围后重试。"))

    @property
    def busy(self):
        return self.active

    def send(self, config, messages, *, tools=None, execute=None):
        if self.active:
            raise ValueError("请等待当前请求完成。")
        self.config, self.messages = config, list(messages)
        self.tools, self.execute = tools, execute
        self.rounds, self.calls = 0, 0
        self.active = True
        try:
            self._request()
        except ValueError:
            self.active = False
            raise
        self.timer.start(120_000)

    def _request(self):
        # 工具模式整条请求使用非流式，保证调用参数完整后才执行。
        self.network.send(self.config, self.messages, stream=False if self.tools else None, tools=self.tools)

    def cancel(self, reason="已取消请求。输入和代码仍保留，可以重试。"):
        if self.network.busy:
            self.network.cancel(reason)
        elif self.active:
            self._fail(reason)

    def _fail(self, message):
        if self.active:
            self.active = False
            self.timer.stop()
            self.failed.emit(message)

    def _receive(self, result):
        if not self.active:
            return
        calls = result.get("tool_calls", [])
        if not calls:
            self.active = False
            self.timer.stop()
            self.completed.emit(result)
            return
        if not self.tools or not self.execute:
            self._fail("当前连接未启用工具，请先在设置中检测工具调用。")
            return
        self.rounds += 1
        self.calls += len(calls)
        if self.rounds > 4 or self.calls > 8:
            self._fail("工具调用达到本次上限（4 轮、8 次），请缩小问题范围再问。")
            return
        ids = set()
        parsed = []
        try:
            for call in calls:
                ident = call["id"]
                function = call["function"]
                if not isinstance(ident, str) or not ident or ident in ids or call.get("type") != "function":
                    raise ValueError
                ids.add(ident)
                name, raw = function["name"], function["arguments"]
                if not isinstance(name, str) or not isinstance(raw, str) or len(raw) > 24_000:
                    raise ValueError
                args = json.loads(raw)
                if not isinstance(args, dict):
                    raise ValueError
                parsed.append((ident, name, args))
        except (KeyError, TypeError, ValueError, RecursionError):
            self._fail("模型返回的工具参数不完整，本次未执行这些调用。")
            return
        assistant = {"role": "assistant", "content": result["content"] or None, "tool_calls": calls}
        if "reasoning_content" in result:
            assistant["reasoning_content"] = result["reasoning_content"]
        self.messages.append(assistant)
        for ident, name, args in parsed:
            if not self.active:
                return
            try:
                output = self.execute(name, args)
            except (ValueError, OSError):
                output = {"error": "工具无法访问该内容，请检查授权、相对路径和文件大小。"}
            self.messages.append({"role": "tool", "tool_call_id": ident,
                                  "content": json.dumps(output, ensure_ascii=False)})
            self.activity.emit(f"已处理工具：{name}")
        # 下一次网络调用放回事件循环，让取消按钮有机会响应。
        QTimer.singleShot(0, self._continue)

    def _continue(self):
        if self.active:
            try:
                self._request()
            except ValueError as exc:
                self._fail(str(exc))
