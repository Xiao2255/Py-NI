import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from services.learning import new_progress
from services.review import recommend, REVIEW_QUESTIONS
from services.study_store import StudyStore
from ui.lessons import LESSONS
from ui.review_dialog import ReviewDialog
from ui.main_window import MainWindow

APP = QApplication.instance() or QApplication([])


class ReviewTests(unittest.TestCase):
    def test_priority_and_completion_are_based_on_records(self):
        progress = {i: new_progress() for i in range(len(LESSONS))}
        self.assertEqual(recommend(progress)[:2], (0, 'study'))
        progress[2]['status'] = '练习通过，待确认理解'
        self.assertEqual(recommend(progress)[:2], (2, 'study'))
        progress[3]['status'] = '需要复习'
        self.assertEqual(recommend(progress)[:2], (3, 'review'))
        for record in progress.values():
            record['status'] = '独立完成'
        self.assertEqual(recommend(progress)[:2], (0, 'review'))
        progress[0]['review'] = {'result': '独立答对', 'attempts': 1, 'updated': '2026-10-14'}
        self.assertEqual(recommend(progress)[:2], (1, 'review'))
        progress[4]['review'] = {'result': '需要再练', 'attempts': 1, 'updated': '2026-10-14'}
        self.assertEqual(recommend(progress)[:2], (4, 'review'))

    def test_existing_learner_is_offered_first_new_lesson(self):
        completed = {'print', 'variables', 'types', 'conditions', 'loops'}
        progress = {i: new_progress() for i in range(len(LESSONS))}
        for index, lesson in enumerate(LESSONS):
            if lesson['id'] in completed:
                progress[index]['status'] = '独立完成'
        index, action, _ = recommend(progress)
        self.assertEqual((LESSONS[index]['id'], action), ('lists', 'study'))

    def test_blank_does_not_count_and_every_lesson_has_a_working_review(self):
        self.assertEqual(set(REVIEW_QUESTIONS), {lesson['id'] for lesson in LESSONS})
        for lesson_id, question in REVIEW_QUESTIONS.items():
            with self.subTest(lesson=lesson_id):
                dialog = ReviewDialog(lesson_id)
                dialog.check()
                self.assertEqual(dialog.attempts, 0)
                dialog.output.setPlainText(question[1])
                dialog.reason.setCurrentText(question[4])
                dialog.check()
                self.assertTrue(dialog.passed)
                self.assertEqual(dialog.attempts, 1)
                dialog.check()
                self.assertEqual(dialog.attempts, 1)
                dialog.deleteLater()

    def test_review_retains_course_draft_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'study.sqlite3'
            window = MainWindow(store=StudyStore(path))
            window.editor.setPlainText('print("保留草稿")')
            window.progress[0]['status'] = '提示下完成'
            window.question.setText('保留问题')
            def answer():
                dialog = APP.activeModalWidget()
                dialog.reason.setCurrentIndex(1)
                dialog.output.setPlainText('错误')
                dialog.check()
                dialog.output.setPlainText(REVIEW_QUESTIONS['print'][1])
                dialog.check()
                dialog.reject()
            QTimer.singleShot(0, answer)
            window.show_review()
            self.assertEqual(window.progress[0]['status'], '提示下完成')
            self.assertEqual(window.progress[0]['review']['result'], '提示后答对')
            self.assertEqual(window.editor.toPlainText(), 'print("保留草稿")')
            self.assertEqual(window.question.text(), '保留问题')
            restored = MainWindow(store=StudyStore(path))
            self.assertEqual(restored.progress[0]['review'], window.progress[0]['review'])
            for item in (window, restored):
                item.save_timer.stop()
                item.deleteLater()

    def test_close_without_answer_does_not_create_review_record(self):
        window = MainWindow(store=False)
        QTimer.singleShot(0, lambda: APP.activeModalWidget().reject())
        window.show_review()
        self.assertNotIn('review', window.progress[0])
        window.save_timer.stop()
        window.deleteLater()

    def test_backup_accepts_old_records_but_rejects_invalid_review(self):
        row = {'draft': '', 'question': '', 'progress': new_progress(), 'chats': []}
        StudyStore.validate(row)
        row['progress']['review'] = {'result': '独立答对', 'attempts': True, 'updated': ''}
        with self.assertRaises(ValueError):
            StudyStore.validate(row)
