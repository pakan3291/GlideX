"""
Input Hooks & Sound Synthesizer
===============================
Global mouse movement/click events bridge via pynput, and multi-style synthesized
in-memory haptic sound effects.
"""

import io
import wave
import math
import struct
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QObject, Signal
from pynput import mouse
import winsound

from app.core.win32_api import get_current_cursor_pos


class SoundSynthesizer:
    """Generates and plays multi-style haptic pop/click sounds in memory."""

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AudioWorker")
        self._cache = {}

    def _generate_sound(self, style: str, volume: float) -> bytes:
        sample_rate = 44100
        duration = 0.030
        total_samples = int(sample_rate * duration)

        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)

            frames = []
            for i in range(total_samples):
                t = i / sample_rate
                if style == "Mechanical Switch":
                    freq = 2800.0 * math.exp(-t * 220.0) + 400.0
                    decay = math.exp(-t * 180.0)
                    noise = (((i * 73) % 100) / 50.0 - 1.0) * math.exp(-t * 400.0) * 0.4
                    val = (math.sin(2.0 * math.pi * freq * t) * 0.6 + noise) * decay
                elif style == "macOS Tap":
                    freq = 680.0 * math.exp(-t * 70.0) + 120.0
                    decay = math.exp(-t * 140.0)
                    val = math.sin(2.0 * math.pi * freq * t) * decay
                else:  # "Soft Pop"
                    freq = 1350.0 * math.exp(-t * 95.0) + 240.0
                    decay = math.exp(-t * 125.0)
                    pop = math.sin(2.0 * math.pi * 3200.0 * t) * math.exp(-t * 380.0) * 0.35
                    val = (math.sin(2.0 * math.pi * freq * t) * 0.65 + pop) * decay

                sample_val = int(val * 24000 * max(0.0, min(1.0, volume)))
                sample_val = max(-32767, min(32767, sample_val))
                frames.append(struct.pack('<h', sample_val))

            wav.writeframes(b''.join(frames))
        return wav_io.getvalue()

    def play_click(self, style: str = "Soft Pop", volume: float = 0.7):
        try:
            key = (style, round(volume, 2))
            if key not in self._cache:
                self._cache[key] = self._generate_sound(style, volume)
            data = self._cache[key]
            self._executor.submit(winsound.PlaySound, data, winsound.SND_MEMORY | winsound.SND_ASYNC)
        except Exception:
            pass


class MouseBridge(QObject):
    """Thread-safe event bridge from pynput listener to Qt."""
    button_pressed = Signal(float, float, str)
    button_released = Signal(float, float, str)
    mouse_moved = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.target_x = 0.0
        self.target_y = 0.0
        self.is_pressed = False
        self._listener = None

    def start(self):
        cx, cy = get_current_cursor_pos()
        self.target_x = float(cx)
        self.target_y = float(cy)

        self._listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click
        )
        self._listener.daemon = True
        self._listener.start()

    def _on_move(self, x, y):
        self.target_x = float(x)
        self.target_y = float(y)
        self.mouse_moved.emit(self.target_x, self.target_y)

    def _on_click(self, x, y, button, pressed):
        btn_name = "left" if button == mouse.Button.left else "right" if button == mouse.Button.right else "other"
        self.target_x = float(x)
        self.target_y = float(y)
        if pressed:
            self.is_pressed = True
            self.button_pressed.emit(float(x), float(y), btn_name)
        else:
            self.is_pressed = False
            self.button_released.emit(float(x), float(y), btn_name)

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
