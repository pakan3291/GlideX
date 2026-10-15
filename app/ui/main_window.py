"""
Modern Settings Dashboard Window
================================
Sleek dark-themed desktop application with 240px Left Sidebar, categorized
navigation, interactive preview card, visual cursor gallery, and presets.
"""

import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSlider,
    QCheckBox,
    QPushButton,
    QFrame,
    QStackedWidget,
    QScrollArea,
    QColorDialog,
    QFileDialog,
    QComboBox,
    QButtonGroup
)

from app.config import AppConfig, set_start_with_windows, is_start_with_windows, get_cursors_dir, get_app_icon
from app.core.win32_api import SystemCursorManager, SYSTEM_CURSOR_DEFINITIONS
from app.core.cursor_manager import WindowsCursorExtractor
from app.core.input_hook import SoundSynthesizer
from app.ui.styles import DARK_THEME_QSS, TestAreaWidget


class ModernDashboardWindow(QMainWindow):
    """
    Sleek modern dark-themed desktop application with a 240px Left Sidebar,
    6 categorized pages, live visual cursor gallery, and presets manager.
    """

    def __init__(self, config: AppConfig, cursor_mgr: SystemCursorManager, sound_synth: SoundSynthesizer, extractor: WindowsCursorExtractor):
        super().__init__()
        self.config = config
        self.cursor_mgr = cursor_mgr
        self.sound = sound_synth
        self.extractor = extractor

        self.setWindowTitle("GlideX - Real-Time Cursor Physics & Studio")
        self.setWindowIcon(get_app_icon())
        self.resize(1020, 720)
        self.setMinimumSize(920, 640)

        self.setStyleSheet(DARK_THEME_QSS)
        self._init_layout()

    def _init_layout(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------------------------------------------------------
        # Left Sidebar (240px width)
        # ---------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 18, 14, 18)
        sidebar_layout.setSpacing(6)

        # App Brand Header
        header_row = QHBoxLayout()
        logo_icon = QLabel("✨")
        logo_icon.setFont(QFont("Segoe UI Emoji", 18))
        header_row.addWidget(logo_icon)

        title_col = QVBoxLayout()
        title_lbl = QLabel("GlideX")
        title_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        sub_lbl = QLabel("STUDIO PRO 2.0")
        sub_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        sub_lbl.setStyleSheet("color: #6366F1; letter-spacing: 1px;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        header_row.addLayout(title_col)
        header_row.addStretch()
        sidebar_layout.addLayout(header_row)

        sidebar_layout.addSpacing(16)

        # Nav Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("🏠  General & Size", "عمومی و اندازه", 0),
            ("🌊  Smoothness & Physics", "حرکت نرم و فیزیک", 1),
            ("👆  Click & Drag Effects", "انیمیشنهای کلیک و درگ", 2),
            ("🔦  Spotlight & Halo", "هایلایت و تمرکز", 3),
            ("🖱️  Cursor Gallery", "مدیریت آیکونهای کرسر", 4),
            ("💾  Presets & Shortcuts", "پروفایلها و کلیدها", 5)
        ]

        self.nav_buttons = []
        for en_title, fa_title, idx in nav_items:
            btn = QPushButton(f"{en_title}\n   {fa_title}")
            btn.setObjectName("NavBtn")
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, i=idx: self.stack.setCurrentIndex(i))
            self.nav_group.addButton(btn, idx)
            self.nav_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Master Toggle Card at bottom of sidebar
        master_card = QFrame()
        master_card.setStyleSheet("background: #181822; border: 1px solid #282838; border-radius: 10px; padding: 10px;")
        lay_master = QVBoxLayout(master_card)
        lay_master.setSpacing(8)

        lbl_engine_title = QLabel("Custom Cursor Engine")
        lbl_engine_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_engine_title.setStyleSheet("color: #FFFFFF;")
        lay_master.addWidget(lbl_engine_title)

        self.chk_master = QCheckBox("Master Overlay Active")
        self.chk_master.setChecked(self.config.master_enabled)
        self.chk_master.toggled.connect(self._on_master_toggled)
        lay_master.addWidget(self.chk_master)

        emergency_badge = QLabel("Emergency Hotkey: Ctrl+Shift+Q")
        emergency_badge.setStyleSheet("color: #8C8CA0; font-size: 10px;")
        lay_master.addWidget(emergency_badge)

        sidebar_layout.addWidget(master_card)
        root.addWidget(sidebar)

        # ---------------------------------------------------------
        # Main Content Area (Stacked Widget)
        # ---------------------------------------------------------
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_page_general())
        self.stack.addWidget(self._create_page_physics())
        self.stack.addWidget(self._create_page_click())
        self.stack.addWidget(self._create_page_spotlight())
        self.stack.addWidget(self._create_page_gallery())
        self.stack.addWidget(self._create_page_presets())
        root.addWidget(self.stack)

    # ------------------------------------------------------------------------
    # Page 1: General & Size
    # ------------------------------------------------------------------------
    def _create_page_general(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)

        h_title = QLabel("General & Size (عمومی و اندازه)")
        h_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        h_title.setStyleSheet("color: #FFFFFF;")
        lay.addWidget(h_title)

        h_sub = QLabel("Configure master engine switches, baseline cursor scale, and test interactive responses.")
        h_sub.setStyleSheet("color: #9090A8; font-size: 12px; margin-bottom: 4px;")
        lay.addWidget(h_sub)

        # Card: Size Slider
        card_scale = QFrame()
        card_scale.setObjectName("Card")
        lay_scale = QVBoxLayout(card_scale)
        lay_scale.setSpacing(12)

        scale_row = QHBoxLayout()
        scale_title = QLabel("Cursor Base Scale Multiplier:")
        scale_title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.lbl_scale_val = QLabel(f"{self.config.cursor_scale:.1f}x")
        self.lbl_scale_val.setStyleSheet("color: #6366F1; font-weight: bold; font-size: 14px;")
        btn_reset_scale = QPushButton("Reset (1.0x)")
        btn_reset_scale.setObjectName("ActionBtn")
        btn_reset_scale.clicked.connect(lambda: self.slider_scale.setValue(10))

        scale_row.addWidget(scale_title)
        scale_row.addStretch()
        scale_row.addWidget(self.lbl_scale_val)
        scale_row.addWidget(btn_reset_scale)
        lay_scale.addLayout(scale_row)

        self.slider_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_scale.setRange(8, 40)
        self.slider_scale.setValue(int(self.config.cursor_scale * 10))
        self.slider_scale.valueChanged.connect(self._on_scale_changed)
        lay_scale.addWidget(self.slider_scale)

        desc_scale = QLabel("Scales all 17 Windows cursors proportionally using normalized visual height.")
        desc_scale.setStyleSheet("color: #808098; font-size: 11px;")
        lay_scale.addWidget(desc_scale)
        lay.addWidget(card_scale)

        # Card: System Integration & Hardware Hiding
        card_sys = QFrame()
        card_sys.setObjectName("Card")
        lay_sys = QVBoxLayout(card_sys)
        lay_sys.setSpacing(12)

        self.chk_hide_native = QCheckBox("Hide Native Windows Cursor Globally (MagShowSystemCursor)")
        self.chk_hide_native.setChecked(self.config.hide_native_cursor)
        self.chk_hide_native.toggled.connect(self._on_toggle_hide_native)
        lay_sys.addWidget(self.chk_hide_native)

        self.chk_startup = QCheckBox("Start GlideX automatically with Windows")
        self.chk_startup.setChecked(is_start_with_windows())
        self.chk_startup.toggled.connect(self._on_toggle_startup)
        lay_sys.addWidget(self.chk_startup)

        btn_failsafe = QPushButton("🚨 Emergency Restore System Cursors (Ctrl+Shift+Q)")
        btn_failsafe.setObjectName("DangerBtn")
        btn_failsafe.clicked.connect(self._emergency_restore_action)
        lay_sys.addWidget(btn_failsafe)

        lay.addWidget(card_sys)

        # Card: Interactive Test Area
        card_test = QFrame()
        card_test.setObjectName("Card")
        lay_test = QVBoxLayout(card_test)
        lay_test.setSpacing(10)

        test_title = QLabel("Live Interactive Preview Card (آزمایش زنده)")
        test_title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        lay_test.addWidget(test_title)

        test_sub = QLabel("Hover across zones to test Pointer, Text, Grab/Drag Fist, and Animated Busy cursor.")
        test_sub.setStyleSheet("color: #8C8CA0; font-size: 11px;")
        lay_test.addWidget(test_sub)

        self.test_area = TestAreaWidget(self.config, self.sound, self.extractor)
        lay_test.addWidget(self.test_area)
        lay.addWidget(card_test)

        lay.addStretch()
        scroll.setWidget(content)
        return scroll

    # ------------------------------------------------------------------------
    # Page 2: Smoothness & Physics
    # ------------------------------------------------------------------------
    def _create_page_physics(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)

        h_title = QLabel("Smoothness & Physics (حرکت نرم و فیزیک)")
        h_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        h_title.setStyleSheet("color: #FFFFFF;")
        lay.addWidget(h_title)

        h_sub = QLabel("Customize cinematic interpolation, directional banking angles, and velocity stretch.")
        h_sub.setStyleSheet("color: #9090A8; font-size: 12px; margin-bottom: 4px;")
        lay.addWidget(h_sub)

        # Card: Smoothing Factor
        card_smooth = QFrame()
        card_smooth.setObjectName("Card")
        lay_smooth = QVBoxLayout(card_smooth)
        lay_smooth.setSpacing(10)

        smooth_row = QHBoxLayout()
        smooth_title = QLabel("Movement Smoothing / Glide Factor:")
        smooth_title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.lbl_smooth_val = QLabel("Balanced")
        self.lbl_smooth_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        smooth_row.addWidget(smooth_title)
        smooth_row.addStretch()
        smooth_row.addWidget(self.lbl_smooth_val)
        lay_smooth.addLayout(smooth_row)

        self.slider_smooth = QSlider(Qt.Orientation.Horizontal)
        self.slider_smooth.setRange(8, 100)
        self.slider_smooth.setValue(int(self.config.smoothing_factor * 100))
        self.slider_smooth.valueChanged.connect(self._on_smooth_changed)
        lay_smooth.addWidget(self.slider_smooth)
        self._update_smooth_label(self.config.smoothing_factor)
        lay.addWidget(card_smooth)

        # Card: Directional Tilt / Banking Angle
        card_tilt = QFrame()
        card_tilt.setObjectName("Card")
        lay_tilt = QVBoxLayout(card_tilt)
        lay_tilt.setSpacing(12)

        self.chk_tilt = QCheckBox("Enable Directional Banking / Tilt Angle")
        self.chk_tilt.setChecked(self.config.tilt_enabled)
        self.chk_tilt.toggled.connect(lambda v: self._update_cfg('tilt_enabled', v))
        lay_tilt.addWidget(self.chk_tilt)

        tilt_row = QHBoxLayout()
        tilt_row.addWidget(QLabel("Max Tilt Angle:"))
        self.lbl_tilt_val = QLabel(f"{int(self.config.tilt_max_angle)}°")
        self.lbl_tilt_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        tilt_row.addStretch()
        tilt_row.addWidget(self.lbl_tilt_val)
        lay_tilt.addLayout(tilt_row)

        self.slider_tilt = QSlider(Qt.Orientation.Horizontal)
        self.slider_tilt.setRange(0, 45)
        self.slider_tilt.setValue(int(self.config.tilt_max_angle))
        self.slider_tilt.valueChanged.connect(self._on_tilt_changed)
        lay_tilt.addWidget(self.slider_tilt)

        stiff_row = QHBoxLayout()
        stiff_row.addWidget(QLabel("Tilt Spring Stiffness (Straighten Speed):"))
        self.lbl_stiff_val = QLabel(f"{self.config.tilt_stiffness:.2f}")
        self.lbl_stiff_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        stiff_row.addStretch()
        stiff_row.addWidget(self.lbl_stiff_val)
        lay_tilt.addLayout(stiff_row)

        self.slider_stiff = QSlider(Qt.Orientation.Horizontal)
        self.slider_stiff.setRange(5, 40)
        self.slider_stiff.setValue(int(self.config.tilt_stiffness * 100))
        self.slider_stiff.valueChanged.connect(lambda v: (
            self._update_cfg('tilt_stiffness', v / 100.0),
            self.lbl_stiff_val.setText(f"{v / 100.0:.2f}")
        ))
        lay_tilt.addWidget(self.slider_stiff)
        lay.addWidget(card_tilt)

        # Card: Velocity Squash & Stretch
        card_stretch = QFrame()
        card_stretch.setObjectName("Card")
        lay_stretch = QVBoxLayout(card_stretch)
        lay_stretch.setSpacing(10)

        self.chk_stretch = QCheckBox("Enable Velocity Squash & Stretch (Elongate on Fast Gestures)")
        self.chk_stretch.setChecked(self.config.velocity_stretch)
        self.chk_stretch.toggled.connect(lambda v: self._update_cfg('velocity_stretch', v))
        lay_stretch.addWidget(self.chk_stretch)

        stretch_row = QHBoxLayout()
        stretch_row.addWidget(QLabel("Stretch Intensity:"))
        self.lbl_stretch_val = QLabel(f"{int(self.config.stretch_intensity * 100)}%")
        self.lbl_stretch_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        stretch_row.addStretch()
        stretch_row.addWidget(self.lbl_stretch_val)
        lay_stretch.addLayout(stretch_row)

        self.slider_stretch = QSlider(Qt.Orientation.Horizontal)
        self.slider_stretch.setRange(20, 200)
        self.slider_stretch.setValue(int(self.config.stretch_intensity * 100))
        self.slider_stretch.valueChanged.connect(lambda v: (
            self._update_cfg('stretch_intensity', v / 100.0),
            self.lbl_stretch_val.setText(f"{v}%")
        ))
        lay_stretch.addWidget(self.slider_stretch)
        lay.addWidget(card_stretch)

        # Card: Motion Trail / Ghosting
        card_trail = QFrame()
        card_trail.setObjectName("Card")
        lay_trail = QVBoxLayout(card_trail)
        lay_trail.setSpacing(10)

        self.chk_trail = QCheckBox("Enable Cinematic Motion Trail / Ghosting Effect")
        self.chk_trail.setChecked(self.config.motion_trail_enabled)
        self.chk_trail.toggled.connect(lambda v: self._update_cfg('motion_trail_enabled', v))
        lay_trail.addWidget(self.chk_trail)

        trail_len_row = QHBoxLayout()
        trail_len_row.addWidget(QLabel("Trail Ghost Frames:"))
        self.lbl_trail_len = QLabel(f"{self.config.trail_length}")
        self.lbl_trail_len.setStyleSheet("color: #6366F1; font-weight: bold;")
        trail_len_row.addStretch()
        trail_len_row.addWidget(self.lbl_trail_len)
        lay_trail.addLayout(trail_len_row)

        self.slider_trail_len = QSlider(Qt.Orientation.Horizontal)
        self.slider_trail_len.setRange(2, 10)
        self.slider_trail_len.setValue(self.config.trail_length)
        self.slider_trail_len.valueChanged.connect(lambda v: (
            self._update_cfg('trail_length', v),
            self.lbl_trail_len.setText(str(v))
        ))
        lay_trail.addWidget(self.slider_trail_len)

        trail_op_row = QHBoxLayout()
        trail_op_row.addWidget(QLabel("Trail Opacity:"))
        self.lbl_trail_op = QLabel(f"{int(self.config.trail_opacity * 100)}%")
        self.lbl_trail_op.setStyleSheet("color: #6366F1; font-weight: bold;")
        trail_op_row.addStretch()
        trail_op_row.addWidget(self.lbl_trail_op)
        lay_trail.addLayout(trail_op_row)

        self.slider_trail_op = QSlider(Qt.Orientation.Horizontal)
        self.slider_trail_op.setRange(10, 70)
        self.slider_trail_op.setValue(int(self.config.trail_opacity * 100))
        self.slider_trail_op.valueChanged.connect(lambda v: (
            self._update_cfg('trail_opacity', v / 100.0),
            self.lbl_trail_op.setText(f"{v}%")
        ))
        lay_trail.addWidget(self.slider_trail_op)
        lay.addWidget(card_trail)

        lay.addStretch()
        scroll.setWidget(content)
        return scroll

    # ------------------------------------------------------------------------
    # Page 3: Click & Drag Effects
    # ------------------------------------------------------------------------
    def _create_page_click(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)

        h_title = QLabel("Click & Drag Effects (انیمیشنهای کلیک و درگ)")
        h_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        h_title.setStyleSheet("color: #FFFFFF;")
        lay.addWidget(h_title)

        h_sub = QLabel("Customize tactile Screen Studio spring bounces, hold compression, ripples, and audio.")
        h_sub.setStyleSheet("color: #9090A8; font-size: 12px; margin-bottom: 4px;")
        lay.addWidget(h_sub)

        # Card: Click Bounce Spring
        card_bounce = QFrame()
        card_bounce.setObjectName("Card")
        lay_bounce = QVBoxLayout(card_bounce)
        lay_bounce.setSpacing(10)

        self.chk_bounce = QCheckBox("Enable Click Bounce / Spring Shrink Effect")
        self.chk_bounce.setChecked(self.config.click_bounce_enabled)
        self.chk_bounce.toggled.connect(lambda v: self._update_cfg('click_bounce_enabled', v))
        lay_bounce.addWidget(self.chk_bounce)

        press_row = QHBoxLayout()
        press_row.addWidget(QLabel("Press Compression Scale:"))
        self.lbl_press_val = QLabel(f"{self.config.press_scale:.2f}x")
        self.lbl_press_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        press_row.addStretch()
        press_row.addWidget(self.lbl_press_val)
        lay_bounce.addLayout(press_row)

        self.slider_press = QSlider(Qt.Orientation.Horizontal)
        self.slider_press.setRange(50, 95)
        self.slider_press.setValue(int(self.config.press_scale * 100))
        self.slider_press.valueChanged.connect(lambda v: (
            self._update_cfg('press_scale', v / 100.0),
            self.lbl_press_val.setText(f"{v / 100.0:.2f}x")
        ))
        lay_bounce.addWidget(self.slider_press)

        over_row = QHBoxLayout()
        over_row.addWidget(QLabel("Release Overshoot Bounce:"))
        self.lbl_over_val = QLabel(f"{self.config.release_overshoot:.2f}x")
        self.lbl_over_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        over_row.addStretch()
        over_row.addWidget(self.lbl_over_val)
        lay_bounce.addLayout(over_row)

        self.slider_over = QSlider(Qt.Orientation.Horizontal)
        self.slider_over.setRange(100, 130)
        self.slider_over.setValue(int(self.config.release_overshoot * 100))
        self.slider_over.valueChanged.connect(lambda v: (
            self._update_cfg('release_overshoot', v / 100.0),
            self.lbl_over_val.setText(f"{v / 100.0:.2f}x")
        ))
        lay_bounce.addWidget(self.slider_over)

        self.chk_drag_comp = QCheckBox("Hold / Drag Compression (Keep cursor compressed while dragging)")
        self.chk_drag_comp.setChecked(self.config.drag_compression_enabled)
        self.chk_drag_comp.toggled.connect(lambda v: self._update_cfg('drag_compression_enabled', v))
        lay_bounce.addWidget(self.chk_drag_comp)
        lay.addWidget(card_bounce)

        # Card: Click Ripple / Shockwave
        card_ripple = QFrame()
        card_ripple.setObjectName("Card")
        lay_ripple = QVBoxLayout(card_ripple)
        lay_ripple.setSpacing(10)

        self.chk_ripple = QCheckBox("Enable Click Ripple / Shockwave Ring")
        self.chk_ripple.setChecked(self.config.ripple_enabled)
        self.chk_ripple.toggled.connect(lambda v: self._update_cfg('ripple_enabled', v))
        lay_ripple.addWidget(self.chk_ripple)

        style_row = QHBoxLayout()
        style_row.addWidget(QLabel("Ripple Style:"))
        self.cmb_ripple_style = QComboBox()
        self.cmb_ripple_style.addItems(["Ring", "Filled Pulse", "Dual Wave"])
        self.cmb_ripple_style.setCurrentText(self.config.ripple_style)
        self.cmb_ripple_style.currentTextChanged.connect(lambda s: self._update_cfg('ripple_style', s))
        style_row.addWidget(self.cmb_ripple_style)
        style_row.addStretch()

        self.btn_ripple_color = QPushButton("Pick Color")
        self.btn_ripple_color.setObjectName("ActionBtn")
        self.btn_ripple_color.setStyleSheet(f"border-left: 12px solid {self.config.ripple_color};")
        self.btn_ripple_color.clicked.connect(self._pick_ripple_color)
        style_row.addWidget(self.btn_ripple_color)
        lay_ripple.addLayout(style_row)

        rsize_row = QHBoxLayout()
        rsize_row.addWidget(QLabel("Ripple Max Radius:"))
        self.lbl_rsize_val = QLabel(f"{int(self.config.ripple_size)}px")
        self.lbl_rsize_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        rsize_row.addStretch()
        rsize_row.addWidget(self.lbl_rsize_val)
        lay_ripple.addLayout(rsize_row)

        self.slider_rsize = QSlider(Qt.Orientation.Horizontal)
        self.slider_rsize.setRange(20, 80)
        self.slider_rsize.setValue(int(self.config.ripple_size))
        self.slider_rsize.valueChanged.connect(lambda v: (
            self._update_cfg('ripple_size', float(v)),
            self.lbl_rsize_val.setText(f"{v}px")
        ))
        lay_ripple.addWidget(self.slider_rsize)
        lay.addWidget(card_ripple)

        # Card: Click Audio Effects
        card_audio = QFrame()
        card_audio.setObjectName("Card")
        lay_audio = QVBoxLayout(card_audio)
        lay_audio.setSpacing(10)

        self.chk_sound = QCheckBox("Enable Click Sound Effects (Synthesized In-Memory Audio)")
        self.chk_sound.setChecked(self.config.sound_enabled)
        self.chk_sound.toggled.connect(lambda v: self._update_cfg('sound_enabled', v))
        lay_audio.addWidget(self.chk_sound)

        sound_row = QHBoxLayout()
        sound_row.addWidget(QLabel("Sound Style:"))
        self.cmb_sound_style = QComboBox()
        self.cmb_sound_style.addItems(["Soft Pop", "Mechanical Switch", "macOS Tap"])
        self.cmb_sound_style.setCurrentText(self.config.sound_style)
        self.cmb_sound_style.currentTextChanged.connect(lambda s: self._update_cfg('sound_style', s))
        sound_row.addWidget(self.cmb_sound_style)
        sound_row.addStretch()

        btn_test_sound = QPushButton("🔊 Test Sound")
        btn_test_sound.setObjectName("ActionBtn")
        btn_test_sound.clicked.connect(lambda: self.sound.play_click(self.config.sound_style, self.config.sound_volume))
        sound_row.addWidget(btn_test_sound)
        lay_audio.addLayout(sound_row)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Volume:"))
        self.lbl_vol_val = QLabel(f"{int(self.config.sound_volume * 100)}%")
        self.lbl_vol_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        vol_row.addStretch()
        vol_row.addWidget(self.lbl_vol_val)
        lay_audio.addLayout(vol_row)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(int(self.config.sound_volume * 100))
        self.slider_vol.valueChanged.connect(lambda v: (
            self._update_cfg('sound_volume', v / 100.0),
            self.lbl_vol_val.setText(f"{v}%")
        ))
        lay_audio.addWidget(self.slider_vol)
        lay.addWidget(card_audio)

        lay.addStretch()
        scroll.setWidget(content)
        return scroll

    # ------------------------------------------------------------------------
    # Page 4: Spotlight & Halo
    # ------------------------------------------------------------------------
    def _create_page_spotlight(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)

        h_title = QLabel("Spotlight & Halo (هایلایت و تمرکز)")
        h_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        h_title.setStyleSheet("color: #FFFFFF;")
        lay.addWidget(h_title)

        h_sub = QLabel("Enhance visibility during screen recordings, tutorials, and presentations.")
        h_sub.setStyleSheet("color: #9090A8; font-size: 12px; margin-bottom: 4px;")
        lay.addWidget(h_sub)

        # Card: Cursor Halo / Glow
        card_halo = QFrame()
        card_halo.setObjectName("Card")
        lay_halo = QVBoxLayout(card_halo)
        lay_halo.setSpacing(10)

        self.chk_halo = QCheckBox("Enable Cursor Halo / Glow Behind Pointer")
        self.chk_halo.setChecked(self.config.halo_enabled)
        self.chk_halo.toggled.connect(lambda v: self._update_cfg('halo_enabled', v))
        lay_halo.addWidget(self.chk_halo)

        hcol_row = QHBoxLayout()
        hcol_row.addWidget(QLabel("Halo Color:"))
        self.btn_halo_color = QPushButton("Pick Color")
        self.btn_halo_color.setObjectName("ActionBtn")
        self.btn_halo_color.setStyleSheet(f"border-left: 12px solid {self.config.halo_color};")
        self.btn_halo_color.clicked.connect(self._pick_halo_color)
        hcol_row.addWidget(self.btn_halo_color)
        hcol_row.addStretch()
        lay_halo.addLayout(hcol_row)

        hr_row = QHBoxLayout()
        hr_row.addWidget(QLabel("Halo Radius:"))
        self.lbl_hr_val = QLabel(f"{int(self.config.halo_radius)}px")
        self.lbl_hr_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        hr_row.addStretch()
        hr_row.addWidget(self.lbl_hr_val)
        lay_halo.addLayout(hr_row)

        self.slider_hr = QSlider(Qt.Orientation.Horizontal)
        self.slider_hr.setRange(20, 80)
        self.slider_hr.setValue(int(self.config.halo_radius))
        self.slider_hr.valueChanged.connect(lambda v: (
            self._update_cfg('halo_radius', float(v)),
            self.lbl_hr_val.setText(f"{v}px")
        ))
        lay_halo.addWidget(self.slider_hr)

        hop_row = QHBoxLayout()
        hop_row.addWidget(QLabel("Halo Opacity:"))
        self.lbl_hop_val = QLabel(f"{int(self.config.halo_opacity * 100)}%")
        self.lbl_hop_val.setStyleSheet("color: #6366F1; font-weight: bold;")
        hop_row.addStretch()
        hop_row.addWidget(self.lbl_hop_val)
        lay_halo.addLayout(hop_row)

        self.slider_hop = QSlider(Qt.Orientation.Horizontal)
        self.slider_hop.setRange(5, 70)
        self.slider_hop.setValue(int(self.config.halo_opacity * 100))
        self.slider_hop.valueChanged.connect(lambda v: (
            self._update_cfg('halo_opacity', v / 100.0),
            self.lbl_hop_val.setText(f"{v}%")
        ))
        lay_halo.addWidget(self.slider_hop)
        lay.addWidget(card_halo)

        # Card: Screen Spotlight Presentation Mode
        card_spot = QFrame()
        card_spot.setObjectName("Card")
        lay_spot = QVBoxLayout(card_spot)
        lay_spot.setSpacing(10)

        self.chk_spot = QCheckBox("Enable Screen Spotlight Mode (Toggle with Ctrl+Shift+F)")
        self.chk_spot.setChecked(self.config.spotlight_enabled)
        self.chk_spot.toggled.connect(lambda v: self._update_cfg('spotlight_enabled', v))
        lay_spot.addWidget(self.chk_spot)

        spot_r_row = QHBoxLayout()
        spot_r_row.addWidget(QLabel("Spotlight Aperture Radius:"))
        self.lbl_spot_r = QLabel(f"{int(self.config.spotlight_radius)}px")
        self.lbl_spot_r.setStyleSheet("color: #6366F1; font-weight: bold;")
        spot_r_row.addStretch()
        spot_r_row.addWidget(self.lbl_spot_r)
        lay_spot.addLayout(spot_r_row)

        self.slider_spot_r = QSlider(Qt.Orientation.Horizontal)
        self.slider_spot_r.setRange(80, 350)
        self.slider_spot_r.setValue(int(self.config.spotlight_radius))
        self.slider_spot_r.valueChanged.connect(lambda v: (
            self._update_cfg('spotlight_radius', float(v)),
            self.lbl_spot_r.setText(f"{v}px")
        ))
        lay_spot.addWidget(self.slider_spot_r)

        spot_dark_row = QHBoxLayout()
        spot_dark_row.addWidget(QLabel("Screen Dim Darkness:"))
        self.lbl_spot_dark = QLabel(f"{int(self.config.spotlight_darkness * 100)}%")
        self.lbl_spot_dark.setStyleSheet("color: #6366F1; font-weight: bold;")
        spot_dark_row.addStretch()
        spot_dark_row.addWidget(self.lbl_spot_dark)
        lay_spot.addLayout(spot_dark_row)

        self.slider_spot_dark = QSlider(Qt.Orientation.Horizontal)
        self.slider_spot_dark.setRange(10, 80)
        self.slider_spot_dark.setValue(int(self.config.spotlight_darkness * 100))
        self.slider_spot_dark.valueChanged.connect(lambda v: (
            self._update_cfg('spotlight_darkness', v / 100.0),
            self.lbl_spot_dark.setText(f"{v}%")
        ))
        lay_spot.addWidget(self.slider_spot_dark)
        lay.addWidget(card_spot)

        lay.addStretch()
        scroll.setWidget(content)
        return scroll

    # ------------------------------------------------------------------------
    # Page 5: Cursor Gallery & Manager (All 17 Windows Cursors + Grab/Grabbing)
    # ------------------------------------------------------------------------
    def _create_page_gallery(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        h_title = QLabel("Cursor Gallery & Manager (مدیریت آیکونهای کرسر)")
        h_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        h_title.setStyleSheet("color: #FFFFFF;")
        self.lbl_gallery_scheme = QLabel(f"Active Scheme: {self.extractor.scheme_name} ({len(self.extractor.assets)} loaded)")
        self.lbl_gallery_scheme.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 500;")
        title_col.addWidget(h_title)
        title_col.addWidget(self.lbl_gallery_scheme)
        header_row.addLayout(title_col)
        header_row.addStretch()

        btn_reload = QPushButton("🔄 Reload Windows Scheme")
        btn_reload.setObjectName("ActionBtn")
        btn_reload.clicked.connect(self._reload_scheme_action)
        header_row.addWidget(btn_reload)

        btn_open_dir = QPushButton("📁 Cursors Folder")
        btn_open_dir.setObjectName("ActionBtn")
        btn_open_dir.clicked.connect(self._open_cursors_folder)
        header_row.addWidget(btn_open_dir)

        lay.addLayout(header_row)

        grid = QGridLayout()
        grid.setSpacing(12)

        row = 0
        col = 0
        for reg_name, shape_key, ocr_id, disp_en, disp_fa in SYSTEM_CURSOR_DEFINITIONS:
            card = self._create_cursor_item_card(shape_key, disp_en, disp_fa)
            grid.addWidget(card, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1

        lay.addLayout(grid)
        lay.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_cursor_item_card(self, shape_key: str, disp_en: str, disp_fa: str) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(14)

        asset = self.extractor.get_asset(shape_key)

        preview_box = QLabel()
        preview_box.setFixedSize(54, 54)
        preview_box.setStyleSheet("background-color: #13131C; border: 1px solid #2C2C3E; border-radius: 8px;")
        preview_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if asset and asset.pixmap and not asset.pixmap.isNull():
            pm = asset.pixmap.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            preview_box.setPixmap(pm)
        lay.addWidget(preview_box)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        title_lbl = QLabel(f"{disp_en} ({disp_fa})")
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        info_col.addWidget(title_lbl)

        frame_count = len(asset.frames) if (asset and asset.frames) else 1
        frame_text = f" • ⚡ {frame_count} Frames (.ani)" if frame_count > 1 else ""
        hot_str = f"Hotspot: ({asset.hotspot_x:.0f}, {asset.hotspot_y:.0f}){frame_text}" if asset else "Default"
        sub_lbl = QLabel(hot_str)
        sub_lbl.setStyleSheet("color: #8E8EA8; font-size: 11px;")
        info_col.addWidget(sub_lbl)

        lay.addLayout(info_col)
        lay.addStretch()

        btn_custom = QPushButton("Custom...")
        btn_custom.setObjectName("ActionBtn")
        btn_custom.clicked.connect(lambda _, sk=shape_key: self._choose_custom_cursor(sk))
        lay.addWidget(btn_custom)

        return card

    def _choose_custom_cursor(self, shape_key: str):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Choose Cursor for {shape_key}", "",
            "Cursor / Image Files (*.cur *.ani *.png *.ico);;All Files (*.*)"
        )
        if path and os.path.exists(path):
            if shape_key not in self.config.per_cursor_overrides:
                self.config.per_cursor_overrides[shape_key] = {}
            self.config.per_cursor_overrides[shape_key]["custom_path"] = path
            self.config.save_to_file()
            self.extractor.reload_all()
            self._refresh_gallery()

    def _refresh_gallery(self):
        old_widget = self.stack.widget(4)
        new_widget = self._create_page_gallery()
        self.stack.removeWidget(old_widget)
        self.stack.insertWidget(4, new_widget)
        self.stack.setCurrentIndex(4)

    # ------------------------------------------------------------------------
    # Page 6: Presets & Shortcuts
    # ------------------------------------------------------------------------
    def _create_page_presets(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)

        h_title = QLabel("Presets & Shortcuts (پروفایلها و کلیدهای میانبر)")
        h_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        h_title.setStyleSheet("color: #FFFFFF;")
        lay.addWidget(h_title)

        h_sub = QLabel("One-click professional presets, auto-persistence status, and hotkey configurations.")
        h_sub.setStyleSheet("color: #9090A8; font-size: 12px; margin-bottom: 4px;")
        lay.addWidget(h_sub)

        presets_grid = QGridLayout()
        presets_grid.setSpacing(14)

        presets = [
            ("🎬 Screen Studio (Cinematic)", "Scale 1.8x, Ultra-Smooth Glide (0.35), Tilt 24°, Dual Wave Ripple, Soft Pop Audio", "screen_studio"),
            ("⚡ Zero-Lag Gaming / Work", "Scale 1.1x, Instant Smoothing (1.0), Physics OFF for zero latency & maximum FPS", "zero_lag"),
            ("🍎 Subtle macOS", "Scale 1.4x, Balanced Glide (0.60), Subtle Tilt 12°, Classic Ring, macOS Tap Audio", "subtle_macos"),
            ("🎓 Tutorial / Presentation", "Scale 2.2x, Tilt 25°, Filled Pulse Ripple, Cursor Halo ON, Spotlight Ready", "presentation")
        ]

        row = 0
        col = 0
        for p_title, p_desc, p_id in presets:
            card = QFrame()
            card.setObjectName("Card")
            c_lay = QVBoxLayout(card)
            c_lay.setSpacing(8)

            t_lbl = QLabel(p_title)
            t_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            t_lbl.setStyleSheet("color: #FFFFFF;")
            c_lay.addWidget(t_lbl)

            d_lbl = QLabel(p_desc)
            d_lbl.setStyleSheet("color: #8C8CA4; font-size: 11px;")
            d_lbl.setWordWrap(True)
            c_lay.addWidget(d_lbl)

            btn_apply = QPushButton("Apply Preset")
            btn_apply.setObjectName("PrimaryBtn")
            btn_apply.clicked.connect(lambda _, pid=p_id: self._apply_preset(pid))
            c_lay.addWidget(btn_apply)

            presets_grid.addWidget(card, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1

        lay.addLayout(presets_grid)

        card_hotkeys = QFrame()
        card_hotkeys.setObjectName("Card")
        lay_hk = QVBoxLayout(card_hotkeys)
        lay_hk.setSpacing(10)

        hk_title = QLabel("Configured Global Hotkeys")
        hk_title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        lay_hk.addWidget(hk_title)

        hk_list = [
            ("Ctrl + Shift + Q", "Emergency Failsafe (Instantly restores native Windows cursors)"),
            ("Ctrl + Shift + S", "Toggle Custom Cursor Overlay On / Off"),
            ("Ctrl + Shift + F", "Toggle Screen Spotlight Presentation Mode")
        ]
        for key, desc in hk_list:
            r = QHBoxLayout()
            k_badge = QLabel(f" {key} ")
            k_badge.setStyleSheet("background: #2D2D42; color: #ECECF2; border-radius: 4px; font-weight: bold; font-size: 11px;")
            r.addWidget(k_badge)
            r.addWidget(QLabel(desc))
            r.addStretch()
            lay_hk.addLayout(r)

        lay.addWidget(card_hotkeys)

        lay.addStretch()
        scroll.setWidget(content)
        return scroll

    # ------------------------------------------------------------------------
    # Control Actions & Presets
    # ------------------------------------------------------------------------
    def _apply_preset(self, preset_id: str):
        if preset_id == "screen_studio":
            self.config.cursor_scale = 1.8
            self.config.smoothing_factor = 0.35
            self.config.tilt_enabled = True
            self.config.tilt_max_angle = 24.0
            self.config.velocity_stretch = True
            self.config.click_bounce_enabled = True
            self.config.press_scale = 0.78
            self.config.release_overshoot = 1.14
            self.config.ripple_enabled = True
            self.config.ripple_style = "Dual Wave"
            self.config.sound_enabled = True
            self.config.sound_style = "Soft Pop"
            self.config.halo_enabled = True
            self.config.halo_opacity = 0.22
        elif preset_id == "zero_lag":
            self.config.cursor_scale = 1.1
            self.config.smoothing_factor = 1.0
            self.config.tilt_enabled = False
            self.config.velocity_stretch = False
            self.config.click_bounce_enabled = False
            self.config.ripple_enabled = False
            self.config.sound_enabled = False
            self.config.halo_enabled = False
            self.config.motion_trail_enabled = False
        elif preset_id == "subtle_macos":
            self.config.cursor_scale = 1.4
            self.config.smoothing_factor = 0.60
            self.config.tilt_enabled = True
            self.config.tilt_max_angle = 14.0
            self.config.velocity_stretch = True
            self.config.click_bounce_enabled = True
            self.config.press_scale = 0.82
            self.config.release_overshoot = 1.08
            self.config.ripple_enabled = True
            self.config.ripple_style = "Ring"
            self.config.sound_enabled = True
            self.config.sound_style = "macOS Tap"
            self.config.halo_enabled = False
        elif preset_id == "presentation":
            self.config.cursor_scale = 2.2
            self.config.smoothing_factor = 0.40
            self.config.tilt_enabled = True
            self.config.tilt_max_angle = 25.0
            self.config.velocity_stretch = True
            self.config.click_bounce_enabled = True
            self.config.ripple_enabled = True
            self.config.ripple_style = "Filled Pulse"
            self.config.sound_enabled = True
            self.config.sound_style = "Mechanical Switch"
            self.config.halo_enabled = True
            self.config.halo_opacity = 0.35

        self.config.save_to_file()
        self.slider_scale.setValue(int(self.config.cursor_scale * 10))
        self.slider_smooth.setValue(int(self.config.smoothing_factor * 100))
        self.chk_tilt.setChecked(self.config.tilt_enabled)
        self.chk_stretch.setChecked(self.config.velocity_stretch)
        self.chk_bounce.setChecked(self.config.click_bounce_enabled)
        self.chk_ripple.setChecked(self.config.ripple_enabled)
        self.chk_sound.setChecked(self.config.sound_enabled)
        self.chk_halo.setChecked(self.config.halo_enabled)
        self.cmb_ripple_style.setCurrentText(self.config.ripple_style)
        self.cmb_sound_style.setCurrentText(self.config.sound_style)

    def _update_cfg(self, attr: str, val):
        setattr(self.config, attr, val)
        self.config.save_to_file()

    def _on_scale_changed(self, val):
        self.config.cursor_scale = val / 10.0
        self.lbl_scale_val.setText(f"{self.config.cursor_scale:.1f}x")
        self.config.save_to_file()

    def _on_smooth_changed(self, val):
        factor = val / 100.0
        self.config.smoothing_factor = factor
        self._update_smooth_label(factor)
        self.config.save_to_file()

    def _update_smooth_label(self, factor):
        if factor >= 0.95:
            text = "Zero-Lag (1.0x Instant)"
        elif factor >= 0.65:
            text = "Responsive"
        elif factor >= 0.35:
            text = "Balanced Cinematic"
        else:
            text = "Ultra-Float Cinematic"
        self.lbl_smooth_val.setText(f"{text} ({factor:.2f})")

    def _on_tilt_changed(self, val):
        self.config.tilt_max_angle = float(val)
        self.lbl_tilt_val.setText(f"{val}°")
        self.config.save_to_file()

    def _pick_ripple_color(self):
        col = QColorDialog.getColor(QColor(self.config.ripple_color), self, "Select Ripple Color")
        if col.isValid():
            self.config.ripple_color = col.name()
            self.btn_ripple_color.setStyleSheet(f"border-left: 12px solid {col.name()};")
            self.config.save_to_file()

    def _pick_halo_color(self):
        col = QColorDialog.getColor(QColor(self.config.halo_color), self, "Select Halo Color")
        if col.isValid():
            self.config.halo_color = col.name()
            self.btn_halo_color.setStyleSheet(f"border-left: 12px solid {col.name()};")
            self.config.save_to_file()

    def _on_master_toggled(self, checked: bool):
        self.config.master_enabled = checked
        if checked:
            if self.config.hide_native_cursor:
                self.cursor_mgr.hide()
        else:
            self.cursor_mgr.restore()
        self.config.save_to_file()

    def _on_toggle_hide_native(self, checked: bool):
        self.config.hide_native_cursor = checked
        if checked and self.config.master_enabled:
            self.cursor_mgr.hide()
        else:
            self.cursor_mgr.restore()
        self.config.save_to_file()

    def _on_toggle_startup(self, checked: bool):
        self.config.start_with_windows = checked
        set_start_with_windows(checked)
        self.config.save_to_file()

    def _emergency_restore_action(self):
        self.chk_master.setChecked(False)
        self.chk_hide_native.setChecked(False)
        self.config.master_enabled = False
        self.config.hide_native_cursor = False
        self.cursor_mgr.restore()
        self.config.save_to_file()

    def _reload_scheme_action(self):
        self.extractor.reload_all()
        self._refresh_gallery()

    def _open_cursors_folder(self):
        cursors_dir = get_cursors_dir()
        os.makedirs(cursors_dir, exist_ok=True)
        try:
            os.startfile(cursors_dir)
        except Exception:
            pass

    def closeEvent(self, event):
        event.ignore()
        self.hide()
