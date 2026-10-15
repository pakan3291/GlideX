"""
System Tray Icon & Context Menu Manager
=======================================
Manages the Windows notification area tray icon and quick action context menu.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from typing import Optional
from app.config import AppConfig, get_app_icon
from app.core.cursor_manager import WindowsCursorExtractor
from app.ui.styles import TRAY_MENU_QSS


class TrayIconManager:
    """Manages QSystemTrayIcon and its context menu."""

    def __init__(self, app_instance, config: AppConfig, extractor: WindowsCursorExtractor, dashboard, icon: Optional[QIcon] = None):
        self.app = app_instance
        self.config = config
        self.extractor = extractor
        self.dashboard = dashboard
        self.icon = icon if (icon is not None and not icon.isNull()) else get_app_icon()
        self._init_tray()

    def _init_tray(self):
        self.tray = QSystemTrayIcon(self.app)
        self.tray.setIcon(self.icon)
        self.tray.setToolTip(f"GlideX ({self.extractor.scheme_name})")

        menu = QMenu()
        menu.setStyleSheet(TRAY_MENU_QSS)

        action_open = menu.addAction("Open Control Dashboard...")
        action_open.triggered.connect(self._show_dashboard)

        menu.addSeparator()

        self.action_master = menu.addAction("Enable Custom Overlay")
        self.action_master.setCheckable(True)
        self.action_master.setChecked(self.config.master_enabled)
        self.action_master.triggered.connect(self._toggle_master)

        self.action_hide_cursor = menu.addAction("Hide Native Hardware Cursor")
        self.action_hide_cursor.setCheckable(True)
        self.action_hide_cursor.setChecked(self.config.hide_native_cursor)
        self.action_hide_cursor.triggered.connect(self._toggle_hide_cursor)

        action_restore = menu.addAction("Emergency Restore Cursors (Ctrl+Shift+Q)")
        action_restore.triggered.connect(self._emergency_restore)

        menu.addSeparator()

        action_exit = menu.addAction("Exit GlideX")
        action_exit.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.setVisible(True)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_dashboard()

    def _show_dashboard(self):
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()

    def _toggle_master(self, checked: bool):
        self.dashboard.chk_master.setChecked(checked)

    def _toggle_hide_cursor(self, checked: bool):
        self.dashboard.chk_hide_native.setChecked(checked)

    def _emergency_restore(self):
        self.dashboard._emergency_restore_action()
