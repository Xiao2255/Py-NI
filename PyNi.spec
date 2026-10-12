# Windows onedir：保留可替换的 Qt 动态库，避免启动时反复解压。
from pathlib import Path
import os
root = Path(SPECPATH)
a = Analysis([str(root / 'main.py')], pathex=[str(root)],
             datas=[(str(root / 'assets/companion.png'), 'assets'),
                    (str(root / 'ui/style.qss'), 'ui'),
                    (str(root / 'prompts/system_prompt.txt'), 'prompts'),
                    (str(root / 'docs/THIRD_PARTY.md'), 'licenses'),
                    (str(root / 'licenses'), 'licenses')],
             runtime_hooks=[str(root / 'scripts/frozen_runtime.py')],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                       'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf', 'tkinter'],
             noarchive=False)
# 本应用只用 Widgets 和 PNG；不分发未使用的 PDF/QML/虚拟键盘组件。
unused = ('qt6qml', 'qt6quick', 'qt6pdf', 'qt6virtualkeyboard', 'qt6opengl', 'qt6svg')
def required_binary(entry):
    path = entry[0].replace('\\', '/').lower()
    name = path.rsplit('/', 1)[-1]
    return (not name.startswith(unused)
            and '/plugins/imageformats/' not in path
            and '/plugins/platforminputcontexts/' not in path
            and name not in {'qopensslbackend.dll', 'opengl32sw.dll'})
a.binaries = [entry for entry in a.binaries if required_binary(entry)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PyNi',
          console=bool(os.environ.get('PYNI_DEBUG_BUILD')), debug=False, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PyNi')
