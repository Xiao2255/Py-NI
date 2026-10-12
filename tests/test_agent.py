import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from test_model_connection import APP, wait_until
from PySide6.QtNetwork import QNetworkProxy
from config import ModelConfig
from services.agent import AgentClient
from services.study_store import StudyStore, StudyConflictError
from services.learning import new_progress
from tools.project_tools import ProjectTools, STUDY_TOOLS


class AgentHandler(BaseHTTPRequestHandler):
    records = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.records.append(request)
        after_tool = request['messages'][-1]['role'] == 'tool'
        message = {'content': '检查完成，接下来试试小测。'}
        if not after_tool or request['model'] == 'loop':
            args = 'invalid' if request['model'] == 'malformed' else '{}'
            message = {'content': None, 'reasoning_content': 'retained protocol state', 'tool_calls': [
                {'id': 'call-1', 'type': 'function', 'function': {'name': 'get_learning_progress', 'arguments': args}}]}
        body = json.dumps({'choices': [{'message': message, 'finish_reason': 'stop'}]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), AgentHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, model='ok', cancel_after_tool=False):
        client = AgentClient()
        client.manager.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        results, errors, executed = [], [], []
        client.completed.connect(results.append)
        client.failed.connect(errors.append)
        if cancel_after_tool:
            client.activity.connect(lambda _: client.cancel())
        config = ModelConfig('自定义服务', f'http://127.0.0.1:{self.server.server_port}/v1', model, '')
        def execute(name, args):
            executed.append((name, args))
            return {'status': '正在练习'}
        client.send(config, [{'role': 'user', 'content': '查看学习进度'}], tools=STUDY_TOOLS, execute=execute)
        wait_until(lambda: results or errors)
        APP.processEvents()
        self.assertFalse(client.busy)
        return results, errors, executed

    def test_tool_roundtrip_preserves_ids_and_reasoning(self):
        results, errors, executed = self.request()
        self.assertFalse(errors)
        self.assertEqual(len(executed), 1)
        self.assertIn('小测', results[0]['content'])
        request = AgentHandler.records[-1]
        self.assertFalse(request['stream'])
        self.assertEqual(request['messages'][-1]['tool_call_id'], 'call-1')
        self.assertEqual(request['messages'][-2]['reasoning_content'], 'retained protocol state')

    def test_loop_limit_and_malformed_args(self):
        results, errors, executed = self.request('loop')
        self.assertFalse(results)
        self.assertEqual(len(executed), 4)
        self.assertIn('上限', errors[0])
        results, errors, executed = self.request('malformed')
        self.assertFalse(executed)
        self.assertIn('参数', errors[0])

    def test_cancel_between_tool_and_next_request(self):
        before = len(AgentHandler.records)
        results, errors, executed = self.request(cancel_after_tool=True)
        self.assertFalse(results)
        self.assertIn('取消', errors[0])
        self.assertEqual(len(AgentHandler.records) - before, 1)


class ProjectBoundaryTests(unittest.TestCase):
    def test_read_requires_authorization_and_rejects_escape_private_binary_large(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'project'
            root.mkdir()
            (root / 'lesson.py').write_text('print("你好")', encoding='utf-8')
            (root / '.env').write_text('private')
            (root / 'api_key.txt').write_text('private')
            (root / 'large.py').write_text('a' * 32001)
            (root / 'binary.py').write_bytes(b'\x00binary')
            (Path(temp) / 'outside.py').write_text('private')
            tools = ProjectTools()
            with self.assertRaises(ValueError):
                tools.read_file('lesson.py')
            tools.select(root)
            self.assertIn('你好', tools.read_file('lesson.py')['content'])
            listing = tools.list_files()['files']
            self.assertIn('lesson.py', listing)
            self.assertNotIn('.env', listing)
            self.assertNotIn('api_key.txt', listing)
            for path in ('../outside.py', str(Path(temp) / 'outside.py'), '.env', 'api_key.txt', 'large.py', 'binary.py', 'lesson.py:stream'):
                with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                    tools.read_file(path)
            tools.revoke()
            with self.assertRaises(ValueError):
                tools.list_files()

    def test_listing_is_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            for i in range(120):
                (Path(temp) / f'{i}.py').touch()
            tools = ProjectTools()
            tools.select(temp)
            result = tools.list_files()
            self.assertEqual(len(result['files']), 100)
            self.assertTrue(result['truncated'])


class BackupTests(unittest.TestCase):
    def test_restore_is_validated_and_atomic_on_conflict(self):
        with tempfile.TemporaryDirectory() as temp:
            store = StudyStore(Path(temp) / 'study.sqlite3')
            row = {'draft': 'original', 'question': '', 'progress': new_progress(), 'chats': []}
            store.save('print', row, 0)
            store.save('variables', row, 0)
            changed = dict(row, draft='restored')
            backup = {'format': 'pyni-study', 'version': 1, 'current': 'variables',
                      'lessons': {'print': changed, 'variables': changed}}
            with self.assertRaises(StudyConflictError):
                store.restore(backup, {'print': 1, 'variables': 0})
            loaded, current = store.load(['print', 'variables'])
            self.assertEqual(loaded['print'][0]['draft'], 'original')
            store.restore(backup, {'print': 1, 'variables': 1})
            loaded, current = store.load(['print', 'variables'])
            self.assertEqual(loaded['print'][0]['draft'], 'restored')
            self.assertEqual(current, 'variables')
            backup['lessons']['print']['chats'] = [{'reply': 'x', 'local': True, 'tools': [None]}]
            with self.assertRaises(ValueError):
                store.restore(backup, {'print': 2, 'variables': 2})
