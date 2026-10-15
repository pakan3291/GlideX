"""
Configuration Manager & Persistence
==================================
Handles settings schema, local JSON persistence, Windows startup registry, and presets.
"""

import os
import sys
import json
import winreg
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional


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
            filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as e:
            print(f"[GlideX] Config save notice: {e}")

    @classmethod
    def load_from_file(cls, filepath: Optional[str] = None) -> 'AppConfig':
        """Load configuration from JSON file or return default."""
        if not filepath:
            filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
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
    exe_path = sys.executable
    if not exe_path.lower().endswith(".exe"):
        main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
        cmd = f'"{sys.executable}" "{main_py}"'
    else:
        cmd = f'"{exe_path}"'

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
