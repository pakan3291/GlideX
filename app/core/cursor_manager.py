"""
Cursor Manager & Extraction Engine
==================================
Comprehensive multi-priority cursor extraction (Registry, Win32 OCR, .ANI RIFF
parsing, and high-DPI vector fallbacks), dynamic HCURSOR caching, and shape detection.
"""

import os
import struct
import hashlib
import threading
import winreg
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import ctypes
from ctypes import wintypes

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPainter,
    QPainterPath,
    QColor,
    QPen,
    QBrush,
    QPixmap,
    QImage
)

from app.core.win32_api import (
    user32,
    kernel32,
    gdi32,
    ICONINFO,
    CURSORINFO,
    BITMAPINFOHEADER,
    IMAGE_CURSOR,
    LR_SHARED,
    SYSTEM_CURSOR_DEFINITIONS
)


def measure_image_geometry(qimg: QImage) -> Tuple[int, int, int, int, bool]:
    """
    Measures the non-transparent alpha bounding box of a QImage.
    Returns (min_x, min_y, crop_width, crop_height, has_visible_pixels).
    """
    if qimg.isNull() or qimg.width() == 0 or qimg.height() == 0:
        return 0, 0, 0, 0, False

    w = qimg.width()
    h = qimg.height()
    min_x, max_x = w, -1
    min_y, max_y = h, -1
    vis_count = 0

    for y in range(h):
        for x in range(w):
            alpha = (qimg.pixel(x, y) >> 24) & 0xFF
            if alpha > 15:
                vis_count += 1
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y

    if max_x < min_x or max_y < min_y or vis_count < 10:
        return 0, 0, w, h, False

    return min_x, min_y, (max_x - min_x + 1), (max_y - min_y + 1), True


