"""应用入口：创建应用、显示窗口、开始处理点击等事件。"""
import sys
from pathlib import Path
from services.startup_trace import trace
trace('importing Qt')
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QLockFile, QEvent
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
from ui.welcome import WelcomeDialog
from config import settings_path
trace('imports complete')


def main():
    trace('creating QApplication')
    app = QApplication(sys.argv)
    trace('QApplication created')
    app.setOrganizationName("PyNi")
    app.setApplicationName("PyNi")
    app.setApplicationVersion("0.1.0")
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets/companion.png")))
    smoke = "--smoke-test" in sys.argv
    lock = None
    if not smoke:
        try:
            location = settings_path().parent
            location.mkdir(parents=True, exist_ok=True)
            lock = QLockFile(str(location / "application.lock"))
            lock.setStaleLockTime(0)
            if not lock.tryLock(0):
                QMessageBox.information(None, "Py妮", "Py妮已经打开，或学习目录暂不可写。请先查看已打开的窗口。")
                return 1
        except OSError:
            QMessageBox.warning(None, "Py妮", "无法创建本机学习目录，请检查目录权限。")
            return 1
    trace('creating MainWindow')
    window = MainWindow(store=False if smoke else None)
    trace('MainWindow created')
    window.show()
    trace('MainWindow shown')
    def welcome():
        dialog = WelcomeDialog(window)
        dialog.exec()
        if dialog.choice == "settings":
            window.show_settings()
        elif dialog.choice == "help":
            window.show_help()
        dialog.deleteLater()
    if smoke:
        # 分发包自检：加载窗口、课程、图片、样式，不调用 API 或写用户记录。
        from PySide6.QtGui import QPixmap
        from PySide6.QtNetwork import QSslSocket
        valid = not QPixmap(str(Path(__file__).resolve().parent / "assets/companion.png")).isNull()
        valid &= bool((Path(__file__).resolve().parent / "prompts/system_prompt.txt").read_text(encoding="utf-8"))
        trace('checking SSL')
        valid &= QSslSocket.supportsSsl()
        trace('SSL checked')
        QTimer.singleShot(500, lambda: app.exit(0 if valid else 2))
    else:
        QTimer.singleShot(0, welcome)
    trace('entering event loop')
    result = app.exec()
    trace('event loop ended')
    # 在 QApplication 和 Python 解释器销毁之前清理所有窗口子对象。
    # 否则窗口中的 QTextDocument/高亮器可能在 Qt 已退出后才被回收。
    window.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    trace('window cleanup complete')
    return result


if __name__ == "__main__":
    sys.exit(main())
