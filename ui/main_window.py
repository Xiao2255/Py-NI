"""学习窗口：本地课程、模型对话与代码反馈。"""
from pathlib import Path
import sqlite3
import json
from copy import deepcopy
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
    QVBoxLayout, QWidget, QFrame, QFileDialog,
)
from .lessons import LESSONS
from .settings_dialog import SettingsDialog
from .chat_view import ChatView
from config import load_config
from services.agent import AgentClient
from tools.project_tools import ProjectTools, STUDY_TOOLS, PROJECT_TOOLS
from .editor import CodeEditor, QuestionEdit
from services.learning import new_progress, CHECKPOINTS
from services.study_store import StudyStore
from .learning_dialogs import UnderstandingDialog, RecordsDialog

ROOT = Path(__file__).resolve().parent.parent


def label(text, name=None):
    widget = QLabel(text)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, action, primary=False):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(action)
    if primary:
        widget.setObjectName("primary")
    return widget


class MainWindow(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.setWindowTitle("Py妮 · Python 学习空间")
        self.resize(1280, 850)
        self.setMinimumSize(1000, 720)
        self.setStyleSheet((ROOT / "ui/style.qss").read_text(encoding="utf-8"))
        self.current_lesson = None
        self.help_mode = False
        self.drafts = {}
        self.model_config = load_config()
        self.connected = False
        self.project_tools = ProjectTools()
        self.client = AgentClient(self)
        self.client.activity.connect(self.tool_activity)
        self.client.delta.connect(self.receive_delta)
        self.client.completed.connect(self.receive_reply)
        self.client.failed.connect(self.receive_error)
        self.chats = {index: [] for index in range(len(LESSONS))}
        self.progress = {index: new_progress() for index in range(len(LESSONS))}
        self.questions = {}
        self.revisions = {index: 0 for index in range(len(LESSONS))}
        self.timestamps = {}
        self.dirty = set()
        self.storage_error = ""
        self.store = None
        start_index = 0
        try:
            self.store = StudyStore() if store is None else (store or None)
            if self.store:
                loaded, selected = self.store.load([lesson["id"] for lesson in LESSONS])
                for index, lesson in enumerate(LESSONS):
                    if lesson["id"] == selected:
                        start_index = index
                    if lesson["id"] in loaded:
                        data, revision, updated = loaded[lesson["id"]]
                        self.drafts[index] = data["draft"]
                        self.questions[index] = data["question"]
                        self.progress[index] = data["progress"]
                        self.chats[index] = data["chats"]
                        for turn in self.chats[index]:
                            if turn.get("status") == "pending":
                                turn.update(status="failed", error="上次请求未完成，可重新发送。")
                        self.revisions[index] = revision
                        self.timestamps[index] = updated
        except (OSError, sqlite3.Error, ValueError):
            self.store = None
            self.storage_error = "学习记录暂时无法读取，原文件已保留。本次内容暂不能自动保存。"
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.persist_changes)
        self.pending_turn = None
        self.retry_data = None
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self.render_conversation)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(18)
        header = QHBoxLayout()
        brand = label("Py妮  |  一步一步，学会 Python", "brand")
        brand.setWordWrap(False)
        header.addWidget(brand)
        header.addStretch()
        self.connection_status = label("○ 模型未连接", "muted")
        header.addWidget(self.connection_status)
        self.settings_button = button("设置", self.show_settings)
        header.addWidget(self.settings_button)
        layout.addLayout(header)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        sidebar = QWidget()
        side = QVBoxLayout(sidebar)
        side.addWidget(label("学习空间", "brand"))
        self.help_button = button("代码求助", self.show_help)
        side.addWidget(self.help_button)
        side.addSpacing(14)
        side.addWidget(label("Python 入门 · 一步一步学", "muted"))
        self.lesson_list = QListWidget()
        for number, lesson in enumerate(LESSONS, 1):
            self.lesson_list.addItem(f"{number:02d}  {lesson['name']}")
        side.addWidget(self.lesson_list, 1)
        side.addWidget(button("学习记录", self.show_records))
        self.folder_button = button("授权代码文件夹", self.select_project)
        side.addWidget(self.folder_button)
        self.folder_status = label("尚未授权文件夹", "muted")
        side.addWidget(self.folder_status)
        self.revoke_button = button("取消文件夹授权", self.revoke_project)
        self.revoke_button.setEnabled(False)
        side.addWidget(self.revoke_button)
        side.addWidget(button("备份学习记录", self.export_records))
        self.restore_button = button("恢复学习记录", self.import_records)
        side.addWidget(self.restore_button)
        sidebar.setMinimumWidth(185)
        splitter.addWidget(sidebar)

        center = QWidget()
        middle = QVBoxLayout(center)
        self.lesson_title = label("", "title")
        middle.addWidget(self.lesson_title)
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(label("本课目标"))
        self.goal = label("")
        card_layout.addWidget(self.goal)
        self.progress_label = label("", "muted")
        card_layout.addWidget(self.progress_label)
        middle.addWidget(card)
        self.conversation = ChatView()
        middle.addWidget(self.conversation, 1)
        entry = QHBoxLayout()
        self.question = QuestionEdit()
        self.question.setPlaceholderText("有什么不明白的，随时问我…")
        self.question.returnPressed.connect(self.send_question)
        entry.addWidget(self.question, 1)
        self.send_button = button("发送", self.send_question, True)
        entry.addWidget(self.send_button)
        middle.addLayout(entry)
        request_actions = QHBoxLayout()
        self.request_status = label("连接模型后可以提问；本地课程可直接浏览。", "muted")
        request_actions.addWidget(self.request_status, 1)
        self.cancel_button = button("取消", lambda: self.client.cancel())
        self.cancel_button.setEnabled(False)
        request_actions.addWidget(self.cancel_button)
        self.retry_button = button("重试", self.retry_last)
        self.retry_button.setEnabled(False)
        request_actions.addWidget(self.retry_button)
        middle.addLayout(request_actions)
        center.setMinimumWidth(340)
        splitter.addWidget(center)

        right = QWidget()
        practice = QVBoxLayout(right)
        practice.addWidget(label("动手练习", "title"))
        self.task = label("")
        practice.addWidget(self.task)
        practice.addWidget(label("practice.py · 草稿自动保存在本机", "muted"))
        self.editor = CodeEditor()
        self.editor.setTabStopDistance(36)
        practice.addWidget(self.editor, 1)
        actions = QHBoxLayout()
        self.check_button = button("提交给 Py妮检查", self.check_code, True)
        actions.addWidget(self.check_button)
        actions.addWidget(button("给我一点提示", self.show_hint))
        practice.addLayout(actions)
        learning_actions = QHBoxLayout()
        self.quiz_button = button("做个理解小测", self.check_understanding)
        self.next_button = button("下一课 →", self.next_lesson)
        learning_actions.addWidget(self.quiz_button)
        learning_actions.addWidget(self.next_button)
        practice.addLayout(learning_actions)
        practice.addWidget(label("发送时会将当前练习代码交给所选模型分析，不执行代码。", "muted"))
        self.companion = QWidget()
        companion_layout = QHBoxLayout(self.companion)
        companion_actions = QVBoxLayout()
        self.bubble = label("需要一点提示吗？")
        companion_actions.addWidget(self.bubble)
        companion_actions.addWidget(button("提示", self.show_hint))
        companion_actions.addWidget(button("休息一下", self.take_break))
        companion_layout.addLayout(companion_actions)
        self.avatar = QPushButton("Py妮\n角色准备中")
        self.avatar.setFixedSize(140, 170)
        self.avatar.setToolTip("点击 Py妮，获得当前练习的提示")
        self.avatar.clicked.connect(self.show_hint)
        image = ROOT / "assets/companion.png"
        if image.exists() and not QPixmap(str(image)).isNull():
            self.avatar.setText("")
            self.avatar.setIcon(QIcon(str(image)))
            self.avatar.setIconSize(QSize(130, 160))
        companion_layout.addWidget(self.avatar)
        practice.addWidget(self.companion)
        self.toggle = button("收起伙伴", self.toggle_companion)
        practice.addWidget(self.toggle, alignment=Qt.AlignmentFlag.AlignRight)
        right.setMinimumWidth(370)
        splitter.addWidget(right)
        splitter.setSizes([200, 500, 440])
        self.setCentralWidget(root)
        self.save_status = label("", "muted")
        layout.addWidget(self.save_status)
        self.statusBar().showMessage("学习记录保存在本机 · API 密钥仍只在本次运行内保留")
        self.lesson_list.currentRowChanged.connect(self.select_lesson)
        self.editor.textChanged.connect(self.on_edit)
        self.question.textChanged.connect(self.on_edit)
        self.lesson_list.setCurrentRow(start_index)

    def select_lesson(self, index):
        if self.current_lesson is not None:
            self.drafts[self.current_lesson] = self.editor.toPlainText()
            self.questions[self.current_lesson] = self.question.text()
            self.dirty.add(self.current_lesson)
        self.current_lesson = index
        self.help_mode = False
        self.help_button.setText("代码求助")
        lesson = LESSONS[index]
        self.lesson_title.setText(f"{index + 1:02d}  {lesson['title']}")
        self.goal.setText(lesson["goal"])
        self.task.setText(lesson["task"])
        self.editor.blockSignals(True)
        self.question.blockSignals(True)
        self.editor.setPlainText(self.drafts.get(index, lesson["code"]))
        self.question.setText(self.questions.get(index, ""))
        self.editor.blockSignals(False)
        self.question.blockSignals(False)
        if self.progress[index]["status"] == "尚未开始":
            self.progress[index].update(status="看过示例", evidence="打开了本课讲解，尚未检查练习。")
        self.render_conversation()
        self.retry_button.setEnabled(self.retry_data is not None and self.retry_data[0] == index)
        self.bubble.setText("需要一点提示吗？")
        self.on_edit(mark_practice=False)

    def on_edit(self, *_args, mark_practice=True):
        if self.current_lesson is None:
            return
        index = self.current_lesson
        self.drafts[index] = self.editor.toPlainText()
        self.questions[index] = self.question.text()
        record = self.progress[index]
        if mark_practice and record["status"] in ("看过示例", "尚未开始") and self.drafts[index] != LESSONS[index]["code"]:
            record.update(status="正在练习", evidence="正在修改练习代码，尚未完成检查。")
        self.dirty.add(index)
        self.update_progress_ui()
        self.save_status.setText(self.storage_error or "正在保存到本机…")
        self.save_timer.start(600)

    def update_progress_ui(self):
        record = self.progress[self.current_lesson]
        supported = LESSONS[self.current_lesson]["id"] in CHECKPOINTS
        checked = record["checked_code"] is not None and record["checked_code"] == self.editor.toPlainText()
        changed = record["checked_code"] is not None and not checked
        self.progress_label.setText(f'学习状态：{record["status"]} · {record["source"]}' + ("\n代码已改动，需重新检查当前练习。" if changed else ""))
        self.progress_label.setToolTip(record["evidence"])
        self.quiz_button.setVisible(supported and not self.help_mode)
        self.check_button.setText("请 Py妮看代码" if self.help_mode or not supported else "检查本课练习")
        self.quiz_button.setEnabled(supported and checked and not self.client.busy)
        self.quiz_button.setToolTip("先让当前代码通过本地练习检查，再确认理解。")
        self.next_button.setText("回顾学习记录" if self.current_lesson == len(LESSONS) - 1 else "下一课 →")
        self.next_button.setEnabled(not self.client.busy)
        for index, lesson in enumerate(LESSONS):
            done = self.progress[index]["status"] in ("提示下完成", "独立完成")
            self.lesson_list.item(index).setText(f'{"✓" if done else f"{index + 1:02d}"}  {lesson["name"]}')

    def persist_changes(self):
        self.save_timer.stop()
        if not self.store:
            self.save_status.setText(self.storage_error or "本次会话模式 · 内容未写入磁盘")
            return not self.dirty
        try:
            for index in sorted(self.dirty):
                data = {"draft": self.drafts.get(index, LESSONS[index]["code"]), "question": self.questions.get(index, ""),
                        "progress": deepcopy(self.progress[index]), "chats": deepcopy(self.chats[index])}
                revision, updated = self.store.save(LESSONS[index]["id"], data, self.revisions[index], current=index == self.current_lesson)
                self.revisions[index], self.timestamps[index] = revision, updated
                self.dirty.discard(index)
            self.storage_error = ""
            self.save_status.setText("已保存到本机 · 下次从这里继续")
            return True
        except (OSError, sqlite3.Error, ValueError) as exc:
            self.storage_error = str(exc) if isinstance(exc, OSError) else "学习记录保存失败，请检查目录权限或磁盘空间。"
            self.save_status.setText("尚未保存：" + self.storage_error)
            return False

    def render_conversation(self):
        lesson = LESSONS[self.current_lesson]
        intro = "嗨，我是 Py妮。今天先让 Python 说一句话，我们从这一行开始吧。" if self.current_lesson == 0 else "这一小节，我们一起学点新东西。先看看下面的例子吧。"
        messages = [{"key": "lesson", "role": "assistant", "subtitle": "本课小讲解",
                     "text": f'{intro}\n\n{lesson["explanation"]}\n\n```python\n{lesson["code"]}\n```\n\n轮到你试一试啦。右边有个小练习，卡住时点“给我一点提示”，我们一起看。'}]
        for index, turn in enumerate(self.chats[self.current_lesson]):
            if turn.get("local"):
                messages.append({"key": (index, "hint"), "role": "assistant", "subtitle": turn.get("label", "一点小提示"), "text": turn["reply"]})
                continue
            messages.append({"key": (index, "user"), "role": "user", "text": turn.get("display_question", turn["question"]), "code": turn.get("code", "")})
            messages.append({"key": (index, "reply"), "role": "assistant", "subtitle": "正在回复…" if turn["status"] == "pending" else "一起想一想", "model": turn["model"], "text": (turn["reply"] or "让我看看你的问题，稍等一下…") + ("\n\n工具记录：\n" + "\n".join(turn["tools"]) if turn.get("tools") else ""), "error": turn.get("error", "")})
        self.conversation.set_messages(self.current_lesson, messages)

    def show_hint(self):
        record = self.progress[self.current_lesson]
        lesson = LESSONS[self.current_lesson]
        hints = CHECKPOINTS[lesson["id"]]["hints"] if lesson["id"] in CHECKPOINTS else (lesson["hint"],)
        hint = hints[min(record["hints"], len(hints) - 1)]
        record["hints"] = min(record["hints"] + 1, 1000)
        record["assisted"] = True
        self.chats[self.current_lesson].append({"local": True, "reply": hint})
        self.render_conversation()
        self.bubble.setText("提示放在左边啦，试着改一改。")
        self.on_edit(mark_practice=False)

    def send_question(self):
        question = self.question.text().strip()
        if question:
            self.request_reply(question, self.editor.toPlainText(), self.question.text())

    def check_code(self):
        index = self.current_lesson
        checkpoint = CHECKPOINTS.get(LESSONS[index]["id"])
        if checkpoint and not self.help_mode:
            passed, feedback = checkpoint["checker"](self.editor.toPlainText())
            record = self.progress[index]
            record.update(checked_code=self.editor.toPlainText() if passed else None, status="练习通过，待确认理解" if passed else "正在练习",
                          evidence=checkpoint["exercise_evidence"] if passed else "本地练习检查未通过，继续修改。", source="本地练习检查")
            if not passed:
                record["assisted"] = True
            self.chats[index].append({"local": True, "label": "练习小检查", "reply": feedback})
            self.render_conversation()
            self.on_edit(mark_practice=False)
            return
        self.request_reply("请检查我当前的练习代码：是否符合本课任务？先解释问题并给提示，不要直接替我完成。", self.editor.toPlainText(), "")

    def check_understanding(self):
        index = self.current_lesson
        lesson_id = LESSONS[index]["id"]
        checkpoint = CHECKPOINTS.get(lesson_id)
        if not checkpoint or self.help_mode or self.client.busy or self.progress[index]["checked_code"] != self.editor.toPlainText():
            return
        dialog = UnderstandingDialog(self, lesson_id=lesson_id)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        record = self.progress[index]
        record["assisted"] |= dialog.had_mistake
        if accepted:
            status = "提示下完成" if record["assisted"] else "独立完成"
            record.update(status=status, source="本地练习与理解小测", evidence=checkpoint["completion_evidence"])
            self.chats[index].append({"local": True, "label": "本课小结", "reply": f"这次练习和理解小测都完成了。本课记录为“{status}”。\n\n{checkpoint['recap']}"})
            self.render_conversation()
        self.on_edit(mark_practice=False)
        self.persist_changes()
        dialog.deleteLater()

    def next_lesson(self):
        if not self.client.busy:
            if self.current_lesson < len(LESSONS) - 1:
                self.lesson_list.setCurrentRow(self.current_lesson + 1)
            else:
                self.show_records()

    def show_settings(self):
        if self.client.busy:
            return
        dialog = SettingsDialog(self.model_config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.model_config = dialog.result_config
            self.connected = True
            self.connection_status.setText(f"● {self.model_config.provider} 已连接")
            self.request_status.setText("模型已准备好，可以发送问题或检查代码。")
        dialog.deleteLater()

    def show_help(self):
        self.help_mode = not self.help_mode
        self.help_button.setText("返回课程练习" if self.help_mode else "代码求助")
        self.task.setText("把相关代码放在这里，说说你遇到的问题，我们一起看。" if self.help_mode else LESSONS[self.current_lesson]["task"])
        self.question.setPlaceholderText("描述问题或报错，在右侧粘贴相关代码…" if self.help_mode else "有什么不明白的，随时问我…")
        self.question.setFocus()
        self.update_progress_ui()
        self.statusBar().showMessage("代码求助 · 发送时包含右侧代码和本课最近的对话" if self.help_mode else "已回到本课练习")

    def request_reply(self, question, code, input_text):
        if self.client.busy:
            return
        if not self.connected:
            self.show_settings()
            if self.connected:
                self.request_status.setText("模型已连接，请再次点击发送或提交检查。")
            return
        if len(question) + len(code) > 24_000:
            self.request_status.setText("内容较长，请只保留相关代码和问题（最多 24000 个字符）。")
            return
        lesson = LESSONS[self.current_lesson]
        system = (ROOT / "prompts/system_prompt.txt").read_text(encoding="utf-8")
        system += f'\n当前课程：{lesson["name"]}\n学习目标：{lesson["goal"]}\n练习任务：{lesson["task"]}'
        record = self.progress[self.current_lesson]
        system += f'\n学习状态（记录并非全面掌握证明）：{record["status"]}\n记录依据：{record["evidence"]}\n已使用本地提示次数：{record["hints"]}'
        messages = [{"role": "system", "content": system}]
        previous = [turn for turn in self.chats[self.current_lesson] if turn.get("status") == "success"][-6:]
        budget = 40_000
        retained = []
        for turn in reversed(previous):
            size = len(turn["question"]) + len(turn["reply"])
            if size > budget:
                break
            retained.insert(0, turn)
            budget -= size
        for turn in retained:
            messages.extend([{"role": "user", "content": turn["question"]}, {"role": "assistant", "content": turn["reply"]}])
        content = f"{question}\n\n当前练习代码（供阅读分析，未执行）：\n```python\n{code}\n```"
        messages.append({"role": "user", "content": content})
        self.tool_context = (self.current_lesson, code)
        enabled_tools = (STUDY_TOOLS + (PROJECT_TOOLS if self.project_tools.root else [])) if self.model_config.tools_enabled else None
        try:
            self.client.send(self.model_config, messages, tools=enabled_tools, execute=self.execute_tool)
        except ValueError as exc:
            self.request_status.setText(str(exc))
            return
        self.retry_data = (self.current_lesson, question, code, input_text)
        self.pending_turn = {"question": content, "display_question": question, "code": code, "reply": "", "status": "pending", "model": self.model_config.model}
        self.chats[self.current_lesson].append(self.pending_turn)
        self.progress[self.current_lesson]["assisted"] = True
        self.on_edit(mark_practice=False)
        self.set_busy(True)
        self.render_conversation()
        self.request_status.setText("Py妮正在思考… 可以取消；最长等待 120 秒。" + (" Agent 模式整段显示回复。" if enabled_tools else ""))
        self.bubble.setText("我正在看你的问题…")

    def set_busy(self, busy):
        for widget in (self.send_button, self.check_button, self.lesson_list, self.settings_button, self.folder_button, self.help_button, self.restore_button):
            widget.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.retry_button.setEnabled(not busy and self.retry_data is not None and self.retry_data[0] == self.current_lesson)
        self.update_progress_ui()

    def receive_delta(self, piece):
        if self.pending_turn:
            self.pending_turn["reply"] += piece
            if not self.render_timer.isActive():
                self.render_timer.start(80)

    def receive_reply(self, result):
        self.render_timer.stop()
        self.pending_turn.update(reply=result["content"], status="success")
        if self.retry_data[3] and self.question.text() == self.retry_data[3]:
            self.question.clear()
        self.pending_turn = None
        self.retry_data = None
        self.set_busy(False)
        self.render_conversation()
        self.connection_status.setText(f"● {self.model_config.provider} 已连接")
        self.request_status.setText("回复已完成 · AI 分析未运行代码，可继续追问。")
        self.bubble.setText("我回复好啦。哪里还不明白，我们接着聊。")
        self.on_edit(mark_practice=False)

    def receive_error(self, message):
        self.render_timer.stop()
        if self.pending_turn:
            self.pending_turn.update(status="failed", error=message)
            if not self.pending_turn["reply"]:
                self.pending_turn["reply"] = "未收到回复。"
        self.pending_turn = None
        self.set_busy(False)
        self.render_conversation()
        self.request_status.setText(message)
        self.connection_status.setText(f"○ {self.model_config.provider} · 上次请求未完成")
        self.bubble.setText("输入还在，我们可以再试一次。")
        self.on_edit(mark_practice=False)

    def retry_last(self):
        if self.retry_data and self.retry_data[0] == self.current_lesson:
            self.request_reply(*self.retry_data[1:])

    def show_records(self):
        dialog = RecordsDialog(self.progress, self.timestamps, self.current_lesson, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            index, status, note = dialog.correction
            self.progress[index].update(status=status, source="用户自评", note=note, evidence=note or "由用户自行调整学习状态。")
            self.dirty.add(index)
            self.update_progress_ui()
            self.persist_changes()
        dialog.deleteLater()

    def select_project(self):
        directory = QFileDialog.getExistingDirectory(self, "选择希望 Py妮阅读的代码文件夹")
        if not directory:
            return
        answer = QMessageBox.question(self, "允许模型阅读这个文件夹？",
            "启用 Agent 后，模型可按需列出并读取此目录内的 Python 和说明文本，内容将发送到你选择的 API 服务。\n\n"
            "请选择专门的练习文件夹，先移除代码中的密钥等私人内容。授权仅限本次运行，可以随时取消。\n\n" + directory)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.project_tools.select(directory)
        except (OSError, ValueError):
            QMessageBox.warning(self, "无法打开", "无法访问所选文件夹。")
            return
        self.folder_status.setText("已授权：" + self.project_tools.root.name)
        self.folder_status.setToolTip(str(self.project_tools.root))
        self.revoke_button.setEnabled(True)
        self.request_status.setText("文件夹已授权。在设置中检测工具调用后，可提问让 Py妮阅读文件。")

    def revoke_project(self):
        if self.client.busy:
            self.client.cancel("已取消文件夹授权和当前请求；此前已发送的内容无法撤回。")
        self.project_tools.revoke()
        self.folder_status.setText("尚未授权文件夹")
        self.folder_status.setToolTip("")
        self.revoke_button.setEnabled(False)

    def execute_tool(self, name, args):
        index, code = self.tool_context
        if name == "read_project_file" and set(args) == {"path"}:
            return self.project_tools.read_file(args["path"])
        if args:
            raise ValueError("参数无效。")
        if name == "list_project_files":
            return self.project_tools.list_files()
        if name == "get_learning_progress":
            return {"lessons": [{"lesson": lesson["name"], "status": self.progress[i]["status"],
                    "evidence": self.progress[i]["evidence"]} for i, lesson in enumerate(LESSONS)],
                    "current": LESSONS[index]["name"], "next_step": "检查练习通过后，完成理解小测。"}
        if name == "check_current_exercise":
            passed, feedback = CHECKPOINTS[LESSONS[index]["id"]]["checker"](code)
            return {"passed_static_check": passed, "feedback": feedback, "executed": False,
                    "note": "仅检查发送时的代码快照；未更改学习状态。"}
        raise ValueError("未知工具。")

    def tool_activity(self, message):
        self.request_status.setText(message + " · 正在整理回复…")
        if self.pending_turn:
            self.pending_turn.setdefault("tools", []).append(message)
            self.on_edit(mark_practice=False)

    def export_records(self):
        self.on_edit(mark_practice=False)
        destination, _ = QFileDialog.getSaveFileName(self, "备份学习记录（包含对话和代码，请妥善保管）", "PyNi-study.json", "JSON (*.json)")
        if not destination:
            return
        data = {"format": "pyni-study", "version": 1, "current": LESSONS[self.current_lesson]["id"],
                "lessons": {lesson["id"]: {"draft": self.drafts.get(i, lesson["code"]),
                    "question": self.questions.get(i, ""), "progress": self.progress[i], "chats": self.chats[i]}
                    for i, lesson in enumerate(LESSONS)}}
        from PySide6.QtCore import QSaveFile, QIODevice
        file = QSaveFile(destination)
        raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        if not file.open(QIODevice.OpenModeFlag.WriteOnly) or file.write(raw) != len(raw) or not file.commit():
            QMessageBox.warning(self, "备份失败", "请检查保存位置和剩余空间。")
            return
        self.request_status.setText("备份已导出，包含学习内容；不包含 API 配置或文件夹授权。")

    def import_records(self):
        if self.client.busy or not self.store:
            return
        source, _ = QFileDialog.getOpenFileName(self, "选择 Py妮学习备份", "", "JSON (*.json)")
        if not source:
            return
        try:
            with open(source, "rb") as file:
                raw = file.read(10_000_001)
            if len(raw) > 10_000_000:
                raise ValueError("备份超过 10 MB。")
            data = json.loads(raw)
            StudyStore.validate_backup(data, [lesson["id"] for lesson in LESSONS])
        except (OSError, ValueError, RecursionError):
            QMessageBox.warning(self, "无法恢复", "备份格式不正确或文件过大，现有记录未更改。")
            return
        if QMessageBox.question(self, "恢复学习记录", "这会替换当前五节课的草稿、对话和进度。需要保留当前内容时，请先备份。确定恢复吗？") != QMessageBox.StandardButton.Yes:
            return
        self.save_timer.stop()
        try:
            self.store.restore(data, {lesson["id"]: self.revisions[i] for i, lesson in enumerate(LESSONS)})
            loaded, selected = self.store.load([lesson["id"] for lesson in LESSONS])
        except (OSError, sqlite3.Error, ValueError):
            QMessageBox.warning(self, "恢复失败", "未能恢复，请检查文件权限或其他窗口的修改。")
            return
        self.current_lesson = None
        self.dirty.clear()
        for i, lesson in enumerate(LESSONS):
            row, revision, updated = loaded[lesson["id"]]
            self.drafts[i], self.questions[i] = row["draft"], row["question"]
            self.progress[i], self.chats[i] = row["progress"], row["chats"]
            for turn in self.chats[i]:
                if turn.get("status") == "pending":
                    turn.update(status="failed", error="备份中的请求未完成，请重新发送。")
            self.revisions[i], self.timestamps[i] = revision, updated
        self.retry_data = None
        index = next(i for i, lesson in enumerate(LESSONS) if lesson["id"] == selected)
        self.lesson_list.blockSignals(True)
        self.lesson_list.setCurrentRow(index)
        self.lesson_list.blockSignals(False)
        self.select_lesson(index)
        self.request_status.setText("学习记录已恢复。")

    def take_break(self):
        self.bubble.setText("休息一下吧，回来再继续。")

    def toggle_companion(self):
        visible = not self.companion.isVisible()
        self.companion.setVisible(visible)
        self.toggle.setText("收起伙伴" if visible else "展开伙伴")

    def closeEvent(self, event):
        if self.client.busy:
            answer = QMessageBox.question(self, "正在请求模型", "要取消当前请求并退出吗？")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.client.cancel()
        self.on_edit(mark_practice=False)
        if not self.persist_changes():
            answer = QMessageBox.question(self, "尚有内容未保存", "学习记录未能保存，退出可能丢失本次修改。要直接退出吗？")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()
