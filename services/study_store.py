"""本机学习记录：SQLite 事务保存，版本检查避免多个窗口覆盖彼此。"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from .learning import STATUSES


class StudyConflictError(OSError):
    pass


def study_path():
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "study.sqlite3"


class StudyStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else study_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("学习记录来自更新的版本，请使用对应版本打开。")
            db.execute("CREATE TABLE IF NOT EXISTS lessons (id TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL, updated TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("PRAGMA user_version=1")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        try:
            with db:
                yield db
        finally:
            db.close()

    def load(self, lesson_ids):
        result = {}
        with self.connect() as db:
            for key, raw, revision, updated in db.execute("SELECT id,payload,revision,updated FROM lessons"):
                if key not in lesson_ids:
                    continue
                data = json.loads(raw)
                self.validate(data)
                result[key] = (data, revision, updated)
            row = db.execute("SELECT value FROM settings WHERE name='current_lesson'").fetchone()
        return result, row[0] if row and row[0] in lesson_ids else lesson_ids[0]

    @staticmethod
    def validate(data):
        if not isinstance(data, dict) or not all(isinstance(data.get(key), str) for key in ("draft", "question")):
            raise ValueError("学习记录格式异常，原文件已保留。")
        progress = data.get("progress")
        if not isinstance(progress, dict) or progress.get("status") not in STATUSES:
            raise ValueError("学习进度格式异常，原文件已保留。")
        if type(progress.get("hints")) is not int or not 0 <= progress["hints"] <= 1000 or type(progress.get("assisted")) is not bool:
            raise ValueError("提示记录格式异常，原文件已保留。")
        if progress.get("checked_code") is not None and not isinstance(progress["checked_code"], str):
            raise ValueError("练习检查记录格式异常，原文件已保留。")
        if not all(isinstance(progress.get(key), str) for key in ("evidence", "source", "note")):
            raise ValueError("学习记录格式异常，原文件已保留。")
        if not isinstance(data.get("chats"), list):
            raise ValueError("对话记录格式异常，原文件已保留。")
        for turn in data["chats"]:
            if not isinstance(turn, dict) or not isinstance(turn.get("reply"), str):
                raise ValueError("对话内容格式异常，原文件已保留。")
            if "tools" in turn and (not isinstance(turn["tools"], list) or len(turn["tools"]) > 8 or not all(isinstance(item, str) and len(item) < 500 for item in turn["tools"])):
                raise ValueError("工具记录格式异常。")
            if turn.get("local"):
                if "label" in turn and not isinstance(turn["label"], str):
                    raise ValueError("对话标签格式异常，原文件已保留。")
                continue
            if not all(isinstance(turn.get(key), str) for key in ("question", "model")) or turn.get("status") not in ("success", "failed", "pending"):
                raise ValueError("对话内容格式异常，原文件已保留。")
            if not all(isinstance(turn[key], str) for key in ("display_question", "code", "error") if key in turn):
                raise ValueError("对话内容格式异常，原文件已保留。")

    @classmethod
    def validate_backup(cls, data, lesson_ids):
        if not isinstance(data, dict) or data.get("format") != "pyni-study" or data.get("version") != 1:
            raise ValueError("未知备份格式。")
        if not isinstance(data.get("lessons"), dict) or set(data["lessons"]) != set(lesson_ids) or data.get("current") not in lesson_ids:
            raise ValueError("备份课程不匹配。")
        for row in data["lessons"].values():
            cls.validate(row)

    def restore(self, data, revisions):
        self.validate_backup(data, list(revisions))
        updated = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for key, revision in revisions.items():
                row = db.execute("SELECT revision FROM lessons WHERE id=?", (key,)).fetchone()
                if (row[0] if row else 0) != revision:
                    raise StudyConflictError("其他窗口已更新记录，恢复已取消。")
            for key, payload in data["lessons"].items():
                db.execute("INSERT INTO lessons VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision,updated=excluded.updated",
                           (key, json.dumps(payload, ensure_ascii=False), revisions[key] + 1, updated))
            db.execute("INSERT INTO settings VALUES ('current_lesson',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (data["current"],))

    def save(self, lesson_id, data, revision, current=True):
        self.validate(data)
        updated = datetime.now(timezone.utc).isoformat(timespec="seconds")
        raw = json.dumps(data, ensure_ascii=False)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT revision FROM lessons WHERE id=?", (lesson_id,)).fetchone()
            if (row[0] if row else 0) != revision:
                raise StudyConflictError("另一个窗口已更新这节课。请保留当前代码，重新打开后继续，以免覆盖新记录。")
            db.execute("INSERT INTO lessons VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision,updated=excluded.updated", (lesson_id, raw, revision + 1, updated))
            if current:
                db.execute("INSERT INTO settings VALUES ('current_lesson',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (lesson_id,))
        return revision + 1, updated
