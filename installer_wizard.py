"""
GlideX - Professional Windows Setup Wizard
==========================================
Sleek dark-themed GUI installer for GlideX with multi-page wizard layout:
Welcome -> Install Location -> Options -> Installing Progress -> Completed.
Preserves user settings & custom cursors on upgrades, registers in Windows Settings,
creates Desktop and Start Menu shortcuts, and handles startup configuration.
"""

import os
import sys
import json
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
    QLineEdit,
    QCheckBox,
    QProgressBar,
    QStackedWidget,
    QFrame,
    QFileDialog
)

INSTALLER_STYLE = """
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
QFrame#Banner {
    background-color: #151F33;
    border: 1px solid #1E3A8A;
    border-radius: 8px;
    padding: 8px 12px;
}
QLabel#Title {
    font-size: 20px;
    font-weight: 700;
    color: #FFFFFF;
}
QLabel#Subtitle {
    font-size: 13px;
    color: #94A3B8;
    line-height: 1.4;
}
QLabel#BannerText {
    font-size: 12px;
    color: #60A5FA;
    font-weight: 500;
}
QLabel#DiskSpace {
    font-size: 12px;
    color: #64748B;
}
QLineEdit {
    background-color: #0C0C0E;
    border: 1px solid #2A2A38;
    border-radius: 8px;
    padding: 9px 12px;
    color: #F1F5F9;
    font-size: 13px;
    selection-background-color: #6366F1;
}
QLineEdit:focus {
    border: 1px solid #6366F1;
}
QCheckBox {
    font-size: 13px;
    color: #E2E8F0;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #3B3B4F;
    border-radius: 5px;
    background-color: #181822;
}
QCheckBox::indicator:hover {
    border-color: #6366F1;
}
QCheckBox::indicator:checked {
    background-color: #6366F1;
    border-color: #818CF8;
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
    padding: 9px 22px;
}
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #6366F1);
    color: #FFFFFF;
    border: none;
}
QPushButton#PrimaryBtn:hover {
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
QPushButton#BrowseBtn {
    background-color: #22222D;
    color: #E2E8F0;
    border: 1px solid #333344;
    padding: 8px 16px;
}
QPushButton#BrowseBtn:hover {
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
    """Restores cursor and gracefully terminates any running GlideX processes."""
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


def create_windows_shortcut(target_exe: str, shortcut_path: str, icon_path: str = None, description: str = "GlideX - Real-Time Cursor Physics & Studio"):
    """Creates a Windows .lnk shortcut using WScript.Shell with PowerShell fallback."""
    os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_exe
        shortcut.WorkingDirectory = os.path.dirname(target_exe)
        shortcut.Description = description
        if icon_path and os.path.exists(icon_path):
            shortcut.IconLocation = f"{icon_path},0"
        shortcut.save()
        return True
    except Exception:
        pass

    # Fallback to PowerShell
    try:
        ps_script = f'$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut("{shortcut_path}"); $s.TargetPath = "{target_exe}"; $s.WorkingDirectory = "{os.path.dirname(target_exe)}"; $s.Description = "{description}"; '
        if icon_path and os.path.exists(icon_path):
            ps_script += f'$s.IconLocation = "{icon_path},0"; '
        ps_script += '$s.Save()'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=5)
        return os.path.exists(shortcut_path)
    except Exception:
        return False


def get_disk_free_gb(path: str) -> float:
    """Returns available free disk space on path drive in GB."""
    try:
        drive = os.path.splitdrive(os.path.abspath(path))[0]
        if not drive:
            drive = "C:"
        drive += "\\"
        total, used, free = shutil.disk_usage(drive)
        return free / (1024 ** 3)
    except Exception:
        return 0.0


def is_already_installed(target_dir: str) -> bool:
    """Checks if an existing installation is detected in directory or registry."""
    # Check directory
    if os.path.exists(os.path.join(target_dir, "GlideX.exe")):
        return True
    if os.path.exists(os.path.join(target_dir, "bin", "GlideX.exe")):
        return True
    # Check registry
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\GlideX",
            0,
            winreg.KEY_READ
        )
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def merge_settings(target_settings: str, default_settings: str):
    """Preserves existing user settings and non-destructively merges any new defaults."""
    if not os.path.exists(target_settings):
        if os.path.exists(default_settings):
            os.makedirs(os.path.dirname(target_settings), exist_ok=True)
            shutil.copy2(default_settings, target_settings)
        return

    try:
        with open(target_settings, "r", encoding="utf-8") as f:
            user_data = json.load(f)
    except Exception:
        user_data = {}

    try:
        with open(default_settings, "r", encoding="utf-8") as f:
            default_data = json.load(f)
    except Exception:
        default_data = {}

    merged = dict(default_data)
    merged.update(user_data)

    try:
        with open(target_settings, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
    except Exception:
        pass


class InstallWorker(QThread):
    progress_changed = Signal(int, str)
    finished_signal = Signal(bool, str)

    def __init__(self, payload_dir: str, target_dir: str, opts: dict):
        super().__init__()
        self.payload_dir = os.path.abspath(payload_dir)
        self.target_dir = os.path.abspath(target_dir)
        self.opts = opts

    def run(self):
        try:
            self.progress_changed.emit(5, "Checking running instances...")
            restore_windows_cursors()
            time.sleep(0.3)

            self.progress_changed.emit(15, "Safely restoring cursor & closing active processes...")
            kill_glidex_processes()
            time.sleep(0.5)

            os.makedirs(self.target_dir, exist_ok=True)
            bin_dir = os.path.join(self.target_dir, "bin")
            config_dir = os.path.join(self.target_dir, "config")
            assets_dir = os.path.join(self.target_dir, "assets")
            cursors_dir = os.path.join(assets_dir, "cursors")

            os.makedirs(bin_dir, exist_ok=True)
            os.makedirs(config_dir, exist_ok=True)
            os.makedirs(cursors_dir, exist_ok=True)

            # 1. Copy core bin directory
            self.progress_changed.emit(30, "Extracting application binaries...")
            payload_bin = os.path.join(self.payload_dir, "bin")
            if os.path.exists(payload_bin):
                for item in os.listdir(payload_bin):
                    s = os.path.join(payload_bin, item)
                    d = os.path.join(bin_dir, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d, ignore_errors=True)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)

            # 2. Copy root GlideX.exe and uninstaller.exe
            self.progress_changed.emit(50, "Setting up launchers and uninstaller...")
            for exe_name in ["GlideX.exe", "uninstaller.exe"]:
                src_exe = os.path.join(self.payload_dir, exe_name)
                if os.path.exists(src_exe):
                    shutil.copy2(src_exe, os.path.join(self.target_dir, exe_name))

            # 3. Copy/Merge settings.json
            self.progress_changed.emit(65, "Preserving user settings & presets...")
            target_settings = os.path.join(config_dir, "settings.json")
            payload_settings = os.path.join(self.payload_dir, "config", "settings.json")
            merge_settings(target_settings, payload_settings)

            # If user checked "start_with_windows", update setting in target_settings
            if self.opts.get("start_with_windows", False):
                try:
                    with open(target_settings, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    cfg["start_with_windows"] = True
                    with open(target_settings, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2)
                except Exception:
                    pass

            # 4. Copy custom cursors non-destructively
            self.progress_changed.emit(75, "Updating cursor assets...")
            payload_cursors = os.path.join(self.payload_dir, "assets", "cursors")
            if os.path.exists(payload_cursors):
                for item in os.listdir(payload_cursors):
                    s = os.path.join(payload_cursors, item)
                    d = os.path.join(cursors_dir, item)
                    if os.path.isfile(s) and not os.path.exists(d):
                        shutil.copy2(s, d)

            # Copy icons to assets
            payload_assets = os.path.join(self.payload_dir, "assets")
            if os.path.exists(payload_assets):
                for item in os.listdir(payload_assets):
                    s = os.path.join(payload_assets, item)
                    d = os.path.join(assets_dir, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)

            # 5. Create shortcuts
            self.progress_changed.emit(85, "Creating Windows shortcuts...")
            installed_exe = os.path.join(self.target_dir, "GlideX.exe")
            installed_ico = os.path.join(assets_dir, "GlideX.ico")
            uninstaller_exe = os.path.join(self.target_dir, "uninstaller.exe")

            if self.opts.get("desktop_shortcut", True):
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                create_windows_shortcut(
                    installed_exe,
                    os.path.join(desktop, "GlideX.lnk"),
                    installed_ico,
                    "GlideX - Real-Time Cursor Physics & Studio"
                )

            if self.opts.get("start_menu_shortcut", True):
                appdata = os.environ.get("APPDATA", "")
                if appdata:
                    start_menu_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\GlideX")
                    os.makedirs(start_menu_dir, exist_ok=True)
                    create_windows_shortcut(
                        installed_exe,
                        os.path.join(start_menu_dir, "GlideX.lnk"),
                        installed_ico,
                        "GlideX - Real-Time Cursor Physics & Studio"
                    )
                    create_windows_shortcut(
                        uninstaller_exe,
                        os.path.join(start_menu_dir, "Uninstall GlideX.lnk"),
                        installed_ico,
                        "Uninstall GlideX"
                    )

            # 6. Windows Startup Registry
            self.progress_changed.emit(90, "Configuring Windows startup preferences...")
            try:
                run_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_ALL_ACCESS
                )
                if self.opts.get("start_with_windows", False):
                    winreg.SetValueEx(run_key, "GlideX", 0, winreg.REG_SZ, f'"{installed_exe}"')
                else:
                    try:
                        winreg.DeleteValue(run_key, "GlideX")
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(run_key)
            except Exception:
                pass

            # 7. Register in Windows Installed Apps
            self.progress_changed.emit(95, "Registering in Windows Settings...")
            try:
                uninst_key = winreg.CreateKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Uninstall\GlideX"
                )
                winreg.SetValueEx(uninst_key, "DisplayName", 0, winreg.REG_SZ, "GlideX")
                winreg.SetValueEx(uninst_key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
                winreg.SetValueEx(uninst_key, "Publisher", 0, winreg.REG_SZ, "GlideX Team")
                winreg.SetValueEx(uninst_key, "InstallLocation", 0, winreg.REG_SZ, self.target_dir)
                winreg.SetValueEx(uninst_key, "DisplayIcon", 0, winreg.REG_SZ, f'"{installed_ico}"')
                winreg.SetValueEx(uninst_key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_exe}"')
                winreg.SetValueEx(uninst_key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(uninst_key, "NoRepair", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(uninst_key, "EstimatedSize", 0, winreg.REG_DWORD, 118000)
                winreg.CloseKey(uninst_key)
            except Exception:
                pass

            self.progress_changed.emit(100, "Installation completed successfully!")
            self.finished_signal.emit(True, "Setup finished.")

        except Exception as e:
            self.finished_signal.emit(False, str(e))


class SetupWizardWindow(QMainWindow):
    def __init__(self, payload_dir: str):
        super().__init__()
        self.payload_dir = os.path.abspath(payload_dir)
        self.default_install_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Programs",
            "GlideX"
        )
        self.target_install_dir = self.default_install_dir

        self.setWindowTitle("GlideX Setup")
        self.resize(600, 440)
        self.setFixedSize(600, 440)
        self.setStyleSheet(INSTALLER_STYLE)

        self._setup_icon()
        self._init_ui()

    def _setup_icon(self):
        candidates = [
            os.path.join(self.payload_dir, "assets", "GlideX.ico"),
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

        # Page 0: Welcome
        self.page_welcome = self._create_welcome_page()
        self.stack.addWidget(self.page_welcome)

        # Page 1: Install Location
        self.page_location = self._create_location_page()
        self.stack.addWidget(self.page_location)

        # Page 2: Options
        self.page_options = self._create_options_page()
        self.stack.addWidget(self.page_options)

        # Page 3: Progress
        self.page_progress = self._create_progress_page()
        self.stack.addWidget(self.page_progress)

        # Page 4: Completed
        self.page_completed = self._create_completed_page()
        self.stack.addWidget(self.page_completed)

    # -------------------------------------------------------------------------
    # PAGE 0: WELCOME
    # -------------------------------------------------------------------------
    def _create_welcome_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(12)

        lbl_title = QLabel("Welcome to GlideX Setup")
        lbl_title.setObjectName("Title")
        card_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "This setup wizard will install GlideX on your computer.\n\n"
            "GlideX is the ultra-smooth, physics-based cursor enhancement suite "
            "designed specifically for Windows 11 with interactive particle ripples, "
            "spotlights, sub-pixel motion smoothing, and real-time cursor schemes."
        )
        lbl_desc.setObjectName("Subtitle")
        lbl_desc.setWordWrap(True)
        card_layout.addWidget(lbl_desc)

        card_layout.addSpacing(6)
        highlights = QLabel(
            "• Ultra-smooth sub-pixel interpolation with dynamic velocity tilt\n"
            "• 100% complete Windows 11 cursor scheme support\n"
            "• Click ripples, spotlights, halo glows, and sound synthesis\n"
            "• Emergency failsafe: Ctrl + Shift + Q"
        )
        highlights.setStyleSheet("font-size: 12px; color: #38BDF8; line-height: 1.5;")
        card_layout.addWidget(highlights)

        layout.addWidget(card)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryBtn")
        btn_cancel.clicked.connect(self.close)
        btn_row.addWidget(btn_cancel)

        btn_next = QPushButton("Next >")
        btn_next.setObjectName("PrimaryBtn")
        btn_next.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_row.addWidget(btn_next)

        layout.addLayout(btn_row)
        return w

    # -------------------------------------------------------------------------
    # PAGE 1: INSTALL LOCATION
    # -------------------------------------------------------------------------
    def _create_location_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(10)

        lbl_title = QLabel("Choose Install Location")
        lbl_title.setObjectName("Title")
        card_layout.addWidget(lbl_title)

        lbl_desc = QLabel("Select the destination folder where GlideX should be installed:")
        lbl_desc.setObjectName("Subtitle")
        card_layout.addWidget(lbl_desc)

        # Path input row
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self.txt_path = QLineEdit(self.default_install_dir)
        self.txt_path.textChanged.connect(self._on_path_changed)
        path_row.addWidget(self.txt_path)

        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("BrowseBtn")
        btn_browse.clicked.connect(self._browse_directory)
        path_row.addWidget(btn_browse)

        card_layout.addLayout(path_row)

        # Space labels
        space_row = QHBoxLayout()
        lbl_req = QLabel("Space required: ~118 MB")
        lbl_req.setObjectName("DiskSpace")
        space_row.addWidget(lbl_req)
        space_row.addStretch()

        self.lbl_avail = QLabel(f"Space available: {get_disk_free_gb(self.default_install_dir):.1f} GB")
        self.lbl_avail.setObjectName("DiskSpace")
        space_row.addWidget(self.lbl_avail)
        card_layout.addLayout(space_row)

        # Update / Upgrade detection banner
        self.banner_frame = QFrame()
        self.banner_frame.setObjectName("Banner")
        b_layout = QHBoxLayout(self.banner_frame)
        b_layout.setContentsMargins(8, 6, 8, 6)
        self.lbl_banner = QLabel("Existing installation detected — your settings and custom cursors will be preserved during this update.")
        self.lbl_banner.setObjectName("BannerText")
        self.lbl_banner.setWordWrap(True)
        b_layout.addWidget(self.lbl_banner)
        card_layout.addWidget(self.banner_frame)

        self._check_upgrade_status(self.default_install_dir)

        layout.addWidget(card)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryBtn")
        btn_cancel.clicked.connect(self.close)
        btn_row.addWidget(btn_cancel)

        btn_row.addStretch()

        btn_back = QPushButton("< Back")
        btn_back.setObjectName("SecondaryBtn")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_row.addWidget(btn_back)

        btn_next = QPushButton("Next >")
        btn_next.setObjectName("PrimaryBtn")
        btn_next.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_row.addWidget(btn_next)

        layout.addLayout(btn_row)
        return w

    def _browse_directory(self):
        d = QFileDialog.getExistingDirectory(self, "Select Installation Directory", self.txt_path.text())
        if d:
            chosen = os.path.join(d, "GlideX") if not d.endswith("GlideX") else d
            self.txt_path.setText(chosen)

    def _on_path_changed(self, text: str):
        self.target_install_dir = text.strip()
        free_gb = get_disk_free_gb(self.target_install_dir)
        self.lbl_avail.setText(f"Space available: {free_gb:.1f} GB")
        self._check_upgrade_status(self.target_install_dir)

    def _check_upgrade_status(self, path: str):
        if is_already_installed(path):
            self.banner_frame.show()
        else:
            self.banner_frame.hide()

    # -------------------------------------------------------------------------
    # PAGE 2: OPTIONS
    # -------------------------------------------------------------------------
    def _create_options_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        lbl_title = QLabel("Installation Options")
        lbl_title.setObjectName("Title")
        card_layout.addWidget(lbl_title)

        lbl_desc = QLabel("Select shortcuts and startup preferences for GlideX:")
        lbl_desc.setObjectName("Subtitle")
        card_layout.addWidget(lbl_desc)

        card_layout.addSpacing(4)

        self.chk_desktop = QCheckBox("Create a Desktop shortcut (GlideX.lnk)")
        self.chk_desktop.setChecked(True)
        card_layout.addWidget(self.chk_desktop)

        self.chk_start_menu = QCheckBox("Create a Start Menu shortcut")
        self.chk_start_menu.setChecked(True)
        card_layout.addWidget(self.chk_start_menu)

        self.chk_startup = QCheckBox("Launch GlideX automatically when Windows starts")
        self.chk_startup.setChecked(False)
        card_layout.addWidget(self.chk_startup)

        layout.addWidget(card)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryBtn")
        btn_cancel.clicked.connect(self.close)
        btn_row.addWidget(btn_cancel)

        btn_row.addStretch()

        btn_back = QPushButton("< Back")
        btn_back.setObjectName("SecondaryBtn")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_row.addWidget(btn_back)

        btn_install = QPushButton("Install")
        btn_install.setObjectName("PrimaryBtn")
        btn_install.clicked.connect(self._start_installation)
        btn_row.addWidget(btn_install)

        layout.addLayout(btn_row)
        return w

    # -------------------------------------------------------------------------
    # PAGE 3: PROGRESS
    # -------------------------------------------------------------------------
    def _create_progress_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        lbl_title = QLabel("Installing GlideX...")
        lbl_title.setObjectName("Title")
        card_layout.addWidget(lbl_title)

        self.status_label = QLabel("Preparing installation files...")
        self.status_label.setObjectName("Subtitle")
        card_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        card_layout.addWidget(self.progress_bar)

        layout.addWidget(card)
        layout.addStretch()
        return w

    # -------------------------------------------------------------------------
    # PAGE 4: COMPLETED
    # -------------------------------------------------------------------------
    def _create_completed_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        lbl_title = QLabel("Completing GlideX Setup")
        lbl_title.setObjectName("Title")
        card_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "GlideX has been successfully installed on your computer.\n\n"
            "You can access GlideX anytime from your Desktop, Start Menu, "
            "or the Windows System Tray icon near the clock."
        )
        lbl_desc.setObjectName("Subtitle")
        card_layout.addWidget(lbl_desc)

        card_layout.addSpacing(6)
        self.chk_launch = QCheckBox("Launch GlideX now")
        self.chk_launch.setChecked(True)
        card_layout.addWidget(self.chk_launch)

        layout.addWidget(card)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_finish = QPushButton("Finish")
        btn_finish.setObjectName("PrimaryBtn")
        btn_finish.clicked.connect(self._on_finish_clicked)
        btn_row.addWidget(btn_finish)

        layout.addLayout(btn_row)
        return w

    def _start_installation(self):
        self.stack.setCurrentIndex(3)
        opts = {
            "desktop_shortcut": self.chk_desktop.isChecked(),
            "start_menu_shortcut": self.chk_start_menu.isChecked(),
            "start_with_windows": self.chk_startup.isChecked()
        }
        self.worker = InstallWorker(self.payload_dir, self.target_install_dir, opts)
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.status_label.setText(msg)

    def _on_finished(self, success: bool, msg: str):
        if success:
            self.stack.setCurrentIndex(4)
        else:
            self.status_label.setText(f"Installation error: {msg}")

    def _on_finish_clicked(self):
        if self.chk_launch.isChecked():
            installed_exe = os.path.join(self.target_install_dir, "GlideX.exe")
            if os.path.exists(installed_exe):
                try:
                    subprocess.Popen(
                        [installed_exe],
                        cwd=self.target_install_dir,
                        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    )
                except Exception:
                    pass
        self.close()
        sys.exit(0)


def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GlideX.CursorPhysics.Setup.v1")
    except Exception:
        pass

    app = QApplication.instance() or QApplication(sys.argv)

    # Determine payload directory
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    payload_candidates = [
        os.path.join(base_dir, "payload"),
        os.path.join(os.path.dirname(base_dir), "payload"),
        os.path.join(base_dir, "portable", "GlideX"),
        os.path.join(os.path.dirname(base_dir), "portable", "GlideX")
    ]
    payload_dir = ""
    for c in payload_candidates:
        if os.path.exists(c) and os.path.exists(os.path.join(c, "bin")):
            payload_dir = c
            break

    if not payload_dir:
        payload_dir = os.path.join(base_dir, "payload")

    win = SetupWizardWindow(payload_dir)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
