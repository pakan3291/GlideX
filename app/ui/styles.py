"""
UI Theme Styles & Reusable Interactive Widgets
==============================================
Modern dark stylesheet definitions (#0F0F12 / #16161D / #1E1E28) and the
interactive test preview playground widget.
"""

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QFont
)
from PySide6.QtWidgets import QFrame

from app.config import AppConfig
from app.core.cursor_manager import WindowsCursorExtractor
from app.core.input_hook import SoundSynthesizer

DARK_THEME_QSS = """
    QMainWindow {
        background-color: #16161D;
    }
    QWidget {
        color: #ECECF2;
        font-family: 'Segoe UI', -apple-system, sans-serif;
        font-size: 13px;
    }
    QFrame#Sidebar {
        background-color: #0F0F12;
        border-right: 1px solid #232332;
    }
    QPushButton#NavBtn {
        text-align: left;
        background-color: transparent;
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
        font-weight: 500;
        color: #9E9EB8;
    }
    QPushButton#NavBtn:hover {
        background-color: #1B1B26;
        color: #FFFFFF;
    }
    QPushButton#NavBtn:checked {
        background-color: #212132;
        color: #FFFFFF;
        font-weight: 600;
        border-left: 3px solid #6366F1;
    }
    QFrame#Card {
        background-color: #1E1E28;
        border: 1px solid #2D2D3E;
        border-radius: 12px;
        padding: 16px;
    }
    QLabel#CardTitle {
        font-size: 14px;
        font-weight: 600;
        color: #FFFFFF;
    }
    QLabel#CardSubtitle {
        font-size: 11px;
        color: #8C8CA4;
    }
    QSlider::groove:horizontal {
        height: 6px;
        background: #2B2B3C;
        border-radius: 3px;
    }
    QSlider::sub-page:horizontal {
        background: #6366F1;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #FFFFFF;
        border: 2px solid #6366F1;
        width: 18px;
        margin-top: -6px;
        margin-bottom: -6px;
        border-radius: 9px;
    }
    QSlider::handle:horizontal:hover {
        background: #EAEBFF;
        border-color: #818CF8;
    }
    QCheckBox {
        spacing: 10px;
        color: #ECECF2;
    }
    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border-radius: 6px;
        border: 1px solid #3B3B4E;
        background-color: #1B1B26;
    }
    QCheckBox::indicator:hover {
        border-color: #6366F1;
    }
    QCheckBox::indicator:checked {
        background-color: #6366F1;
        border-color: #6366F1;
    }
    QPushButton#ActionBtn {
        background-color: #252538;
        color: #FFFFFF;
        border: 1px solid #3B3B52;
        border-radius: 8px;
        padding: 7px 14px;
        font-weight: 500;
    }
    QPushButton#ActionBtn:hover {
        background-color: #313148;
        border-color: #4F4F70;
    }
    QPushButton#PrimaryBtn {
        background-color: #6366F1;
        color: #FFFFFF;
        border: 1px solid #7174FA;
        border-radius: 8px;
        padding: 7px 16px;
        font-weight: 600;
    }
    QPushButton#PrimaryBtn:hover {
        background-color: #4F46E5;
    }
    QPushButton#DangerBtn {
        background-color: #381518;
        border: 1px solid #632226;
        color: #FF6B72;
        font-weight: 600;
        border-radius: 8px;
        padding: 7px 14px;
    }
    QPushButton#DangerBtn:hover {
        background-color: #4A1B20;
        border-color: #8C2E34;
    }
    QComboBox {
        background-color: #20202E;
        color: #FFFFFF;
        border: 1px solid #38384E;
        border-radius: 8px;
        padding: 6px 12px;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QScrollArea {
        border: none;
        background-color: transparent;
    }
"""

TRAY_MENU_QSS = """
    QMenu {
        background-color: #171722;
        color: #ECECF2;
        border: 1px solid #282838;
        border-radius: 8px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 20px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #6366F1;
        color: #FFFFFF;
    }
    QMenu::separator {
        height: 1px;
        background: #282838;
        margin: 4px 8px;
    }
"""


