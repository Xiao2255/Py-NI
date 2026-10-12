"""聊天呈现的回归检查：流式更新、代码排版与阅读位置。"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog
from ui.chat_view import ChatView, MessageText, show_text_dialog

APP = QApplication.instance() or QApplication([])


def settle():
    for _ in range(10):
        APP.processEvents()


class ChatViewTests(unittest.TestCase):
    def test_new_long_lesson_opens_at_beginning(self):
        view = ChatView()
        view.resize(380, 240)
        view.show()
        view.set_messages('variables', [{"key": "lesson", "role": "assistant", "text": "变量的讲解。\n\n" * 30}])
        settle()
        self.assertGreater(view.verticalScrollBar().maximum(), 0)
        self.assertEqual(view.verticalScrollBar().value(), 0)
        view.close()
        view.deleteLater()

    def test_markdown_code_and_plain_user_text(self):
        text = MessageText()
        text.resize(300, 100)
        text.set_message('试试 **这一行**：\n\n```python\nif True:\n    print("你好")\n```')
        self.assertIn('    print("你好")', text.toPlainText())
        self.assertNotIn('```', text.toPlainText())
        self.assertNotIn('**', text.toPlainText())
        text.set_message('<img src="file:///private.png"> **原文**', markdown=False)
        self.assertIn('<img', text.toPlainText())
        self.assertIn('**原文**', text.toPlainText())
        self.assertFalse(text.openLinks())
        text.deleteLater()

    def test_stream_update_reuses_bubble_and_respects_scroll(self):
        view = ChatView()
        view.resize(380, 250)
        view.show()
        messages = [{"key": i, "role": "assistant", "text": "一起看看这段代码。\n\n" * 6} for i in range(5)]
        view.set_messages(0, messages)
        settle()
        bubble = view.bubbles[4]
        self.assertGreater(view.verticalScrollBar().maximum(), 0)
        view.verticalScrollBar().setValue(0)
        messages[-1]["text"] += "新增的流式回复。\n\n" * 5
        view.set_messages(0, messages)
        settle()
        self.assertIs(view.bubbles[4], bubble)
        self.assertEqual(view.verticalScrollBar().value(), 0)
        view.set_messages(1, [{"key": "new", "role": "user", "text": "新的一课"}])
        settle()
        self.assertEqual(len(view.bubbles), 1)
        self.assertEqual(view.toPlainText(), "新的一课")
        view.close()
        view.deleteLater()

    def test_expanded_answer_dialog(self):
        observed = []
        def inspect():
            dialog = APP.activeModalWidget()
            observed.append(isinstance(dialog, QDialog))
            reader = dialog.findChild(MessageText)
            observed.append(reader.toPlainText() == "一起来看")
            dialog.accept()
        QTimer.singleShot(0, inspect)
        show_text_dialog(None, "Py妮的回答", "**一起来看**")
        self.assertEqual(observed, [True, True])


if __name__ == "__main__":
    unittest.main()