def compute_pixmap_hash(pm: QPixmap) -> str:
    """Computes a normalized 32x32 bitmap hash for O(1) shape matching."""
    if not pm or pm.isNull():
        return ""
    img = pm.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    scaled = img.scaled(32, 32, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    b = bytes(scaled.constBits())
    return hashlib.md5(b).hexdigest()


@dataclass
class CursorAsset:
    name: str
    pixmap: QPixmap
    hotspot_x: float
    hotspot_y: float
    source_width: float
    source_height: float
    visual_height: float = 24.0
    frames: List[QPixmap] = field(default_factory=list)
    jif_rate: int = 4
    bitmap_hash: str = ""


def create_vector_fallback(shape: str, base_size: int = 128) -> CursorAsset:
    """
    Renders high-DPI modern macOS-styled vector cursors as guaranteed fallback
    when extraction or local files are missing or empty.
    """
    img = QImage(base_size, base_size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    scale = base_size / 32.0
    p.scale(scale, scale)

    hot_x = 0.0
    hot_y = 0.0
    vis_h = 24.0

    path = QPainterPath()
    fill_color = QColor(255, 255, 255)
    stroke_color = QColor(10, 10, 15, 235)
    stroke_width = 1.8

    if shape == "ARROW":
        hot_x, hot_y = 1.0 * scale, 1.0 * scale
        path.moveTo(2.0, 2.0)
        path.lineTo(2.0, 24.0)
        path.lineTo(7.5, 18.5)
        path.lineTo(12.5, 27.5)
        path.lineTo(15.5, 26.0)
        path.lineTo(10.5, 17.0)
        path.lineTo(18.0, 17.0)
        path.closeSubpath()
        vis_h = 26.0

    elif shape == "HAND":
        hot_x, hot_y = 8.0 * scale, 2.0 * scale
        path.moveTo(8.0, 2.0)
        path.lineTo(11.0, 2.0)
        path.lineTo(11.0, 11.0)
        path.lineTo(14.0, 11.0)
        path.lineTo(14.0, 13.0)
        path.lineTo(17.0, 13.0)
        path.lineTo(17.0, 15.0)
        path.lineTo(19.0, 15.0)
        path.lineTo(19.0, 22.0)
        path.lineTo(14.0, 27.0)
        path.lineTo(6.0, 27.0)
        path.lineTo(3.0, 18.0)
        path.lineTo(7.0, 15.0)
        path.lineTo(8.0, 11.0)
        path.closeSubpath()
        vis_h = 25.0

    elif shape == "GRAB":
        hot_x, hot_y = 16.0 * scale, 16.0 * scale
        path.addRoundedRect(QRectF(9.0, 13.0, 14.0, 14.0), 4.0, 4.0)
        path.addRoundedRect(QRectF(5.0, 14.0, 6.0, 9.0), 3.0, 3.0)
        path.addRoundedRect(QRectF(9.0, 5.0, 3.2, 12.0), 1.6, 1.6)
        path.addRoundedRect(QRectF(12.6, 3.0, 3.2, 14.0), 1.6, 1.6)
        path.addRoundedRect(QRectF(16.2, 5.0, 3.2, 12.0), 1.6, 1.6)
        path.addRoundedRect(QRectF(19.8, 8.0, 3.2, 9.0), 1.6, 1.6)
        vis_h = 24.0

    elif shape == "GRABBING":
        hot_x, hot_y = 16.0 * scale, 16.0 * scale
        path.addRoundedRect(QRectF(8.0, 11.0, 16.0, 16.0), 5.0, 5.0)
        path.addRoundedRect(QRectF(9.0, 9.0, 14.0, 6.0), 3.0, 3.0)
        path.addRoundedRect(QRectF(6.0, 13.0, 8.0, 8.0), 4.0, 4.0)
        vis_h = 22.0

    elif shape == "IBEAM":
        hot_x, hot_y = 8.0 * scale, 12.0 * scale
        path.moveTo(4.0, 3.0)
        path.lineTo(12.0, 3.0)
        path.moveTo(8.0, 3.0)
        path.lineTo(8.0, 21.0)
        path.moveTo(4.0, 21.0)
        path.lineTo(12.0, 21.0)
        fill_color = QColor(0, 0, 0, 0)
        stroke_color = QColor(255, 255, 255)
        stroke_width = 2.4
        vis_h = 22.0

    elif shape == "CROSS":
        hot_x, hot_y = 12.0 * scale, 12.0 * scale
        path.moveTo(12.0, 2.0)
        path.lineTo(12.0, 9.0)
        path.moveTo(12.0, 15.0)
        path.lineTo(12.0, 22.0)
        path.moveTo(2.0, 12.0)
        path.lineTo(9.0, 12.0)
        path.moveTo(15.0, 12.0)
        path.lineTo(22.0, 12.0)
        fill_color = QColor(0, 0, 0, 0)
        stroke_color = QColor(255, 255, 255)
        stroke_width = 2.0
        vis_h = 22.0

    elif shape in ("WAIT", "APPSTARTING"):
        hot_x, hot_y = 12.0 * scale, 12.0 * scale
        path.addEllipse(QRectF(4.0, 4.0, 16.0, 16.0))
        fill_color = QColor(0, 0, 0, 0)
        stroke_color = QColor(59, 130, 246)
        stroke_width = 3.0
        vis_h = 22.0

    elif shape == "NWPEN":
        hot_x, hot_y = 2.0 * scale, 22.0 * scale
        path.moveTo(2.0, 22.0)
        path.lineTo(6.0, 16.0)
        path.lineTo(20.0, 2.0)
        path.lineTo(24.0, 6.0)
        path.lineTo(10.0, 20.0)
        path.closeSubpath()
        vis_h = 24.0

    else:
        # Default Arrow / Generic
        hot_x, hot_y = 1.0 * scale, 1.0 * scale
        path.moveTo(2.0, 2.0)
        path.lineTo(2.0, 22.0)
        path.lineTo(7.0, 17.0)
        path.lineTo(15.0, 17.0)
        path.closeSubpath()
        vis_h = 24.0

    p.setPen(QPen(stroke_color, stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if fill_color.alpha() > 0:
        p.setBrush(QBrush(fill_color))
    else:
        p.setBrush(Qt.BrushStyle.NoBrush)

    p.drawPath(path)
    p.end()

    min_x, min_y, crop_w, crop_h, has_vis = measure_image_geometry(img)
    if has_vis and crop_w > 0 and crop_h > 0:
        cropped = img.copy(min_x, min_y, crop_w, crop_h)
        pm = QPixmap.fromImage(cropped)
        return CursorAsset(
            name=shape,
            pixmap=pm,
            hotspot_x=max(0.0, hot_x - min_x),
            hotspot_y=max(0.0, hot_y - min_y),
            source_width=float(pm.width()),
            source_height=float(pm.height()),
            visual_height=float(crop_h),
            frames=[pm],
            bitmap_hash=compute_pixmap_hash(pm)
        )

    pm = QPixmap.fromImage(img)
    return CursorAsset(
        name=shape,
        pixmap=pm,
        hotspot_x=hot_x,
        hotspot_y=hot_y,
        source_width=float(pm.width()),
        source_height=float(pm.height()),
        visual_height=vis_h,
        frames=[pm],
        bitmap_hash=compute_pixmap_hash(pm)
    )


class DynamicCursorCache:
    """
    Extracts and caches in-memory custom application HCURSOR handles (e.g. from Chrome,
    Edge, Figma, Adobe, VSCode) using dual-background alpha reconstruction.
    """

    def __init__(self):
        self._cache: Dict[int, CursorAsset] = {}
        self._hash_cache: Dict[str, str] = {}
        self._lock = threading.Lock()

    def get_or_extract(self, hCursor: int) -> Optional[CursorAsset]:
        if not hCursor:
            return None

        with self._lock:
            if hCursor in self._cache:
                return self._cache[hCursor]

            asset = self._extract_hcursor(hCursor)
            if asset:
                self._cache[hCursor] = asset
                if asset.bitmap_hash:
                    self._hash_cache[asset.bitmap_hash] = asset.name
            return asset

    def _extract_hcursor(self, hCursor: int) -> Optional[CursorAsset]:
        try:
            ii = ICONINFO()
            if not user32.GetIconInfo(hCursor, ctypes.byref(ii)):
                return None

            hot_x = float(ii.xHotspot)
            hot_y = float(ii.yHotspot)

            size = 128
            hdc_screen = user32.GetDC(None)
            hdc_b = gdi32.CreateCompatibleDC(hdc_screen)
            hdc_w = gdi32.CreateCompatibleDC(hdc_screen)

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = size
            bmi.biHeight = -size
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0

            pBits_b = ctypes.c_void_p()
            pBits_w = ctypes.c_void_p()
            hbmp_b = gdi32.CreateDIBSection(hdc_b, ctypes.byref(bmi), 0, ctypes.byref(pBits_b), None, 0)
            hbmp_w = gdi32.CreateDIBSection(hdc_w, ctypes.byref(bmi), 0, ctypes.byref(pBits_w), None, 0)

            old_b = gdi32.SelectObject(hdc_b, hbmp_b)
            old_w = gdi32.SelectObject(hdc_w, hbmp_w)

            # 1. Fill black buffer
            hbr_b = gdi32.CreateSolidBrush(0x00000000)
            rect = wintypes.RECT(0, 0, size, size)
            user32.FillRect(hdc_b, ctypes.byref(rect), hbr_b)
            gdi32.DeleteObject(hbr_b)

            # 2. Fill white buffer
            hbr_w = gdi32.CreateSolidBrush(0x00FFFFFF)
            user32.FillRect(hdc_w, ctypes.byref(rect), hbr_w)
            gdi32.DeleteObject(hbr_w)

            # 3. Draw cursor on both buffers
            DI_NORMAL = 0x0003
            user32.DrawIconEx(hdc_b, 0, 0, hCursor, size, size, 0, None, DI_NORMAL)
            user32.DrawIconEx(hdc_w, 0, 0, hCursor, size, size, 0, None, DI_NORMAL)

            buf_len = size * size * 4
            bytes_b = bytearray(ctypes.string_at(pBits_b, buf_len))
            bytes_w = bytearray(ctypes.string_at(pBits_w, buf_len))

            # 4. Mathematically reconstruct true per-pixel alpha
            out_bytes = bytearray(buf_len)
            has_visible = False

            for i in range(0, buf_len, 4):
                b_b = bytes_b[i]
                g_b = bytes_b[i+1]
                r_b = bytes_b[i+2]

                b_w = bytes_w[i]
                g_w = bytes_w[i+1]
                r_w = bytes_w[i+2]

                diff = (max(0, r_w - r_b) + max(0, g_w - g_b) + max(0, b_w - b_b)) // 3
                alpha = 255 - diff
                if alpha < 0: alpha = 0
                elif alpha > 255: alpha = 255

                if alpha > 15:
                    has_visible = True

                out_bytes[i] = b_b
                out_bytes[i+1] = g_b
                out_bytes[i+2] = r_b
                out_bytes[i+3] = alpha

            # Cleanup GDI handles
            gdi32.SelectObject(hdc_b, old_b)
            gdi32.SelectObject(hdc_w, old_w)
            gdi32.DeleteObject(hbmp_b)
            gdi32.DeleteObject(hbmp_w)
            gdi32.DeleteDC(hdc_b)
            gdi32.DeleteDC(hdc_w)
            user32.ReleaseDC(None, hdc_screen)

            if ii.hbmMask: gdi32.DeleteObject(ii.hbmMask)
            if ii.hbmColor: gdi32.DeleteObject(ii.hbmColor)

            if not has_visible:
                return None

            qimg = QImage(bytes(out_bytes), size, size, size * 4, QImage.Format.Format_ARGB32_Premultiplied)
            if qimg.isNull():
                return None

            min_x, min_y, crop_w, crop_h, ok = measure_image_geometry(qimg)
            if ok and crop_w > 0 and crop_h > 0:
                cropped = qimg.copy(min_x, min_y, crop_w, crop_h)
                pm = QPixmap.fromImage(cropped)
                return CursorAsset(
                    name=f"DYNAMIC_{hCursor}",
                    pixmap=pm,
                    hotspot_x=max(0.0, hot_x - min_x),
                    hotspot_y=max(0.0, hot_y - min_y),
                    source_width=float(pm.width()),
                    source_height=float(pm.height()),
                    visual_height=float(crop_h),
                    frames=[pm],
                    bitmap_hash=compute_pixmap_hash(pm)
                )

            pm = QPixmap.fromImage(qimg)
            return CursorAsset(
                name=f"DYNAMIC_{hCursor}",
                pixmap=pm,
                hotspot_x=hot_x,
                hotspot_y=hot_y,
                source_width=float(pm.width()),
                source_height=float(pm.height()),
                visual_height=24.0,
                frames=[pm],
                bitmap_hash=compute_pixmap_hash(pm)
            )
        except Exception:
            return None


class WindowsCursorExtractor:
    r"""
    Comprehensive multi-priority loader for all 17 Windows cursors + Grab/Grabbing:
    Step A: User custom override path (from config.json)
    Step B: Local ./assets/cursors/ and ./cursors/ directories (up to 256x256 high-DPI)
    Step C: Active Windows Registry (HKCU\Control Panel\Cursors) with .ani frame extraction
    Step D: Win32 Kernel OCR system handles (LoadImageW / LoadCursorW)
    Step E: Windows system default cursor directory (C:\Windows\Cursors)
    Step F: Guaranteed sleek vector fallbacks
    """

    def __init__(self, config_overrides: Optional[Dict] = None):
        self.assets: Dict[str, CursorAsset] = {}
        self.known_hashes: Dict[str, str] = {}
        self.scheme_name = "Windows System Scheme"
        self.dynamic_cache = DynamicCursorCache()
        self.config_overrides = config_overrides or {}
        self.reload_all()

    def reload_all(self):
        self.assets.clear()
        self.known_hashes.clear()
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        local_cursors_dirs = [
            os.path.join(project_root, "assets", "cursors"),
            os.path.join(project_root, "cursors")
        ]

        # Try to read active scheme name from registry
        reg_cursor_dict = {}
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors")
            try:
                val, _ = winreg.QueryValueEx(key, "")
                if val and str(val).strip():
                    self.scheme_name = str(val).strip()
            except WindowsError:
                pass

            idx = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(key, idx)
                    if name and val:
                        reg_cursor_dict[name.lower()] = os.path.expandvars(str(val).strip())
                    idx += 1
                except OSError:
                    break
        except Exception as e:
            print(f"[GlideX] Registry warning: {e}")

        for reg_name, shape_key, ocr_id, disp_en, disp_fa in SYSTEM_CURSOR_DEFINITIONS:
            asset = None

            # 1. Check custom path from user config override
            override_entry = self.config_overrides.get(shape_key, {})
            custom_path = override_entry.get("custom_path", "")
            if custom_path and os.path.exists(custom_path):
                asset = self._load_file(custom_path, shape_key)

            # 2. Check local cursors folders
            if not asset:
                for folder in local_cursors_dirs:
                    asset = self._search_local_folder(folder, shape_key, reg_name)
                    if asset:
                        break

            # 3. Check Windows Registry Scheme
            if not asset:
                reg_path = reg_cursor_dict.get(reg_name.lower())
                if reg_path and os.path.exists(reg_path):
                    asset = self._load_file(reg_path, shape_key)

            # 4. Check Win32 Kernel OCR Fallback (LoadImageW / LoadCursorW)
            if not asset and ocr_id:
                asset = self._load_win32_ocr(ocr_id, shape_key)

            # 5. Check Windows Cursors Aero Fallback
            if not asset:
                asset = self._search_system_aero(shape_key)

            # 6. High-DPI Vector Fallback
            if not asset:
                asset = create_vector_fallback(shape_key)

            # Apply per-cursor scale multiplier & hotspot offsets if defined
            if asset:
                scale_mult = override_entry.get("scale_mult", 1.0)
                offset_x = override_entry.get("offset_x", 0.0)
                offset_y = override_entry.get("offset_y", 0.0)
                asset.hotspot_x = max(0.0, asset.hotspot_x + offset_x)
                asset.hotspot_y = max(0.0, asset.hotspot_y + offset_y)
                if scale_mult != 1.0:
                    asset.visual_height = max(6.0, asset.visual_height * scale_mult)

                self.assets[shape_key] = asset
                if asset.bitmap_hash:
                    self.known_hashes[asset.bitmap_hash] = shape_key

        print(f"[GlideX] Engine initialized {len(self.assets)} cursors for scheme '{self.scheme_name}'.")

    def _search_local_folder(self, folder: str, shape: str, reg_name: str) -> Optional[CursorAsset]:
        if not os.path.exists(folder):
            return None

        candidates = {
            "ARROW": ["Normal.cur", "arrow.cur", "arrow.png"],
            "HAND": ["Link.cur", "hand.cur", "pointing.cur"],
            "IBEAM": ["Text.cur", "ibeam.cur", "beam.cur"],
            "WAIT": ["Busy.ani", "busy.cur", "wait.cur"],
            "APPSTARTING": ["Working.ani", "working.cur", "appstarting.cur"],
            "CROSS": ["Precision.cur", "cross.cur", "crosshair.cur"],
            "NO": ["Unavailable.cur", "no.cur"],
            "SIZEALL": ["Move.cur", "sizeall.cur"],
            "SIZEWE": ["Horizontal Resize.cur", "sizewe.cur"],
            "SIZENS": ["Vertical Resize.cur", "sizens.cur"],
            "SIZENWSE": ["Diagonal Resize 1.cur", "sizenwse.cur"],
            "SIZENESW": ["Diagonal Resize 2.cur", "sizenesw.cur"],
            "UPARROW": ["Alternate.cur", "uparrow.cur"],
            "NWPEN": ["Handwriting.cur", "nwpen.cur", "pen.cur"],
            "HELP": ["Help.cur", "helpsel.cur"],
            "PIN": ["Pin.cur"],
            "PERSON": ["Person.cur"],
            "GRAB": ["Pan.cur", "grab.cur", "openhand.cur"],
            "GRABBING": ["Closehand.cur", "grabbing.cur", "closedhand.cur"]
        }.get(shape, [f"{shape.lower()}.cur", f"{reg_name.lower()}.cur"])

        for fname in candidates:
            p = os.path.join(folder, fname)
            if os.path.exists(p):
                asset = self._load_file(p, shape)
                if asset:
                    return asset
        return None

    def _search_system_aero(self, shape: str) -> Optional[CursorAsset]:
        win_dir = os.environ.get("SYSTEMROOT", r"C:\Windows")
        cursors_dir = os.path.join(win_dir, "Cursors")
        defaults = {
            "ARROW": "aero_arrow.cur",
            "HAND": "aero_link.cur",
            "IBEAM": "beam_r.cur",
            "WAIT": "aero_busy.ani",
            "APPSTARTING": "aero_working.ani",
            "CROSS": "cross_r.cur",
            "NO": "aero_unavail.cur",
            "SIZEALL": "aero_move.cur",
            "SIZEWE": "aero_ew.cur",
            "SIZENS": "aero_ns.cur",
            "SIZENWSE": "aero_nwse.cur",
            "SIZENESW": "aero_nesw.cur",
            "UPARROW": "aero_up.cur",
            "NWPEN": "aero_pen.cur",
            "HELP": "aero_helpsel.cur",
            "PIN": "aero_pin.cur",
            "PERSON": "aero_person.cur",
        }
        fname = defaults.get(shape)
        if fname:
            p = os.path.join(cursors_dir, fname)
            if os.path.exists(p):
                return self._load_file(p, shape)
        return None

    def _load_win32_ocr(self, ocr_id: int, shape: str) -> Optional[CursorAsset]:
        try:
            h = user32.LoadImageW(0, ctypes.cast(ocr_id, wintypes.LPCWSTR), IMAGE_CURSOR, 128, 128, LR_SHARED)
            if not h:
                h = user32.LoadCursorW(0, ocr_id)
            if h:
                asset = self.dynamic_cache.get_or_extract(h)
                if asset:
                    asset.name = shape
                    return asset
        except Exception:
            pass
        return None

    def _load_file(self, filepath: str, shape: str) -> Optional[CursorAsset]:
        try:
            if not os.path.exists(filepath):
                return None

            with open(filepath, 'rb') as f:
                data = f.read()

            # 1. Handle .ANI Animated RIFF Cursors
            if data.startswith(b'RIFF') and b'ACON' in data[:16]:
                return self._parse_ani_file(data, shape)

            # 2. Handle standard multi-frame .CUR / .ICO files
            if len(data) >= 6:
                return self._parse_cur_file(data, shape)

            # 3. Handle standard image files (.PNG, etc.)
            qimg = QImage(filepath)
            if not qimg.isNull():
                pm = QPixmap.fromImage(qimg)
                min_x, min_y, crop_w, crop_h, has_vis = measure_image_geometry(qimg)
                vis_h = float(crop_h) if has_vis else float(pm.height())
                return CursorAsset(
                    name=shape,
                    pixmap=pm,
                    hotspot_x=0.0,
                    hotspot_y=0.0,
                    source_width=float(pm.width()),
                    source_height=float(pm.height()),
                    visual_height=vis_h,
                    frames=[pm],
                    bitmap_hash=compute_pixmap_hash(pm)
                )

        except Exception as e:
            print(f"[GlideX] Error loading {filepath}: {e}")
        return None

    def _parse_ani_file(self, data: bytes, shape: str) -> Optional[CursorAsset]:
        """Extracts all high-res animation frames and jifRate from .ANI RIFF file."""
        frames = []
        jif_rate = 4

        pos_anih = data.find(b'anih')
        if pos_anih != -1:
            try:
                sz = struct.unpack('<I', data[pos_anih+4:pos_anih+8])[0]
                anih_bytes = data[pos_anih+8:pos_anih+8+sz]
                if len(anih_bytes) >= 36:
                    _, cFrames, cSteps, cx, cy, _, _, jifRate, _ = struct.unpack('<IIIIIIIII', anih_bytes[:36])
                    if jifRate > 0:
                        jif_rate = jifRate
            except Exception:
                pass

        idx = 0
        hot_x = 0.0
        hot_y = 0.0
        first_vis_h = 24.0

        while True:
            pos = data.find(b'icon', idx)
            if pos == -1:
                break
            sz = int.from_bytes(data[pos+4:pos+8], 'little')
            icon_bytes = data[pos+8:pos+8+sz]
            idx = pos + 8 + sz

            if len(frames) == 0 and len(icon_bytes) >= 14:
                try:
                    _, ctype, _ = struct.unpack_from('<HHH', icon_bytes, 0)
                    if ctype == 2:  # CURSOR
                        _, _, _, _, hx, hy = struct.unpack_from('<BBBBHH', icon_bytes, 6)
                        hot_x = float(hx)
                        hot_y = float(hy)
                except Exception:
                    pass

            qimg = QImage()
            if qimg.loadFromData(icon_bytes):
                pm = QPixmap.fromImage(qimg)
                frames.append(pm)
                if len(frames) == 1:
                    _, _, _, crop_h, has_vis = measure_image_geometry(qimg)
                    if has_vis and crop_h > 0:
                        first_vis_h = float(crop_h)
                    else:
                        first_vis_h = float(pm.height())

        if frames:
            primary = frames[0]
            if hot_x == 0.0 and hot_y == 0.0 and shape == "WAIT":
                hot_x = primary.width() / 2.0
                hot_y = primary.height() / 2.0

            return CursorAsset(
                name=shape,
                pixmap=primary,
                hotspot_x=hot_x,
                hotspot_y=hot_y,
                source_width=float(primary.width()),
                source_height=float(primary.height()),
                visual_height=first_vis_h,
                frames=frames,
                jif_rate=jif_rate,
                bitmap_hash=compute_pixmap_hash(primary)
            )
        return None

    def _parse_cur_file(self, data: bytes, shape: str) -> Optional[CursorAsset]:
        """Finds highest resolution frame (up to 256x256) in .CUR / .ICO file."""
        reserved, cur_type, count = struct.unpack_from('<HHH', data, 0)
        best = None

        for i in range(count):
            w, h, colors, res, hot_x, hot_y, size, offset = struct.unpack_from('<BBBBHHII', data, 6 + i * 16)
            rw = 256 if w == 0 else w
            rh = 256 if h == 0 else h

            if best is None or rw > best['w']:
                best = {
                    'w': rw, 'h': rh,
                    'hot_x': float(hot_x), 'hot_y': float(hot_y),
                    'size': size, 'offset': offset
                }

        if best:
            fb = data[best['offset']:best['offset'] + best['size']]
            qimg = QImage()
            if fb.startswith(b'\x89PNG'):
                qimg.loadFromData(fb, 'PNG')
            else:
                single_header = struct.pack('<HHH', 0, cur_type, 1)
                single_entry = struct.pack(
                    '<BBBBHHII',
                    0 if best['w'] == 256 else best['w'],
                    0 if best['h'] == 256 else best['h'],
                    0, 0, int(best['hot_x']), int(best['hot_y']),
                    best['size'], 22
                )
                qimg.loadFromData(single_header + single_entry + fb)

            if not qimg.isNull():
                min_x, min_y, crop_w, crop_h, has_vis = measure_image_geometry(qimg)
                vis_h = float(crop_h) if has_vis else float(best['h'])
                pm = QPixmap.fromImage(qimg)
                return CursorAsset(
                    name=shape,
                    pixmap=pm,
                    hotspot_x=best['hot_x'],
                    hotspot_y=best['hot_y'],
                    source_width=float(pm.width()),
                    source_height=float(pm.height()),
                    visual_height=vis_h,
                    frames=[pm],
                    bitmap_hash=compute_pixmap_hash(pm)
                )

        return None

    def get_asset(self, shape: str) -> CursorAsset:
        if shape == "GRABBING":
            return self.assets.get("GRABBING", self.assets.get("GRAB", self.assets.get("HAND")))
        if shape == "GRAB":
            return self.assets.get("GRAB", self.assets.get("HAND"))
        return self.assets.get(shape, self.assets.get("ARROW", create_vector_fallback("ARROW")))


class CursorShapeDetector:
    """
    Maps all 17 live Windows cursor handles at startup, queries GetCursorInfo(),
    and resolves unknown custom app handles via fast bitmap hash comparison.
    """

    def __init__(self, extractor: WindowsCursorExtractor):
        self.extractor = extractor
        self.system_handle_map: Dict[int, str] = {}
        self._init_handle_mapping()

        self.cur_tid = kernel32.GetCurrentThreadId()
        self.class_buf = ctypes.create_unicode_buffer(256)

    def _init_handle_mapping(self):
        for reg_name, shape_key, ocr_id, _, _ in SYSTEM_CURSOR_DEFINITIONS:
            if ocr_id:
                h = user32.LoadCursorW(0, ocr_id)
                if h:
                    self.system_handle_map[h] = shape_key

        standard_known = {
            65539: "ARROW",
            65541: "IBEAM",
            65543: "WAIT",
            65545: "CROSS",
            65547: "UPARROW",
            65549: "SIZENWSE",
            65551: "SIZENESW",
            65553: "SIZEWE",
            65555: "SIZENS",
            65557: "SIZEALL",
            65559: "NO",
            65567: "HAND",
            65561: "APPSTARTING",
            65563: "HELP",
            65565: "NWPEN",
            65573: "PIN",
            65575: "PERSON"
        }
        for h, shape in standard_known.items():
            if h not in self.system_handle_map:
                self.system_handle_map[h] = shape

    def detect(self, target_x: float, target_y: float) -> Tuple[str, Optional[int]]:
        ci = CURSORINFO()
        ci.cbSize = ctypes.sizeof(CURSORINFO)
        if user32.GetCursorInfo(ctypes.byref(ci)):
            h = ci.hCursor
            if h:
                if h in self.system_handle_map:
                    return (self.system_handle_map[h], None)

                extracted = self.extractor.dynamic_cache.get_or_extract(h)
                if extracted and extracted.bitmap_hash:
                    if extracted.bitmap_hash in self.extractor.known_hashes:
                        matched_shape = self.extractor.known_hashes[extracted.bitmap_hash]
                        self.system_handle_map[h] = matched_shape
                        return (matched_shape, None)

                return ("DYNAMIC", h)

        pt = wintypes.POINT(int(target_x), int(target_y))
        hwnd = user32.WindowFromPoint(pt)
        if hwnd:
            pid = wintypes.DWORD()
            tid = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if tid and tid != self.cur_tid:
                if user32.AttachThreadInput(self.cur_tid, tid, True):
                    th_cur = user32.GetCursor()
                    user32.AttachThreadInput(self.cur_tid, tid, False)
                    if th_cur:
                        if th_cur in self.system_handle_map:
                            return (self.system_handle_map[th_cur], None)
                        extracted = self.extractor.dynamic_cache.get_or_extract(th_cur)
                        if extracted and extracted.bitmap_hash:
                            if extracted.bitmap_hash in self.extractor.known_hashes:
                                matched_shape = self.extractor.known_hashes[extracted.bitmap_hash]
                                self.system_handle_map[th_cur] = matched_shape
                                return (matched_shape, None)
                        return ("DYNAMIC", th_cur)

            user32.GetClassNameW(hwnd, self.class_buf, 256)
            c_name = self.class_buf.value.lower()
            if any(k in c_name for k in ["edit", "richedit", "scintilla", "textbox", "input"]):
                return ("IBEAM", None)

        return ("ARROW", None)


def render_extracted_cursor(
    painter: QPainter,
    asset: CursorAsset,
    local_x: float,
    local_y: float,
    display_scale: float,
    squash: float,
    stretch: float,
    rotation: float,
    animation_time: float = 0.0
):
    """
    Renders cursor asset through high-DPI transform & normalization pipeline.
    """
    if not asset or not asset.pixmap or asset.pixmap.isNull():
        return

    current_pixmap = asset.pixmap
    if asset.frames and len(asset.frames) > 1:
        fps = 60.0 / max(1, asset.jif_rate)
        frame_idx = int(animation_time * fps) % len(asset.frames)
        current_pixmap = asset.frames[frame_idx]

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    target_visual_height = 26.0 * display_scale
    vis_h = max(8.0, getattr(asset, 'visual_height', 24.0))
    scale_ratio = target_visual_height / vis_h
    scale_ratio = max(0.04, min(4.0, scale_ratio))

    hs_x = asset.hotspot_x * scale_ratio
    hs_y = asset.hotspot_y * scale_ratio

    # 1. Translate to mouse coordinates
    painter.translate(local_x, local_y)

    # 2. Banking / Tilt rotation around hotspot (preserve vertical I-Beam & spinners)
    if abs(rotation) > 0.01 and asset.name not in ("IBEAM", "WAIT", "APPSTARTING"):
        painter.rotate(rotation)

    # 3. Squash and stretch along velocity vector
    painter.scale(squash, stretch)

    # 4. Shift so exact pixel hotspot aligns with (0, 0)
    painter.translate(-hs_x, -hs_y)

    # 5. Draw high-res pixmap
    target_rect = QRectF(0.0, 0.0, asset.source_width * scale_ratio, asset.source_height * scale_ratio)
    source_rect = QRectF(current_pixmap.rect())
    painter.drawPixmap(target_rect, current_pixmap, source_rect)

    painter.restore()
