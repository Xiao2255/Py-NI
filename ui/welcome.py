"""启动入口：从基础开始，也保留直接求助的入口。"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


class WelcomeDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("欢迎来到 Py妮")
        self.setMinimumWidth(470)
        self.choice = "study"
        layout = QVBoxLayout(self)
        title = QLabel("每天懂一点，慢慢写出自己的代码。")
        title.setObjectName("brand")
        layout.addWidget(title)
        intro = QLabel("我是 Py妮，陪你从 Python 基础开始。\n\n先看例子，再自己修改代码，最后用小测确认理解。\n课程、提示和练习检查可以离线使用；向 AI 提问前需要连接模型。")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        for text, choice in [("继续我的基础课", "study"), ("我有代码问题，直接求助", "help"), ("先连接 AI 模型", "settings")]:
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, value=choice: self.choose(value))
            layout.addWidget(button)
        privacy = QLabel("学习记录保存在本机。API 密钥仅在本次运行保留。\n发送问题时会附上练习代码；文件夹阅读需单独授权。")
        privacy.setObjectName("muted")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)

    def choose(self, choice):
        self.choice = choice
        self.accept()
