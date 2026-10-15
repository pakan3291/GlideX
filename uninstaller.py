"""
GlideX - Professional Windows Uninstaller
========================================
Sleek dark-themed GUI uninstaller removing GlideX cleanly from Windows 11.
Safely restores system hardware cursors, kills processes, removes shortcuts,
unregisters from Windows Settings, and deletes all files.
"""

import os
import sys
import time
import shutil
import ctypes
import winreg
import subprocess
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QStackedWidget,
    QFrame
)

UNINSTALLER_STYLE = """
QMainWindow, QWidget {
    background-color: #0F0F12;
    color: #F8FAFC;
    font-family: 'Segoe UI', -apple-system, sans-serif;
}
QFrame#Card {
    background-color: #16161D;
    border: 1px solid #282833;
    border-radius: 12px;
}
QLabel#Title {
    font-size: 20px;
    font-weight: 700;
    color: #FFFFFF;
}
QLabel#Subtitle {
    font-size: 13px;
    color: #94A3B8;
}
QLabel#PathLabel {
    font-size: 11px;
    color: #64748B;
    background-color: #0A0A0D;
    border: 1px solid #22222E;
    border-radius: 6px;
    padding: 6px 10px;
}
QProgressBar {
    background-color: #1E1E28;
    border: 1px solid #2D2D3D;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #6366F1);
    border-radius: 5px;
}
QPushButton {
    font-size: 13px;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 20px;
}
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EF4444, stop:1 #DC2626);
    color: #FFFFFF;
    border: none;
}
QPushButton#PrimaryBtn:hover {
    background: #DC2626;
}
QPushButton#FinishBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #6366F1);
    color: #FFFFFF;
    border: none;
}
QPushButton#FinishBtn:hover {
    background: #6366F1;
}
QPushButton#SecondaryBtn {
    background-color: #22222D;
    color: #E2E8F0;
    border: 1px solid #333344;
}
QPushButton#SecondaryBtn:hover {
    background-color: #2C2C3A;
    border-color: #4B5563;
}
"""


def restore_windows_cursors():
    """Failsafe restoration of native Windows hardware cursor."""
    try:
        mag = getattr(ctypes.windll, "magnification", None)
        if mag:
            mag.MagInitialize()
            mag.MagShowSystemCursor(True)
            mag.MagUninitialize()
    except Exception:
        pass
    try:
        # SPI_SETCURSORS = 0x0057
        ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)
    except Exception:
        pass


def kill_glidex_processes():
    """Restores cursor and terminates any running GlideX processes."""
    restore_windows_cursors()
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "GlideX.exe"],
            capture_output=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    except Exception:
        pass


class UninstallWorker(QThread):
    progress_changed = Signal(int, str)
    finished_signal = Signal(bool, str)

    def __init__(self, install_dir: str):
        super().__init__()
        self.install_dir = os.path.abspath(install_dir)

    def run(self):
        try:
            self.progress_changed.emit(10, "Restoring Windows native cursors...")
            restore_windows_cursors()
            time.sleep(0.3)

            self.progress_changed.emit(25, "Closing running GlideX instances...")
            kill_glidex_processes()
            time.sleep(0.5)

            self.progress_changed.emit(45, "Removing Desktop shortcut...")
            # 1. Remove Desktop shortcut
            desktop_dirs = [
                os.path.join(os.path.expanduser("~"), "Desktop"),
                os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            ]
            for d in set(desktop_dirs):
                shortcut = os.path.join(d, "GlideX.lnk")
                if os.path.exists(shortcut):
                    try:
                        os.remove(shortcut)
                    except Exception:
                        pass

            self.progress_changed.emit(60, "Removing Start Menu folder & shortcuts...")
            # 2. Remove Start Menu folder
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                start_menu_folder = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\GlideX")
                if os.path.exists(start_menu_folder):
                    try:
                        shutil.rmtree(start_menu_folder, ignore_errors=True)
                    except Exception:
                        pass

            self.progress_changed.emit(75, "Cleaning Windows startup registry...")
            # 3. Remove Windows Startup key
            try:
                run_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_ALL_ACCESS
                )
                try:
                    winreg.DeleteValue(run_key, "GlideX")
                except FileNotFoundError:
                    pass
                winreg.CloseKey(run_key)
            except Exception:
                pass

            self.progress_changed.emit(85, "Removing Windows Installed Apps registration...")
            # 4. Remove Uninstall registry key
            try:
                winreg.DeleteKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Uninstall\GlideX"
                )
            except FileNotFoundError:
                pass
            except Exception:
                pass

            self.progress_changed.emit(95, "Deleting installed files and directories...")
            # 5. Remove all files in install_dir except uninstaller.exe
            current_exe = os.path.abspath(sys.argv[0]).lower()
            if os.path.exists(self.install_dir):
                for item in os.listdir(self.install_dir):
                    item_path = os.path.join(self.install_dir, item)
                    if os.path.abspath(item_path).lower() == current_exe:
                        continue
                    try:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path, ignore_errors=True)
                        else:
                            os.remove(item_path)
                    except Exception:
                        pass

            self.progress_changed.emit(100, "Uninstallation completed successfully.")
            self.finished_signal.emit(True, "GlideX has been cleanly removed.")

        except Exception as e:
            self.finished_signal.emit(False, str(e))


