"""
GlideX - Main Application Entry Point
=====================================
Clean entry point initializing configuration, Win32 failsafes, low-level input
hooks, fullscreen overlay rendering, settings dashboard, and system tray icon.
"""

import sys
from PySide6.QtWidgets import QApplication
from pynput import keyboard

from app.config import AppConfig
from app.core.win32_api import SystemCursorManager
from app.core.cursor_manager import WindowsCursorExtractor
from app.core.input_hook import SoundSynthesizer, MouseBridge
from app.overlay.overlay_window import CursorOverlayWindow
from app.ui.main_window import ModernDashboardWindow
from app.ui.tray_icon import TrayIconManager


class GlideXApp:
    """Master application controller coordinating overlay, tray, hooks, and GUI."""

    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # 1. Load Persistent Config
        self.config = AppConfig.load_from_file()

        # 2. Initialize Core Subsystems
        self.sound = SoundSynthesizer()
        self.cursor_mgr = SystemCursorManager()
        self.bridge = MouseBridge()
        self.extractor = WindowsCursorExtractor(self.config.per_cursor_overrides)

        # 3. Hide Hardware Cursor on Startup if enabled
        if self.config.master_enabled and self.config.hide_native_cursor:
            self.cursor_mgr.hide()

        # 4. Windows & GUI
        self.overlay = CursorOverlayWindow(self.config, self.bridge, self.sound, self.extractor)
        self.dashboard = ModernDashboardWindow(self.config, self.cursor_mgr, self.sound, self.extractor)

        # 5. System Tray & Hotkeys
        self.tray_manager = TrayIconManager(self.app, self.config, self.extractor, self.dashboard)
        self._init_global_hotkeys()

        self.app.aboutToQuit.connect(self._cleanup)

    def _init_global_hotkeys(self):
        def on_failsafe():
            print("[GlideX] Failsafe Hotkey triggered! Restoring Windows cursors...")
            self.cursor_mgr.restore()
            self.dashboard.chk_master.setChecked(False)
            self.dashboard.chk_hide_native.setChecked(False)
            self.tray_manager.action_master.setChecked(False)
            self.tray_manager.action_hide_cursor.setChecked(False)
            self.config.master_enabled = False
            self.config.hide_native_cursor = False
            self.config.save_to_file()

        def on_toggle_overlay():
            new_state = not self.config.master_enabled
            self.dashboard.chk_master.setChecked(new_state)

        def on_toggle_spotlight():
            new_state = not self.config.spotlight_enabled
            self.dashboard.chk_spot.setChecked(new_state)

        self._hotkey_listener = keyboard.GlobalHotKeys({
            '<ctrl>+<shift>+q': on_failsafe,
            '<ctrl>+<shift>+s': on_toggle_overlay,
            '<ctrl>+<shift>+f': on_toggle_spotlight
        })
        self._hotkey_listener.daemon = True
        self._hotkey_listener.start()

    def start(self):
        self.bridge.start()
        self.overlay.show()
        self.dashboard.show()
        return self.app.exec()

    def _cleanup(self):
        self.cursor_mgr.restore()
        self.bridge.stop()
        if hasattr(self, '_hotkey_listener'):
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass


def main():
    app = GlideXApp()
    sys.exit(app.start())


if __name__ == "__main__":
    main()
