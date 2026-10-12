"""理解小测与可修正的学习记录。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
)
from services.learning import STATUSES, CHECKPOINTS, check_understanding
from .lessons import LESSONS


class UnderstandingDialog(QDialog):
    def __init__(self, parent=None, lesson_id="print"):
        super().__init__(parent)
        self.lesson_id = lesson_id
        checkpoint = CHECKPOINTS[lesson_id]
        self.setWindowTitle("读懂了吗？来试一个小判断")
        self.resize(480, 420)
        self.had_mistake = False
        layout = QVBoxLayout(self)
        heading = QLabel("先不运行，想一想下面的代码会显示什么：")
        layout.addWidget(heading)
        code = QPlainTextEdit(checkpoint["quiz_code"])
        code.setReadOnly(True)
        code.setFixedHeight(min(180, 30 + 22 * len(checkpoint["quiz_code"].splitlines())))
        layout.addWidget(code)
        self.output = QPlainTextEdit()
        self.output.setPlaceholderText("在这里写出你预测的输出，注意换行…")
        self.output.setMaximumHeight(110)
        layout.addWidget(self.output)
        question = QLabel(checkpoint["quiz_question"])
        question.setWordWrap(True)
        layout.addWidget(question)
        self.reason = QComboBox()
        self.reason.addItems(("请选择一个解释", *checkpoint["quiz_options"]))
        layout.addWidget(self.reason)
        self.feedback = QLabel("慢慢想，不确定也可以试一试。")
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        buttons = QHBoxLayout()
        later = QPushButton("待会儿再试")
        later.clicked.connect(self.reject)
        submit = QPushButton("确认答案")
        submit.setObjectName("primary")
        submit.clicked.connect(self.check)
        buttons.addWidget(later)
        buttons.addWidget(submit)
        layout.addLayout(buttons)

    def check(self):
        if check_understanding(self.output.toPlainText(), self.reason.currentText(), self.lesson_id):
            self.accept()
        else:
            self.had_mistake = True
            self.feedback.setText(CHECKPOINTS[self.lesson_id]["quiz_feedback"])


class RecordsDialog(QDialog):
    def __init__(self, progress, timestamps, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle("我的学习记录")
        self.resize(770, 550)
        self.progress = progress
        self.correction = None
        layout = QVBoxLayout(self)
        names = "、".join(lesson["name"] for lesson in LESSONS if lesson["id"] in CHECKPOINTS)
        note = QLabel(f"{names}均有本地练习检查和理解小测。完成记录不是实际运行结果，也不代表全面掌握；你可以根据实际理解情况修正自评。")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = QTableWidget(len(LESSONS), 3)
        self.table.setHorizontalHeaderLabels(("课程", "学习状态", "依据 / 来源"))
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 185)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        for index, lesson in enumerate(LESSONS):
            record = progress[index]
            for column, text in enumerate((lesson["name"], record["status"], f'{record["source"]}：{record["evidence"]}')):
                item = QTableWidgetItem(text)
                item.setToolTip(text + (f'\n保存时间（UTC）：{timestamps.get(index, "")}' if timestamps.get(index) else ""))
                self.table.setItem(index, column, item)
        self.table.resizeRowsToContents()
        layout.addWidget(self.table)
        self.state = QComboBox()
        self.state.addItems(STATUSES)
        layout.addWidget(QLabel("修正选中课程的状态（会明确标记为你的自评）："))
        layout.addWidget(self.state)
        self.note = QPlainTextEdit()
        self.note.setPlaceholderText("例如：能照着写，但还不太会自己修改。")
        self.note.setMaximumHeight(75)
        layout.addWidget(self.note)
        self.table.currentCellChanged.connect(self.select_record)
        self.table.selectRow(current)
        self.select_record(current)
        actions = QHBoxLayout()
        close = QPushButton("返回学习")
        close.clicked.connect(self.reject)
        save = QPushButton("保存这条自评")
        save.clicked.connect(self.save_correction)
        actions.addWidget(close)
        actions.addWidget(save)
        layout.addLayout(actions)

    def select_record(self, row, *_):
        if row >= 0:
            self.state.setCurrentText(self.progress[row]["status"])
            self.note.setPlainText(self.progress[row]["note"])

    def save_correction(self):
        row = self.table.currentRow()
        if row >= 0:
            self.correction = (row, self.state.currentText(), self.note.toPlainText()[:2000])
            self.accept()
