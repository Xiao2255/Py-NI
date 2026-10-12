"""在 Windows 项目虚拟环境内构建，可重复执行；只打包明确列出的源码。"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'
SOURCE_FILES = ['main.py', 'config.py', 'README.md', 'requirements.txt', 'requirements-dev.txt',
                'start.bat', 'PyNi.spec', '.gitignore', 'CHANGELOG.md']
SOURCE_DIRS = ['ui', 'services', 'tools', 'tests', 'scripts', 'prompts', 'assets', 'docs', '.github', 'licenses']


def source_files():
    result = [ROOT / name for name in SOURCE_FILES]
    for directory in SOURCE_DIRS:
        for file in (ROOT / directory).rglob('*'):
            if file.is_file() and not file.is_symlink() and '__pycache__' not in file.parts and file.suffix not in {'.pyc', '.sqlite3', '.db'}:
                result.append(file)
    return sorted(result)


def main():
    if sys.platform != 'win32':
        raise SystemExit('请在 Windows 上构建 Windows 发行包。')
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, check=True)
    # 不从开发工具注入的 PATH 收集同名 ICU/OpenSSL/UCRT DLL。
    # Qt 的 DLL 由 PyInstaller hooks 从已安装的 wheel 定位。
    build_env = os.environ.copy()
    build_env.pop('PYNI_DEBUG_BUILD', None)
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    build_env['PATH'] = os.pathsep.join(map(str, [Path(sys.executable).parent, Path(sys.base_prefix), windows / 'System32', windows]))
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', 'PyNi.spec'], cwd=ROOT, env=build_env, check=True)
    folder = ROOT / 'dist/PyNi'
    subprocess.run([str(folder / 'PyNi.exe'), '--smoke-test'], cwd=ROOT, check=True, timeout=30)
    info = {'version': VERSION, 'python': sys.version.split()[0],
            'packages': {name: importlib.metadata.version(name) for name in ['PySide6', 'shiboken6', 'PyInstaller']}}
    (folder / 'BUILD-INFO.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    shutil.copy2(ROOT / 'docs/QUICKSTART.md', folder / '使用说明.md')
    shutil.copy2(ROOT / 'docs/THIRD_PARTY.md', folder / 'THIRD_PARTY.md')
    release = ROOT / 'release'
    release.mkdir(exist_ok=True)
    binary = release / f'PyNi-{VERSION}-windows-x64.zip'
    with zipfile.ZipFile(binary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(folder.rglob('*')):
            if file.is_file():
                archive.write(file, file.relative_to(folder.parent))
    # 从解压副本启动，工作目录不在项目中，并移除 Python/开发工具 PATH。
    with tempfile.TemporaryDirectory(prefix='pyni-portable-') as temporary:
        with zipfile.ZipFile(binary) as archive:
            if archive.testzip() is not None:
                raise RuntimeError('便携包完整性检查失败。')
            archive.extractall(temporary)
        portable_env = os.environ.copy()
        portable_env['PATH'] = str(windows / 'System32')
        portable_env.pop('PYTHONPATH', None)
        portable_env.pop('PYTHONHOME', None)
        subprocess.run([str(Path(temporary) / 'PyNi/PyNi.exe'), '--smoke-test'],
                       cwd=temporary, env=portable_env, check=True, timeout=30)
    source = release / f'PyNi-{VERSION}-source.zip'
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in source_files():
            archive.write(file, Path(f'PyNi-{VERSION}') / file.relative_to(ROOT))
    lines = []
    for file in (binary, source):
        with file.open('rb') as stream:
            lines.append(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {file.name}')
    checksums = '\n'.join(lines) + '\n'
    (release / 'SHA256SUMS.txt').write_text(checksums, encoding='utf-8')
    print('Release ready:', binary, source, sep='\n')


if __name__ == '__main__':
    main()
