import unittest

from services.learning import CHECKPOINTS, check_understanding
from ui.lessons import LESSONS


class NewLessonTests(unittest.TestCase):
    lessons = {lesson["id"]: lesson for lesson in LESSONS}

    def answer(self, lesson_id):
        # The last hint gives learners a complete answer they can copy into the editor.
        hint = CHECKPOINTS[lesson_id]["hints"][-1]
        return hint.split("```python\n", 1)[1].split("\n```", 1)[0]

    def test_starter_needs_edit_and_last_hint_solves_each_exercise(self):
        for lesson_id in ("lists", "dictionaries", "functions"):
            with self.subTest(lesson=lesson_id):
                checker = CHECKPOINTS[lesson_id]["checker"]
                self.assertFalse(checker(self.lessons[lesson_id]["code"])[0])
                answer = self.answer(lesson_id).replace('"', "'")
                self.assertTrue(checker("# 我的练习\n" + answer)[0])
                self.assertFalse(checker(answer + '\nprint("重复")')[0])
                self.assertFalse(checker('\x00')[0])

    def test_common_misconceptions_get_feedback(self):
        changes = (
            ("lists", "tasks[1]", "tasks[2]", "第二项"),
            ("lists", 'tasks.append("复习")', 'tasks = tasks.append("复习")', "append"),
            ("lists", 'print(tasks[2])', 'print("复习")', "索引"),
            ("dictionaries", 'scores["小林"] = 5', 'scores["小林"] == 5', "赋"),
            ("dictionaries", 'scores["小雨"] = 2', 'scores = {"小雨": 2}', "字典"),
            ("dictionaries", 'print(scores["小林"])', 'print(scores[0])', "名字"),
            ("functions", "return score + 1", "print(score + 1)", "return"),
            ("functions", "return score + 1", "return 5", "score"),
            ("functions", "print(add_point(4))", "print(add_point)", "4"),
            ("functions", "print(add_point(9))", "print(10)", "调用"),
        )
        for lesson_id, old, new, feedback in changes:
            with self.subTest(lesson=lesson_id, edit=new):
                answer = self.answer(lesson_id)
                self.assertIn(old, answer)
                passed, message = CHECKPOINTS[lesson_id]["checker"](answer.replace(old, new))
                self.assertFalse(passed)
                self.assertIn(feedback, message)

    def test_quizzes_require_both_output_and_explanation(self):
        for lesson_id, output in (("lists", "森林\n海洋"), ("dictionaries", "2\n6"), ("functions", "120\n60")):
            with self.subTest(lesson=lesson_id):
                quiz = CHECKPOINTS[lesson_id]
                self.assertTrue(check_understanding(output, quiz["quiz_reason"], lesson_id))
                wrong_reason = next(option for option in quiz["quiz_options"] if option != quiz["quiz_reason"])
                self.assertFalse(check_understanding(output, wrong_reason, lesson_id))
                self.assertFalse(check_understanding(output.splitlines()[0], quiz["quiz_reason"], lesson_id))