class UninstallerWindow(QMainWindow):
    def __init__(self, install_dir: str):
        super().__init__()
        self.install_dir = os.path.abspath(install_dir)
        self.setWindowTitle("GlideX - Uninstaller")
        self.resize(520, 360)
        self.setFixedSize(520, 360)
        self.setStyleSheet(UNINSTALLER_STYLE)

        self._setup_icon()
        self._init_ui()

    def _setup_icon(self):
        # Locate GlideX.ico
        candidates = [
            os.path.join(self.install_dir, "assets", "GlideX.ico"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "GlideX.ico"),
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "assets", "GlideX.ico")
        ]
        for p in candidates:
            if os.path.exists(p):
                self.setWindowIcon(QIcon(p))
                self.icon_path = p
                return
        self.icon_path = ""

    def _init_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Page 0: Confirmation Page
        self.page_confirm = self._create_confirm_page()
        self.stack.addWidget(self.page_confirm)

        # Page 1: Progress Page
        self.page_progress = self._create_progress_page()
        self.stack.addWidget(self.page_progress)

        # Page 2: Finished Page
        self.page_finish = self._create_finish_page()
        self.stack.addWidget(self.page_finish)

    def _create_confirm_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)

        # Header with warning badge
        lbl_title = QLabel("Uninstall GlideX")
        lbl_title.setObjectName("Title")
        card_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Are you sure you want to completely remove GlideX and all its components\n"
            "from your computer?"
        )
        lbl_desc.setObjectName("Subtitle")
        card_layout.addWidget(lbl_desc)

        lbl_loc = QLabel(f"Installation directory:\n{self.install_dir}")
        lbl_loc.setObjectName("PathLabel")
        card_layout.addWidget(lbl_loc)

        layout.addWidget(card)
        layout.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("SecondaryBtn")
        self.btn_cancel.clicked.connect(self.close)
        btn_row.addWidget(self.btn_cancel)

        self.btn_uninstall = QPushButton("Uninstall")
        self.btn_uninstall.setObjectName("PrimaryBtn")
        self.btn_uninstall.clicked.connect(self._start_uninstall)
        btn_row.addWidget(self.btn_uninstall)

        layout.addLayout(btn_row)
        return w

    def _create_progress_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 24, 20, 24)
        card_layout.setSpacing(16)

        lbl_title = QLabel("Uninstalling GlideX...")
        lbl_title.setObjectName("Title")
        card_layout.addWidget(lbl_title)

        self.status_label = QLabel("Preparing to uninstall...")
        self.status_label.setObjectName("Subtitle")
        card_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar)

        layout.addWidget(card)
        layout.addStretch()
        return w

    def _create_finish_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 24, 20, 24)
        card_layout.setSpacing(14)

        lbl_title = QLabel("GlideX Successfully Uninstalled")
        lbl_title.setObjectName("Title")
        card_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "GlideX has been completely removed from your computer.\n"
            "Hardware cursor control has been returned to Windows default."
        )
        lbl_desc.setObjectName("Subtitle")
        card_layout.addWidget(lbl_desc)

        layout.addWidget(card)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setObjectName("FinishBtn")
        btn_close.clicked.connect(self._on_close_clicked)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)
        return w

    def _start_uninstall(self):
        self.stack.setCurrentIndex(1)
        self.worker = UninstallWorker(self.install_dir)
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.status_label.setText(msg)

    def _on_finished(self, success: bool, msg: str):
        self.stack.setCurrentIndex(2)

    def _on_close_clicked(self):
        # Self-deletion of uninstaller and containing folder
        cmd = f'ping 127.0.0.1 -n 2 > nul & rmdir /s /q "{self.install_dir}"'
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", cmd],
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        except Exception:
            pass
        self.close()
        sys.exit(0)


def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GlideX.CursorPhysics.Uninstaller.v1")
    except Exception:
        pass

    app = QApplication.instance() or QApplication(sys.argv)
    
    # Determine install directory
    install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # Check if installed directory was passed as argument
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        install_dir = os.path.abspath(sys.argv[1])

    win = UninstallerWindow(install_dir)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
