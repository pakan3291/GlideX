"""
Configuration Manager & Persistence
==================================
Handles settings schema, local JSON persistence, Windows startup registry, and presets.
Supports portable mode resolution (portable/GlideX/config/settings.json) and dev mode.
"""

import os
import sys
import json
import winreg
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional


def get_app_root() -> str:
    """Returns the application root directory (source root or portable root)."""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        # If running from inside bin/, the portable root is one level up
        if os.path.basename(exe_dir).lower() == "bin":
            return os.path.dirname(exe_dir)
        return exe_dir
    # Running from Python source: project root is two levels up from app/config.py
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_default_config_path() -> str:
    """Returns the appropriate settings file path (config/settings.json for portable, config.json for dev)."""
    root = get_app_root()
    if getattr(sys, 'frozen', False):
        cfg_dir = os.path.join(root, "config")
        os.makedirs(cfg_dir, exist_ok=True)
        return os.path.join(cfg_dir, "settings.json")

    # In source mode: if config/settings.json exists use it, else default to config.json
    cfg_dir = os.path.join(root, "config")
    settings_json = os.path.join(cfg_dir, "settings.json")
    if os.path.exists(settings_json):
        return settings_json
    return os.path.join(root, "config.json")


def get_cursors_dir() -> str:
    """Returns the assets/cursors directory path."""
    root = get_app_root()
    cursors_dir = os.path.join(root, "assets", "cursors")
    os.makedirs(cursors_dir, exist_ok=True)
    return cursors_dir


def get_asset_path(filename: str) -> str:
    """
    Returns the absolute path to an asset file (e.g. GlideX.ico, GlideX.png, GlideX.svg).
    Checks PyInstaller _MEIPASS, portable root assets/, and project root assets/.
    """
    if hasattr(sys, '_MEIPASS'):
        mei_path = os.path.join(sys._MEIPASS, "assets", filename)
        if os.path.exists(mei_path):
            return mei_path
        mei_root = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(mei_root):
            return mei_root

    root = get_app_root()
    asset_path = os.path.join(root, "assets", filename)
    if os.path.exists(asset_path):
        return asset_path

    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        exe_asset = os.path.join(exe_dir, "assets", filename)
        if os.path.exists(exe_asset):
            return exe_asset

    return asset_path


def get_app_icon():
    """
    Builds a multi-size QIcon containing high-res ICO and pre-rendered pixmaps
    (16, 20, 24, 32, 40, 48, 64, 128, 256) for razor-sharp rendering in Windows 11
    Explorer, Taskbar, and System Tray (^ overflow menu).
    """
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtCore import Qt

    icon = QIcon()
    ico_path = get_asset_path("GlideX.ico")
    if os.path.exists(ico_path):
        icon = QIcon(ico_path)

    png_path = get_asset_path("GlideX.png")
    if os.path.exists(png_path):
        base_pixmap = QPixmap(png_path)
        if not base_pixmap.isNull():
            for s in (16, 20, 24, 32, 40, 48, 64, 128, 256):
                scaled = base_pixmap.scaled(
                    s, s,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                icon.addPixmap(scaled)

    return icon


@dataclass
class AppConfig:
    # General
    master_enabled: bool = True
    hide_native_cursor: bool = True
    cursor_scale: float = 1.6
    start_with_windows: bool = False
    multi_monitor_aware: bool = True

    # Physics & Smoothness
    smoothing_factor: float = 0.45
    tilt_enabled: bool = True
    tilt_max_angle: float = 24.0
    tilt_stiffness: float = 0.20
    velocity_stretch: bool = True
    stretch_intensity: float = 1.0
    motion_trail_enabled: bool = False
    trail_length: int = 5
    trail_opacity: float = 0.35

    # Click & Drag
    click_bounce_enabled: bool = True
    press_scale: float = 0.78
    release_overshoot: float = 1.14
    bounce_speed: float = 380.0
    drag_compression_enabled: bool = True
    drag_scale: float = 0.88

    # Ripple & Sound
    ripple_enabled: bool = True
    ripple_style: str = "Ring"           # "Ring", "Filled Pulse", "Dual Wave"
    ripple_color: str = "#3B82F6"
    ripple_size: float = 46.0
    ripple_duration: float = 350.0
    sound_enabled: bool = False
    sound_style: str = "Soft Pop"        # "Soft Pop", "Mechanical Switch", "macOS Tap"
    sound_volume: float = 0.70

    # Halo & Spotlight
    halo_enabled: bool = False
    halo_color: str = "#6366F1"
    halo_radius: float = 36.0
    halo_opacity: float = 0.26
    spotlight_enabled: bool = False
    spotlight_radius: float = 180.0
    spotlight_darkness: float = 0.45
    spotlight_feather: float = 45.0

    # Per-Cursor Fine Tuning
    per_cursor_overrides: Dict[str, dict] = field(default_factory=dict)

    # Hotkeys
    emergency_hotkey: str = "<ctrl>+<shift>+q"
    toggle_overlay_hotkey: str = "<ctrl>+<shift>+s"
    spotlight_hotkey: str = "<ctrl>+<shift>+f"

    def save_to_file(self, filepath: Optional[str] = None):
        """Save configuration to JSON file."""
        if not filepath:
            filepath = get_default_config_path()
        try:
            parent_dir = os.path.dirname(filepath)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as e:
            print(f"[GlideX] Config save notice: {e}")

    @classmethod
    def load_from_file(cls, filepath: Optional[str] = None) -> 'AppConfig':
        """Load configuration from JSON file or return default."""
        if not filepath:
            filepath = get_default_config_path()
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception as e:
                print(f"[GlideX] Config load notice: {e}")
        return cls()


def set_start_with_windows(enable: bool):
    """Manages Windows startup registry entry under HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run."""
    run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "GlideX"
    if getattr(sys, 'frozen', False):
        root = get_app_root()
        root_exe = os.path.join(root, "GlideX.exe")
        if os.path.exists(root_exe):
            cmd = f'"{root_exe}"'
        else:
            cmd = f'"{sys.executable}"'
    else:
        main_py = os.path.join(get_app_root(), "main.py")
        cmd = f'"{sys.executable}" "{main_py}"'

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except WindowsError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[GlideX] Startup registry error: {e}")


def is_start_with_windows() -> bool:
    """Checks whether the application is configured to start with Windows."""
    run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "GlideX"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except WindowsError:
        return False
