"""隔离打包程序的 DLL 搜索路径，不修改系统环境。"""
import os
from pathlib import Path
import sys

if sys.platform == 'win32' and getattr(sys, 'frozen', False):
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    os.environ['PATH'] = os.pathsep.join(map(str, [windows / 'System32', windows]))
    # GUI 程序没有控制台，给依赖库提供可写的 Python 标准流。
    for name in ('stdout', 'stderr'):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, 'w'))
