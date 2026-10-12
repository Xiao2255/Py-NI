"""配置、测试、应用连接。只有实际请求成功后才能应用新配置。"""
import json
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton,
)
from config import PRESETS, ModelConfig, save_config
from services.chat_client import ChatClient

PROBE_TOOL = [{"type": "function", "function": {
    "name": "pyni_connection_probe", "description": "Return a connection test marker. No real action.",
    "parameters": {"type": "object", "properties": {"marker": {"type": "string", "enum": ["ok"]}}, "required": ["marker"]},
}}]


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Py妮 · 连接 AI 模型")
        self.resize(580, 540)
        self.client = ChatClient(self)
        self.client.completed.connect(self._success)
        self.client.failed.connect(self._failure)
        self.result_config = None
        self.tested = None
        self.pending = None
        self.testing_tools = False
        self.tools_supported = False
        self.profiles = {config.provider: replace(config)}
        self.previous_provider = config.provider
        layout = QVBoxLayout(self)
        title = QLabel("连接 AI 模型")
        title.setObjectName("title")
        layout.addWidget(title)
        intro = QLabel("选择一个服务商即可开始。测试会发送简短请求，可能产生少量 API 费用。")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.provider = QComboBox()
        self.provider.addItems(PRESETS)
        self.provider.setCurrentText(config.provider)
        self.url = QLineEdit(config.base_url)
        self.url.setPlaceholderText("例如 https://服务地址/v1")
        self.key = QLineEdit(config.api_key)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("粘贴 API Key；本机免认证服务可留空")
        self.model = QLineEdit(config.model)
        self.model.setPlaceholderText("填写服务商提供的模型 ID")
        form.addRow("服务商", self.provider)
        form.addRow("API 地址", self.url)
        form.addRow("API Key", self.key)
        form.addRow("模型名称", self.model)
        layout.addLayout(form)
        self.show_key = QCheckBox("显示密钥")
        self.show_key.toggled.connect(lambda value: self.key.setEchoMode(QLineEdit.EchoMode.Normal if value else QLineEdit.EchoMode.Password))
        layout.addWidget(self.show_key)
        self.stream = QCheckBox("逐步显示回复（流式输出）")
        self.stream.setChecked(config.stream)
        layout.addWidget(self.stream)
        note = QLabel("仅支持 Chat Completions 兼容接口。密钥只在本次运行内保留，退出后需重新填写。保存设置不会保存密钥。")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.status = QLabel("尚未测试。也可以先浏览本地课程。")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.tool_status = QLabel("Agent 工具调用：尚未检测。")
        self.tool_status.setWordWrap(True)
        layout.addWidget(self.tool_status)
        actions = QHBoxLayout()
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        self.tool_button = QPushButton("检测工具调用（可选）")
        self.tool_button.setEnabled(False)
        self.tool_button.clicked.connect(self.test_tools)
        self.cancel_button = QPushButton("取消请求")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(lambda: self.client.cancel())
        for widget in (self.test_button, self.tool_button, self.cancel_button):
            actions.addWidget(widget)
        layout.addLayout(actions)
        bottom = QHBoxLayout()
        skip = QPushButton("稍后配置 / 返回")
        skip.clicked.connect(self.reject)
        self.apply_button = QPushButton("保存设置并开始")
        self.apply_button.setObjectName("primary")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_config)
        bottom.addWidget(skip)
        bottom.addWidget(self.apply_button)
        layout.addLayout(bottom)
        self.provider.currentTextChanged.connect(self.switch_provider)
        for widget in (self.url, self.key, self.model):
            widget.textChanged.connect(self.invalidate)
        self.stream.toggled.connect(self.invalidate)

    def current_config(self):
        return ModelConfig(self.provider.currentText(), self.url.text().strip(),
                           self.model.text().strip(), self.key.text().strip(), self.stream.isChecked())

    def switch_provider(self, name):
        self.profiles[self.previous_provider] = ModelConfig(
            self.previous_provider, self.url.text(), self.model.text(), self.key.text(), self.stream.isChecked())
        config = self.profiles.get(name, ModelConfig(name, *PRESETS[name]))
        self.previous_provider = name
        self.url.setText(config.base_url)
        self.key.setText(config.api_key)
        self.model.setText(config.model)
        self.stream.setChecked(config.stream)
        self.show_key.setChecked(False)
        self.invalidate()

    def invalidate(self, *_):
        self.tools_supported = False
        self.tested = None
        self.apply_button.setEnabled(False)
        self.tool_button.setEnabled(False)
        self.status.setText("配置已更改，请重新测试连接。")
        self.tool_status.setText("Agent 工具调用：尚未检测。")

    def set_busy(self, busy):
        for widget in (self.provider, self.url, self.key, self.model, self.stream, self.test_button):
            widget.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.apply_button.setEnabled(not busy and self.tested is not None)
        self.tool_button.setEnabled(not busy and self.tested is not None)

    def test_connection(self):
        self.tools_supported = False
        self.testing_tools = False
        self.tested = None
        self.tool_status.setText("Agent 工具调用：尚未检测。")
        self._send([{"role": "user", "content": "这是连接测试，请只回复：连接成功。"}])

    def test_tools(self):
        self.testing_tools = True
        self._send([{"role": "user", "content": "Please call pyni_connection_probe with marker ok. This is only a capability test."}], tools=PROBE_TOOL)

    def _send(self, messages, tools=None):
        try:
            self.pending = self.current_config().validate()
            self.client.send(self.pending, messages, stream=False if tools else None, tools=tools)
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.set_busy(True)
        self.status.setText("正在检测工具调用…" if tools else "正在连接模型，请稍候…")

    def _success(self, result):
        if self.testing_tools:
            supported = False
            for call in result["tool_calls"]:
                try:
                    function = call["function"]
                    supported |= function["name"] == "pyni_connection_probe" and json.loads(function["arguments"]) == {"marker": "ok"}
                except (KeyError, TypeError, ValueError, RecursionError):
                    pass
            self.tools_supported = supported
            self.tool_status.setText("Agent 工具调用：检测通过，将启用学习检查与授权目录阅读。" if supported else "Agent 工具调用：未验证通过；基础对话仍可使用。")
        else:
            self.tested = replace(self.pending)
        self.status.setText("基础对话连接成功。点击“保存设置并开始”应用配置。")
        self.set_busy(False)

    def _failure(self, message):
        self.status.setText(message)
        if self.testing_tools:
            self.tools_supported = False
            self.tool_status.setText("工具调用检测失败；基础对话测试结果保留。")
        self.set_busy(False)

    def apply_config(self):
        if self.tested is None or self.tested != self.current_config() or self.client.busy:
            return
        try:
            save_config(self.tested)
        except OSError:
            self.status.setText("无法保存本机设置，请检查本机配置目录的写入权限后重试。")
            return
        self.result_config = replace(self.tested, tools_enabled=self.tools_supported)
        self.accept()

    def reject(self):
        self.client.cancel()
        super().reject()
