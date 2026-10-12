# 第三方组件

本软件使用 Python、PySide6 / Qt、Shiboken6，并用 PyInstaller 构建 Windows 便携包。依赖的版权和许可仍归各自作者所有。便携版的 `_internal/licenses` 收录许可证，`BUILD-INFO.json` 记录实际构建版本。

| 组件 | 许可与来源 |
| --- | --- |
| CPython | Python Software Foundation License；https://www.python.org/psf/license/ |
| PySide6 / Shiboken6 | LGPL-3.0 / GPL 可选许可，详见 https://doc.qt.io/qtforpython-6/licenses.html 与 https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Qt Core / Gui / Widgets / Network 及运行时插件 | Qt 开源许可及各第三方组件许可；https://doc.qt.io/qt-6/licensing.html 与 https://doc.qt.io/qt-6/licenses-used-in-qt.html |
| PyInstaller bootloader | GPL-2.0-or-later，带分发例外；https://pyinstaller.org/en/stable/license.html |

Qt 和 PySide6 动态库位于 `_internal` 中，未做修改。此分发不限制为修改这些库、调试修改或替换兼容动态库所需的操作。可用源码和构建说明：

`licenses/Qt-6.12.0/` 保留 QtBase 官方对应版本的许可和第三方版权声明；其中部分文件描述本应用没有使用的组件。构建仅保留 Widgets 所需动态库，移除了 PDF、QML、虚拟键盘和图像格式扩展；PNG 由 QtGui 内置支持。HTTPS 使用 Windows Schannel 后端。

- PySide / Shiboken：<https://code.qt.io/cgit/pyside/pyside-setup.git/>（选择 BUILD-INFO.json 对应版本标签）。
- Qt：<https://download.qt.io/official_releases/qt/>（选择对应版本的 `single` 或 `submodules` 源码包）。
- PyNi 构建：参见源码中的 `scripts/build_release.py` 和 `PyNi.spec`；保持 `_internal` 与 EXE 同级。

动漫伙伴为本项目通过图像生成工具制作的资源，生成说明见 `docs/visual-assets.md`。项目本身尚未选择开源许可证；发布仓库前由作者决定授权方式，第三方许可不因此改变。