class TestAreaWidget(QFrame):
    """Interactive preview canvas with Link, Text, Grab/Drag Fist, and Busy zones."""

    def __init__(self, config: AppConfig, sound_synth: SoundSynthesizer, extractor: WindowsCursorExtractor):
        super().__init__()
        self.config = config
        self.sound = sound_synth
        self.extractor = extractor
        self.setMinimumHeight(130)
        self.setMouseTracking(True)

        self.preview_scale = 1.0
        self.scale_velocity = 0.0
        self.is_pressed = False
        self.test_ripples = []

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def mouseMoveEvent(self, event):
        x = event.position().x()
        w = self.width()
        if x < w * 0.25:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif x < w * 0.50:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        elif x < w * 0.75:
            self.setCursor(Qt.CursorShape.OpenHandCursor if not self.is_pressed else Qt.CursorShape.ClosedHandCursor)
        else:
            self.setCursor(Qt.CursorShape.WaitCursor)

    def mousePressEvent(self, event):
        self.is_pressed = True
        x = event.position().x()
        w = self.width()
        if w * 0.50 <= x < w * 0.75:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        if self.config.sound_enabled:
            self.sound.play_click(self.config.sound_style, self.config.sound_volume)
        if self.config.ripple_enabled:
            self.test_ripples.append({
                'pos': event.position(),
                'radius': 5.0,
                'alpha': 230
            })
        self.update()

    def mouseReleaseEvent(self, event):
        self.is_pressed = False
        x = event.position().x()
        w = self.width()
        if w * 0.50 <= x < w * 0.75:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()

    def _tick(self):
        dt = 0.016
        desired = self.config.press_scale if self.is_pressed else 1.0
        accel = 380.0 * (desired - self.preview_scale) - 22.0 * self.scale_velocity
        self.scale_velocity += accel * dt
        self.preview_scale += self.scale_velocity * dt

        new_ripples = []
        for r in self.test_ripples:
            r['radius'] += 110.0 * dt
            r['alpha'] -= 300.0 * dt
            if r['alpha'] > 0 and r['radius'] < 42.0:
                new_ripples.append(r)
        self.test_ripples = new_ripples
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        w = rect.width()
        h = rect.height()

        painter.setPen(QPen(QColor(45, 45, 60), 1))
        painter.setBrush(QBrush(QColor(18, 18, 26)))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)

        # Dividers
        painter.setPen(QPen(QColor(38, 38, 52), 1, Qt.PenStyle.DashLine))
        painter.drawLine(int(w * 0.25), 10, int(w * 0.25), h - 10)
        painter.drawLine(int(w * 0.50), 10, int(w * 0.50), h - 10)
        painter.drawLine(int(w * 0.75), 10, int(w * 0.75), h - 10)

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        painter.setPen(QColor(140, 140, 165))

        painter.drawText(QRectF(0, 0, w * 0.25, h), Qt.AlignmentFlag.AlignCenter, "🔗 Link\n(Hand)")
        painter.drawText(QRectF(w * 0.25, 0, w * 0.25, h), Qt.AlignmentFlag.AlignCenter, "📝 Text\n(I-Beam)")
        painter.drawText(QRectF(w * 0.50, 0, w * 0.25, h), Qt.AlignmentFlag.AlignCenter, "🖐️ Pan / Drag\n(Click to Fist)")
        painter.drawText(QRectF(w * 0.75, 0, w * 0.75, h), Qt.AlignmentFlag.AlignCenter, "⏳ Busy\n(Ani Spinner)")

        # Ripples
        col = QColor(self.config.ripple_color)
        for r in self.test_ripples:
            alpha = max(0, min(255, int(r['alpha'])))
            painter.setPen(QPen(QColor(col.red(), col.green(), col.blue(), alpha), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(r['pos'], r['radius'], r['radius'])
