"""轻量 Python 编辑体验与支持多行的提问输入框。"""
import re
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit


class PythonHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        for pattern, color in [
            (r'\b(?:False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b', '#7957af'),
            (r'\b\d+(?:\.\d+)?\b', '#a85c26'),
            (r'\b(?:print|range|len|str|int|float|input)\b', '#287d94'),
            (r'"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|#[^\n]*', '#548563'),
        ]:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            for match in re.finditer(pattern, text):
                # Qt 的字符位置使用 UTF-16。
                start = len(text[:match.start()].encode('utf-16-le')) // 2
                length = len(match.group().encode('utf-16-le')) // 2
                self.setFormat(start, length, fmt)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = PythonHighlighter(self.document())
        self.setPlaceholderText("在这里试着写 Python…")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab and not event.modifiers():
            self.insertPlainText("    ")
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers():
            cursor = self.textCursor()
            if not cursor.hasSelection():
                before = cursor.block().text()[:cursor.positionInBlock()]
                indent = re.match(r" *", before).group()
                self.insertPlainText("\n" + indent + ("    " if before.rstrip().endswith(":") else ""))
                return
        super().keyPressEvent(event)


class QuestionEdit(QPlainTextEdit):
    returnPressed = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedHeight(76)
        self.setToolTip("Enter 换行 · Ctrl+Enter 发送")

    def text(self):
        return self.toPlainText()

    def setText(self, text):
        self.setPlainText(text)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.returnPressed.emit()
            return
        super().keyPressEvent(event)
