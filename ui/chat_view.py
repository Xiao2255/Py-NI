"""聊天气泡：正文使用阅读字体，Markdown 代码块保留等宽字体。"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextDocument, QTextOption
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget,
)


class MessageText(QTextBrowser):
    """不打开链接或加载图片/本地文件；气泡高度跟随文字。"""
    def __init__(self, parent=None, fit_content=True):
        super().__init__(parent)
        self.fit_content = fit_content
        self.setObjectName("messageText")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        if fit_content:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.document().setDocumentMargin(2)
        self.document().documentLayout().documentSizeChanged.connect(self.fit_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed if fit_content else QSizePolicy.Policy.Expanding)

    def loadResource(self, resource_type, name):
        return None

    def set_message(self, text, markdown=True):
        if markdown:
            features = QTextDocument.MarkdownFeature.MarkdownDialectGitHub | QTextDocument.MarkdownFeature.MarkdownNoHTML
            self.document().setMarkdown(text, features)
        else:
            self.setPlainText(text)
        self.fit_height()

    def fit_height(self, *_):
        if not self.fit_content:
            return
        self.document().setTextWidth(max(60, self.viewport().width()))
        height = max(30, int(self.document().size().height()) + 6)
        if height != self.height():
            self.setFixedHeight(height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_height()

    def wheelEvent(self, event):
        if self.fit_content:
            event.ignore()  # 让外层聊天区域滚动，避免鼠标停在文字上时被截住。
        else:
            super().wheelEvent(event)


def show_text_dialog(parent, title, text, markdown=True):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(650, 540)
    layout = QVBoxLayout(dialog)
    reader = MessageText(fit_content=False)
    reader.set_message(text, markdown)
    layout.addWidget(reader)
    close = QPushButton("读完啦，返回聊天")
    close.clicked.connect(dialog.accept)
    layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
    dialog.exec()


class MessageBubble(QFrame):
    def __init__(self, role, parent=None):
        super().__init__(parent)
        self.role = role
        self.text = ""
        self.snapshot = ""
        self.previous = None
        self.setObjectName("userBubble" if role == "user" else "assistantBubble")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        header = QHBoxLayout()
        badge = QLabel("你" if role == "user" else "妮")
        badge.setObjectName("chatBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(27, 27)
        header.addWidget(badge)
        self.name = QLabel("你" if role == "user" else "Py妮")
        self.name.setObjectName("chatName")
        header.addWidget(self.name)
        header.addStretch()
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("chatMeta")
        header.addWidget(self.subtitle)
        layout.addLayout(header)
        self.body = MessageText()
        layout.addWidget(self.body)
        self.error = QLabel()
        self.error.setObjectName("chatError")
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        actions = QHBoxLayout()
        actions.addStretch()
        self.details = QPushButton("查看本次代码")
        self.details.setObjectName("chatAction")
        self.details.clicked.connect(lambda: show_text_dialog(self, "这次发送的代码快照", self.snapshot, False))
        self.details.hide()
        actions.addWidget(self.details)
        self.expand = QPushButton("展开阅读")
        self.expand.setObjectName("chatAction")
        self.expand.clicked.connect(lambda: show_text_dialog(self, "Py妮的回答", self.text, self.role != "user"))
        self.expand.setVisible(role != "user")
        actions.addWidget(self.expand)
        self.copy = QPushButton("复制")
        self.copy.setObjectName("chatAction")
        self.copy.clicked.connect(self.copy_text)
        actions.addWidget(self.copy)
        layout.addLayout(actions)

    def update_message(self, message):
        if message == self.previous:
            return
        self.previous = dict(message)
        self.text = message["text"]
        self.snapshot = message.get("code", "")
        self.body.set_message(self.text, self.role != "user")
        self.subtitle.setText(message.get("subtitle", ""))
        self.name.setToolTip(message.get("model", ""))
        self.error.setText(message.get("error", ""))
        self.error.setVisible(bool(message.get("error")))
        self.details.setVisible(bool(self.snapshot))

    def copy_text(self):
        QApplication.clipboard().setText(self.text)
        self.copy.setText("已复制")
        QTimer.singleShot(1200, self, lambda: self.copy.setText("复制"))


class ChatView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatView")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.container = QWidget()
        self.container.setObjectName("chatCanvas")
        self.rows = QVBoxLayout(self.container)
        self.rows.setContentsMargins(10, 12, 10, 12)
        self.rows.setSpacing(16)
        self.rows.addStretch()
        self.setWidget(self.container)
        self.scope = None
        self.bubbles = {}
        self.follow_bottom = True
        bar = self.verticalScrollBar()
        bar.valueChanged.connect(self.track_scroll)
        bar.rangeChanged.connect(self.range_changed)

    def track_scroll(self, value):
        self.follow_bottom = value >= self.verticalScrollBar().maximum() - 24

    def range_changed(self, *_):
        if self.follow_bottom:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def set_messages(self, scope, messages):
        new_intro = scope != self.scope and len(messages) == 1
        if scope == self.scope and self.verticalScrollBar().maximum() == 0:
            self.follow_bottom = True
        if scope != self.scope:
            self.scope = scope
            self.bubbles.clear()
            while self.rows.count() > 1:
                item = self.rows.takeAt(0)
                item.widget().hide()
                item.widget().deleteLater()
            self.follow_bottom = True
        for message in messages:
            key = message["key"]
            if key not in self.bubbles:
                row = QWidget()
                row.setObjectName("chatRow")
                row_layout = QHBoxLayout(row)
                user = message["role"] == "user"
                row_layout.setContentsMargins(32 if user else 0, 0, 0 if user else 16, 0)
                bubble = MessageBubble(message["role"])
                row_layout.addWidget(bubble)
                self.rows.insertWidget(self.rows.count() - 1, row)
                self.bubbles[key] = bubble
            self.bubbles[key].update_message(message)
        if new_intro:
            QTimer.singleShot(0, self, self.show_intro_start)

    def show_intro_start(self):
        if len(self.bubbles) == 1:
            self.verticalScrollBar().setValue(0)
            self.follow_bottom = False

    def toPlainText(self):
        return "\n\n".join(bubble.body.toPlainText() for bubble in self.bubbles.values())
