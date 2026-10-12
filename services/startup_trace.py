"""可选离线启动诊断，只在 --smoke-test 且显式指定路径时记录阶段。"""
import os
import sys


def trace(stage):
    destination = os.environ.get('PYNI_SMOKE_TRACE')
    if destination and '--smoke-test' in sys.argv:
        with open(destination, 'a', encoding='utf-8') as stream:
            stream.write(stage + '\n')
