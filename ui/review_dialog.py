"""可离线使用的复习题；只有提交完整答案才计入一次尝试。"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QComboBox, QPushButton
from services.review import REVIEW_QUESTIONS


class ReviewDialog(QDialog):
    def __init__(self, lesson_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle('换个例子，复习一下')
        self.resize(520, 540)
        self.attempts = 0
        self.passed = False
        self.question = REVIEW_QUESTIONS[lesson_id]
        code, _, question, options, _, _ = self.question
        layout = QVBoxLayout(self)
        intro = QLabel('先预测输出，再选出原因。这里的练习不会覆盖课程草稿或原来的成绩。')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        sample = QPlainTextEdit(code)
        sample.setReadOnly(True)
        sample.setMaximumHeight(175)
        layout.addWidget(sample)
        self.output = QPlainTextEdit()
        self.output.setPlaceholderText('预测输出，每一行分别填写…')
        self.output.setMaximumHeight(110)
        layout.addWidget(self.output)
        layout.addWidget(QLabel(question))
        self.reason = QComboBox()
        self.reason.addItems(('请选择原因', *options))
        layout.addWidget(self.reason)
        self.feedback = QLabel('不确定也可以试一试，我们会一起检查。')
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        self.submit = QPushButton('检查我的答案')
        self.submit.clicked.connect(self.check)
        layout.addWidget(self.submit)
        close = QPushButton('返回学习')
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def check(self):
        if self.passed:
            return
        if not self.output.toPlainText().strip() or self.reason.currentIndex() == 0:
            self.feedback.setText('先写下预测的输出，再选择一个原因。还没填完不会记作答错。')
            return
        self.attempts += 1
        expected = self.question[1].splitlines()
        actual = [line.strip() for line in self.output.toPlainText().strip().splitlines()]
        self.passed = actual == expected and self.reason.currentText() == self.question[4]
        if self.passed:
            self.feedback.setText('这道新题独立答对了。' if self.attempts == 1 else '根据提示重新想过后，这次答对了。')
            self.submit.setEnabled(False)
            self.output.setReadOnly(True)
            self.reason.setEnabled(False)
        else:
            self.feedback.setText(self.question[5] + ' 改好后再检查一次吧。')
