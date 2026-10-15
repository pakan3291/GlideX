"""
Fullscreen Click-Through Overlay Window
=======================================
High-performance 60+ FPS overlay window rendering extracted Windows cursors,
motion smoothing, directional banking tilt, velocity stretch, click bounce,
drag compression, ripples, halo, spotlight, and animated .ani playback.
"""

import time
import math
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QRadialGradient
)
from PySide6.QtWidgets import QWidget

from app.config import AppConfig
from app.core.win32_api import (
    get_virtual_desktop_rect,
    get_current_cursor_pos,
    apply_click_through
)
from app.core.cursor_manager import (
    WindowsCursorExtractor,
    CursorShapeDetector,
    render_extracted_cursor
)
from app.core.input_hook import MouseBridge, SoundSynthesizer


class CursorOverlayWindow(QWidget):
    """
    Transparent fullscreen overlay rendering all 17 Windows cursors + Grab/Grabbing,
    velocity physics, click bounce, halo, spotlight, and animated .ani playback.
    """

    def __init__(self, config: AppConfig, mouse_bridge: MouseBridge, sound_synth: SoundSynthesizer, extractor: WindowsCursorExtractor):
        super().__init__()
        self.config = config
        self.bridge = mouse_bridge
        self.sound = sound_synth
        self.extractor = extractor
        self.detector = CursorShapeDetector(self.extractor)

        self.rendered_x = self.bridge.target_x
        self.rendered_y = self.bridge.target_y
        self.prev_target_x = self.bridge.target_x
        self.prev_target_y = self.bridge.target_y

        self.current_scale = 1.0
        self.scale_velocity = 0.0

        self.current_angle = 0.0
        self.current_stretch = 1.0
        self.current_squash = 1.0

        self.active_shape = "ARROW"
        self.prev_shape = "ARROW"
        self.active_custom_asset = None
        self.prev_custom_asset = None
        self.morph_progress = 1.0

        self.start_time = time.time()
        self.ripples = []
        self.history_positions = []

        self.vx, self.vy, self.vw, self.vh = get_virtual_desktop_rect()

        self._init_window()
        self._init_events()

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._animation_tick)
        self.timer.start(10)

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setGeometry(self.vx, self.vy, self.vw, self.vh)

    def showEvent(self, event):
        super().showEvent(event)
        apply_click_through(int(self.winId()))

    def _init_events(self):
        self.bridge.button_pressed.connect(self._on_button_pressed)
        self.bridge.button_released.connect(self._on_button_released)

    def _on_button_pressed(self, x: float, y: float, btn: str):
        if not self.config.master_enabled:
            return

        if self.config.sound_enabled:
            self.sound.play_click(self.config.sound_style, self.config.sound_volume)

        if self.config.ripple_enabled:
            col = QColor(self.config.ripple_color) if btn == "left" else QColor("#8B5CF6")
            self.ripples.append({
                'x': x,
                'y': y,
                'radius': 4.0,
                'max_radius': self.config.ripple_size,
                'alpha': 230,
                'color': col,
                'style': self.config.ripple_style
            })

    def _on_button_released(self, x: float, y: float, btn: str):
        pass

    def _animation_tick(self):
        if not self.config.master_enabled:
            self.update()
            return

        dt = 0.010
        cx, cy = get_current_cursor_pos()
        target_x = float(cx)
        target_y = float(cy)

        # 1. Detect cursor shape & custom handles
        detected_shape, custom_hcur = self.detector.detect(target_x, target_y)

        custom_asset = None
        if detected_shape == "DYNAMIC" and custom_hcur:
            custom_asset = self.extractor.dynamic_cache.get_or_extract(custom_hcur)

        # 2. Interactive Drag Transition: Holding left-click turns Hand/Grab into Grabbing
        if self.bridge.is_pressed:
            if detected_shape in ("GRAB", "HAND"):
                detected_shape = "GRABBING"
                custom_asset = None
        elif detected_shape == "GRABBING" and not self.bridge.is_pressed:
            detected_shape = "GRAB"
            custom_asset = None

        if detected_shape == "DYNAMIC" and not custom_asset:
            detected_shape = "GRABBING" if self.bridge.is_pressed else "GRAB"

        shape_changed = (detected_shape != self.active_shape)
        asset_changed = (custom_asset != self.active_custom_asset)

        if shape_changed or asset_changed:
            self.prev_shape = self.active_shape
            self.prev_custom_asset = self.active_custom_asset
            self.active_shape = detected_shape
            self.active_custom_asset = custom_asset
            self.morph_progress = 0.0

        if self.morph_progress < 1.0:
            self.morph_progress = min(1.0, self.morph_progress + (dt / 0.075))

        # 3. Smooth Lerp Interpolation
        smoothing = max(0.08, min(1.0, self.config.smoothing_factor))
        if smoothing >= 0.98:
            self.rendered_x = target_x
            self.rendered_y = target_y
        else:
            blend = 1.0 - math.pow(1.0 - smoothing, dt * 60.0)
            blend = max(0.01, min(1.0, blend))
            self.rendered_x += (target_x - self.rendered_x) * blend
            self.rendered_y += (target_y - self.rendered_y) * blend

        # 4. Directional Banking / Tilt Physics
        vel_x = target_x - self.rendered_x
        if self.config.tilt_enabled:
            max_ang = self.config.tilt_max_angle
            desired_angle = max(-max_ang, min(max_ang, vel_x * 0.42))
            stiff = max(0.05, min(0.40, self.config.tilt_stiffness))
            self.current_angle += (desired_angle - self.current_angle) * stiff
        else:
            self.current_angle = 0.0

        # 5. Velocity Squash & Stretch
        dist_x = target_x - self.rendered_x
        dist_y = target_y - self.rendered_y
        speed = math.sqrt(dist_x * dist_x + dist_y * dist_y)

        if self.config.velocity_stretch and speed > 1.0:
            target_stretch = 1.0 + min(0.18 * self.config.stretch_intensity, speed * 0.0035 * self.config.stretch_intensity)
            target_squash = 1.0 / math.sqrt(target_stretch)
        else:
            target_stretch = 1.0
            target_squash = 1.0

        self.current_stretch += (target_stretch - self.current_stretch) * 0.22
        self.current_squash += (target_squash - self.current_squash) * 0.22

        # 6. Screen Studio Click Bounce Spring Physics
        if self.config.click_bounce_enabled:
            if self.bridge.is_pressed:
                desired_scale = self.config.drag_scale if self.config.drag_compression_enabled else self.config.press_scale
            else:
                desired_scale = 1.0

            stiffness = self.config.bounce_speed
            damping = 22.0
            accel = stiffness * (desired_scale - self.current_scale) - damping * self.scale_velocity
            self.scale_velocity += accel * dt
            self.current_scale += self.scale_velocity * dt
            if not self.bridge.is_pressed and self.current_scale > self.config.release_overshoot:
                self.current_scale = self.config.release_overshoot
        else:
            self.current_scale = 1.0

        # 7. Update Motion Trail History
        if self.config.motion_trail_enabled:
            cur_asset = self.active_custom_asset or self.extractor.get_asset(self.active_shape)
            self.history_positions.append((
                self.rendered_x, self.rendered_y, cur_asset,
                self.config.cursor_scale * self.current_scale,
                self.current_squash, self.current_stretch, self.current_angle
            ))
            if len(self.history_positions) > 15:
                self.history_positions.pop(0)
        else:
            self.history_positions.clear()

        # 8. Update Ripples
        alive_ripples = []
        for r in self.ripples:
            r['radius'] += 38.0 * dt * 3.2
            r['alpha'] -= 195.0 * dt * 2.6
            if r['alpha'] > 0 and r['radius'] < r['max_radius']:
                alive_ripples.append(r)
        self.ripples = alive_ripples

        self.prev_target_x = target_x
        self.prev_target_y = target_y
        self.update()

    def paintEvent(self, event):
        if not self.config.master_enabled:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        local_x = self.rendered_x - self.vx
        local_y = self.rendered_y - self.vy
        anim_time = time.time() - self.start_time

        # 1. Screen Spotlight Mode (Presentation / Recording)
        if self.config.spotlight_enabled:
            spot_r = self.config.spotlight_radius
            darkness = int(self.config.spotlight_darkness * 255)
            grad = QRadialGradient(local_x, local_y, spot_r)
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            feather_pos = max(0.0, min(0.95, 1.0 - (self.config.spotlight_feather / spot_r)))
            grad.setColorAt(feather_pos, QColor(0, 0, 0, 0))
            grad.setColorAt(1.0, QColor(0, 0, 0, darkness))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRect(self.rect())

        # 2. Cursor Halo / Glow
        if self.config.halo_enabled:
            h_col = QColor(self.config.halo_color)
            h_r = self.config.halo_radius
            h_alpha = int(self.config.halo_opacity * 255)
            grad = QRadialGradient(local_x, local_y, h_r)
            grad.setColorAt(0.0, QColor(h_col.red(), h_col.green(), h_col.blue(), h_alpha))
            grad.setColorAt(0.65, QColor(h_col.red(), h_col.green(), h_col.blue(), int(h_alpha * 0.45)))
            grad.setColorAt(1.0, QColor(h_col.red(), h_col.green(), h_col.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPointF(local_x, local_y), h_r, h_r)

        # 3. Active Ripples
        for r in self.ripples:
            rx = r['x'] - self.vx
            ry = r['y'] - self.vy
            rad = r['radius']
            alpha = max(0, min(255, int(r['alpha'])))
            rc = r['color']

            if r.get('style') == "Filled Pulse":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(rc.red(), rc.green(), rc.blue(), int(alpha * 0.35))))
                painter.drawEllipse(QPointF(rx, ry), rad, rad)
                painter.setPen(QPen(QColor(rc.red(), rc.green(), rc.blue(), alpha), 1.6))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(rx, ry), rad, rad)
            elif r.get('style') == "Dual Wave":
                painter.setPen(QPen(QColor(rc.red(), rc.green(), rc.blue(), alpha), 2.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(rx, ry), rad, rad)
                if rad > 12:
                    inner_rad = rad * 0.65
                    inner_alpha = int(alpha * 0.75)
                    painter.setPen(QPen(QColor(rc.red(), rc.green(), rc.blue(), inner_alpha), 1.5))
                    painter.drawEllipse(QPointF(rx, ry), inner_rad, inner_rad)
            else:
                painter.setPen(QPen(QColor(rc.red(), rc.green(), rc.blue(), alpha), 2.2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(rx, ry), rad, rad)

        # 4. Motion Trails
        if self.config.motion_trail_enabled and len(self.history_positions) > 1:
            num_ghosts = min(self.config.trail_length, len(self.history_positions))
            for i in range(num_ghosts):
                idx = len(self.history_positions) - 1 - i
                gx, gy, g_asset, g_scale, g_sq, g_st, g_rot = self.history_positions[idx]
                ghost_ratio = (num_ghosts - i) / (num_ghosts + 1.0)
                ghost_alpha = self.config.trail_opacity * ghost_ratio
                if ghost_alpha > 0.03 and g_asset:
                    painter.save()
                    painter.setOpacity(ghost_alpha)
                    render_extracted_cursor(
                        painter, g_asset, gx - self.vx, gy - self.vy,
                        g_scale, g_sq, g_st, g_rot, anim_time
                    )
                    painter.restore()

        # 5. Render Scaled Cursor
        final_scale = self.config.cursor_scale * self.current_scale
        active_asset = self.active_custom_asset or self.extractor.get_asset(self.active_shape)
        if not active_asset:
            active_asset = self.extractor.get_asset("ARROW")

        if self.morph_progress >= 0.99 or not self.prev_shape:
            render_extracted_cursor(
                painter, active_asset, local_x, local_y,
                final_scale, self.current_squash, self.current_stretch, self.current_angle, anim_time
            )
        else:
            t = self.morph_progress
            ease = t * t * (3.0 - 2.0 * t)

            prev_alpha = 1.0 - ease
            if prev_alpha > 0.02:
                painter.save()
                painter.setOpacity(prev_alpha)
                prev_asset = self.prev_custom_asset or self.extractor.get_asset(self.prev_shape)
                if not prev_asset:
                    prev_asset = self.extractor.get_asset("ARROW")
                render_extracted_cursor(
                    painter, prev_asset, local_x, local_y,
                    final_scale * (1.0 - 0.12 * ease), self.current_squash, self.current_stretch, self.current_angle, anim_time
                )
                painter.restore()

            painter.save()
            painter.setOpacity(ease)
            render_extracted_cursor(
                painter, active_asset, local_x, local_y,
                final_scale * (0.88 + 0.12 * ease), self.current_squash, self.current_stretch, self.current_angle, anim_time
            )
            painter.restore()
