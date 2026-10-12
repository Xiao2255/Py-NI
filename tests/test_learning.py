import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog
from services.learning import (check_print_exercise, check_variables_exercise, check_understanding, new_progress,
                              check_types_exercise, check_conditions_exercise, check_loops_exercise)
from services.study_store import StudyStore, StudyConflictError
from ui.main_window import MainWindow
from ui.learning_dialogs import UnderstandingDialog

APP = QApplication.instance() or QApplication([])
GOOD_CODE = 'print("小明")\nprint("我开始学 Python 了")'
VARIABLE_CODE = 'language = "Python"\nprint(language)\nlanguage = "我正在学 Python"\nprint(language)'
TYPES_CODE = 'age = 16\nprint(age + 1)\ntext = "16"\nprint(text + "1")'
CONDITIONS_CODE = 'age = 16\nif age >= 18:\n    print("已成年")\nelse:\n    print("未成年")'
LOOPS_CODE = 'for i in range(5):\n    print("继续加油")'


class LearningTests(unittest.TestCase):
    def test_types_rejects_mixed_types_and_hardcoded_results(self):
        self.assertTrue(check_types_exercise(TYPES_CODE)[0])
        for code in (TYPES_CODE.replace('age = 16', 'age = "16"'), TYPES_CODE.replace('age + 1', '17'),
                     TYPES_CODE.replace('text + "1"', 'text + 1'), TYPES_CODE.replace('text = "16"', 'text = 16'),
                     TYPES_CODE.replace('age + 1', 'age + True'), TYPES_CODE.replace('age = 16', 'age = 16.0'),
                     TYPES_CODE + '\nprint("额外输出")'):
            with self.subTest(code=code):
                self.assertFalse(check_types_exercise(code)[0])
        self.assertTrue(check_understanding('6\n42', '数字相加，字符串拼接', 'types'))
        self.assertFalse(check_understanding('6\n6', '数字相加，字符串拼接', 'types'))

    def test_conditions_rejects_wrong_boundary_and_branches(self):
        self.assertTrue(check_conditions_exercise(CONDITIONS_CODE)[0])
        for code in (CONDITIONS_CODE.replace('>=', '>'), CONDITIONS_CODE.replace('>=', '<='),
                     CONDITIONS_CODE.replace('age = 16', 'age = 18'), CONDITIONS_CODE.replace('if age >= 18:', 'if True:'),
                     CONDITIONS_CODE.replace('print("未成年")', 'print("已成年")'),
                     CONDITIONS_CODE.replace('    print("未成年")', 'print("未成年")'),
                     CONDITIONS_CODE.replace('18:', '17:'), CONDITIONS_CODE + '\nprint("额外输出")'):
            with self.subTest(code=code):
                self.assertFalse(check_conditions_exercise(code)[0])
        self.assertTrue(check_understanding('可以报名', '>= 包含等于，条件成立', 'conditions'))
        self.assertFalse(check_understanding('可以报名\n再等等', '>= 包含等于，条件成立', 'conditions'))

    def test_loops_rejects_wrong_count_and_outside_statements(self):
        self.assertTrue(check_loops_exercise(LOOPS_CODE)[0])
        for code in (LOOPS_CODE.replace('range(5)', 'range(4)'), LOOPS_CODE.replace('range(5)', 'range(5.0)'),
                     LOOPS_CODE.replace('for i ', 'for print '), LOOPS_CODE.replace('    print', 'print'),
                     LOOPS_CODE + '\n    break', LOOPS_CODE + '\nelse:\n    print("多一次")',
                     'print("继续加油")\n' * 5, LOOPS_CODE.replace('range(5)', '__import__("os").listdir()')):
            with self.subTest(code=code):
                self.assertFalse(check_loops_exercise(code)[0])
        reason = 'i 是 0、1、2，循环外的结束显示一次'
        self.assertTrue(check_understanding('0\n1\n2\n结束', reason, 'loops'))
        self.assertFalse(check_understanding('1\n2\n3\n结束', reason, 'loops'))
        self.assertFalse(check_understanding('0\n结束\n1\n结束\n2\n结束', reason, 'loops'))

    def test_remaining_checkers_reject_invalid_or_oversized_source(self):
        for checker in (check_types_exercise, check_conditions_exercise, check_loops_exercise):
            for code in ('print("未闭合"', 'x' * 24001, '\x00', ''):
                with self.subTest(checker=checker.__name__, code_length=len(code)):
                    self.assertFalse(checker(code)[0])

    def test_variable_assignment_and_output(self):
        self.assertTrue(check_variables_exercise(VARIABLE_CODE)[0])
        self.assertTrue(check_variables_exercise('# 我的练习\n' + VARIABLE_CODE + '\n')[0])
        cases = (
            (VARIABLE_CODE.replace('print(language)', 'print("language")', 1), "引号"),
            (VARIABLE_CODE.replace('print(language)', 'print(Language)', 1), "大小写"),
            (VARIABLE_CODE.replace('language = "Python"', 'language == "Python"'), "等号"),
            (VARIABLE_CODE.replace('"Python"', 'Python', 1), "引号"),
            (VARIABLE_CODE.replace('"我正在学 Python"', '"Python"'), "第二次"),
            (VARIABLE_CODE.replace('print(language)', 'print(language, end="")', 1), "额外参数"),
            ('name = "小林"\nprint(name)', "四个"),
            (VARIABLE_CODE.replace('language = "Python"', 'language = __import__("os").getcwd()'), "表达式"),
        )
        for code, feedback in cases:
            with self.subTest(code=code):
                passed, message = check_variables_exercise(code)
                self.assertFalse(passed)
                self.assertIn(feedback, message)
        self.assertTrue(check_understanding('狗\nanimal', '变量读取新的值；引号里是固定文字', 'variables'))
        self.assertFalse(check_understanding('猫\nanimal', '变量读取新的值；引号里是固定文字', 'variables'))
        self.assertFalse(check_understanding('狗\n狗', '变量读取新的值；引号里是固定文字', 'variables'))

    def test_static_exercise_checks(self):
        self.assertTrue(check_print_exercise(GOOD_CODE)[0])
        for code in ('print("你好"', 'print("小明")', 'print("小明")\nprint("其他文字")', 'print("")\nprint("我开始学 Python 了")',
                     'print(__import__("os").getcwd())\nprint("我开始学 Python 了")', 'print("小明",end="")\nprint("我开始学 Python 了")'):
            with self.subTest(code=code):
                self.assertFalse(check_print_exercise(code)[0])
        self.assertTrue(check_understanding("你好\nPython", "引号表示这是一段文字"))
        self.assertFalse(check_understanding('"你好"\n"Python"', "引号表示这是一段文字"))

    def test_quiz_mistake_is_recorded(self):
        dialog = UnderstandingDialog()
        dialog.check()
        self.assertTrue(dialog.had_mistake)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)
        dialog.output.setPlainText("你好\nPython")
        dialog.reason.setCurrentText("引号表示这是一段文字")
        dialog.check()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        dialog.deleteLater()

    def test_code_help_still_uses_ai_on_first_lesson(self):
        window = MainWindow(store=False)
        window.show_help()
        self.assertTrue(window.help_mode)
        with patch.object(window, "request_reply") as request:
            window.check_code()
            request.assert_called_once()
        window.show_help()
        self.assertFalse(window.help_mode)
        with patch.object(window, "request_reply") as request:
            window.check_code()
            request.assert_not_called()
        window.save_timer.stop()
        window.deleteLater()


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / "output"
        root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.path = Path(self.temp.name) / "study.sqlite3"
        self.store = StudyStore(self.path)

    def tearDown(self):
        APP.processEvents()
        self.temp.cleanup()

    def test_roundtrip_and_conflict(self):
        data = {"draft": GOOD_CODE, "question": "还没发的问题", "chats": [], "progress": new_progress()}
        revision, _ = self.store.save("print", data, 0)
        loaded, selected = self.store.load(["print", "variables"])
        self.assertEqual(loaded["print"][0], data)
        self.assertEqual(selected, "print")
        with self.assertRaises(StudyConflictError):
            self.store.save("print", data, 0)
        self.assertEqual(revision, 1)

    def test_corruption_is_not_overwritten(self):
        with self.store.connect() as db:
            db.execute("INSERT INTO lessons VALUES ('print','bad-json',1,'test')")
        with self.assertRaises(ValueError):
            self.store.load(["print"])
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT payload FROM lessons").fetchone()[0], "bad-json")

    def test_first_lesson_completion_and_restart(self):
        window = MainWindow(store=self.store)
        window.show_hint()
        window.editor.setPlainText(GOOD_CODE)
        window.check_code()
        self.assertTrue(window.quiz_button.isEnabled())
        self.assertEqual(window.progress[0]["status"], "练习通过，待确认理解")
        def answer():
            dialog = APP.activeModalWidget()
            dialog.output.setPlainText("你好\nPython")
            dialog.reason.setCurrentText("引号表示这是一段文字")
            dialog.check()
        QTimer.singleShot(0, answer)
        window.check_understanding()
        self.assertEqual(window.progress[0]["status"], "提示下完成")
        window.editor.setPlainText('print("修改过")')
        self.assertFalse(window.quiz_button.isEnabled())
        window.question.setText("留下的问题")
        window.next_lesson()
        window.editor.setPlainText('name = "小明"')
        window.persist_changes()
        restored = MainWindow(store=StudyStore(self.path))
        self.assertEqual(restored.current_lesson, 1)
        self.assertEqual(restored.editor.toPlainText(), 'name = "小明"')
        self.assertEqual(restored.progress[0]["status"], "提示下完成")
        restored.lesson_list.setCurrentRow(0)
        self.assertEqual(restored.question.text(), "留下的问题")
        self.assertEqual(restored.editor.toPlainText(), 'print("修改过")')
        self.assertIn("本课记录", restored.chats[0][-1]["reply"])
        for item in (window, restored):
            item.save_timer.stop()
            item.deleteLater()

    def test_no_hint_completion_and_self_correction(self):
        window = MainWindow(store=self.store)
        window.editor.setPlainText(GOOD_CODE)
        window.check_code()
        def answer():
            dialog = APP.activeModalWidget()
            dialog.output.setPlainText("你好\nPython")
            dialog.reason.setCurrentText("引号表示这是一段文字")
            dialog.check()
        QTimer.singleShot(0, answer)
        window.check_understanding()
        self.assertEqual(window.progress[0]["status"], "独立完成")
        def correct():
            dialog = APP.activeModalWidget()
            dialog.state.setCurrentText("需要复习")
            dialog.note.setPlainText("还想再练练")
            dialog.save_correction()
        QTimer.singleShot(0, correct)
        window.show_records()
        saved, _ = self.store.load(["print"])
        self.assertEqual(saved["print"][0]["progress"]["source"], "用户自评")
        self.assertEqual(saved["print"][0]["progress"]["status"], "需要复习")
        window.save_timer.stop()
        window.deleteLater()

    def test_failed_write_does_not_claim_saved(self):
        window = MainWindow(store=self.store)
        with patch.object(self.store, "save", side_effect=OSError("模拟磁盘写入失败")):
            self.assertFalse(window.persist_changes())
            self.assertIn("尚未保存", window.save_status.text())
            self.assertTrue(window.dirty)
        self.assertTrue(window.persist_changes())
        window.save_timer.stop()
        window.deleteLater()

    def test_interrupted_request_recovers_without_resending(self):
        data = {"draft": GOOD_CODE, "question": "等待回答的问题", "progress": new_progress(),
                "chats": [{"question": "等待回答的问题", "reply": "部分回复", "model": "test", "status": "pending"}]}
        self.store.save("print", data, 0)
        window = MainWindow(store=self.store)
        self.assertEqual(window.chats[0][0]["status"], "failed")
        self.assertIn("未完成", window.chats[0][0]["error"])
        self.assertFalse(window.client.busy)
        self.assertEqual(window.question.text(), "等待回答的问题")
        window.save_timer.stop()
        window.deleteLater()

    def test_variables_complete_without_affecting_first_lesson(self):
        window = MainWindow(store=self.store)
        window.lesson_list.setCurrentRow(1)
        window.editor.setPlainText(VARIABLE_CODE)
        window.check_code()
        self.assertEqual(window.progress[1]["status"], "练习通过，待确认理解")
        self.assertTrue(window.quiz_button.isEnabled())
        first_status = window.progress[0]["status"]
        def answer():
            dialog = APP.activeModalWidget()
            self.assertEqual(dialog.lesson_id, "variables")
            dialog.output.setPlainText("狗\nanimal")
            dialog.reason.setCurrentText("变量读取新的值；引号里是固定文字")
            dialog.check()
        QTimer.singleShot(0, answer)
        window.check_understanding()
        self.assertEqual(window.progress[1]["status"], "独立完成")
        self.assertEqual(window.progress[0]["status"], first_status)
        self.assertIn("变量", window.progress[1]["evidence"])
        window.persist_changes()
        restored = MainWindow(store=StudyStore(self.path))
        self.assertEqual(restored.current_lesson, 1)
        self.assertEqual(restored.editor.toPlainText(), VARIABLE_CODE)
        self.assertEqual(restored.progress[1]["status"], "独立完成")
        restored.editor.setPlainText(VARIABLE_CODE.replace('Python', 'Java'))
        self.assertFalse(restored.quiz_button.isEnabled())
        for item in (window, restored):
            item.save_timer.stop()
            item.deleteLater()

    def test_variables_hint_and_code_help(self):
        window = MainWindow(store=self.store)
        window.lesson_list.setCurrentRow(1)
        for _ in range(3):
            window.show_hint()
        self.assertIn('language =', window.chats[1][-1]['reply'])
        window.editor.setPlainText(VARIABLE_CODE)
        window.check_code()
        def answer():
            dialog = APP.activeModalWidget()
            dialog.output.setPlainText("狗\nanimal")
            dialog.reason.setCurrentText("变量读取新的值；引号里是固定文字")
            dialog.check()
        QTimer.singleShot(0, answer)
        window.check_understanding()
        self.assertEqual(window.progress[1]["status"], "提示下完成")
        window.show_help()
        with patch.object(window, 'request_reply') as request:
            window.check_code()
            request.assert_called_once()
        window.save_timer.stop()
        window.deleteLater()

    def test_remaining_lessons_complete_and_restore_independently(self):
        window = MainWindow(store=self.store)
        cases = (
            (2, 'types', TYPES_CODE, '6\n42', '数字相加，字符串拼接'),
            (3, 'conditions', CONDITIONS_CODE, '可以报名', '>= 包含等于，条件成立'),
            (4, 'loops', LOOPS_CODE, '0\n1\n2\n结束', 'i 是 0、1、2，循环外的结束显示一次'),
        )
        for index, lesson_id, code, output, reason in cases:
            with self.subTest(lesson_id=lesson_id):
                window.lesson_list.setCurrentRow(index)
                # 条件判断使用提示，其余两课独立完成。
                if index == 3:
                    for _ in range(3):
                        window.show_hint()
                window.editor.setPlainText(code)
                window.check_code()
                self.assertTrue(window.quiz_button.isEnabled())
                self.assertEqual(window.progress[index]['status'], '练习通过，待确认理解')
                def answer(output=output, reason=reason):
                    dialog = APP.activeModalWidget()
                    dialog.output.setPlainText(output)
                    dialog.reason.setCurrentText(reason)
                    dialog.check()
                QTimer.singleShot(0, answer)
                window.check_understanding()
                self.assertEqual(window.progress[index]['status'], '提示下完成' if index == 3 else '独立完成')
                window.show_help()
                with patch.object(window, 'request_reply') as request:
                    window.check_code()
                    request.assert_called_once()
                window.show_help()
        self.assertEqual(window.next_button.text(), '回顾学习记录')
        with patch.object(window, 'show_records') as records:
            window.next_lesson()
            records.assert_called_once()
        window.persist_changes()
        restored = MainWindow(store=StudyStore(self.path))
        self.assertEqual(restored.current_lesson, 4)
        for index, _, code, _, _ in cases:
            self.assertEqual(restored.drafts[index], code)
            self.assertEqual(restored.progress[index]['status'], '提示下完成' if index == 3 else '独立完成')
        self.assertEqual(restored.progress[1]['status'], '尚未开始')
        for item in (window, restored):
            item.save_timer.stop()
            item.deleteLater()


if __name__ == "__main__":
    unittest.main()
