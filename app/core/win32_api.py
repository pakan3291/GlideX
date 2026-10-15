"""
Win32 Low-Level APIs & Hardware Cursor Management
=================================================
Bindings for User32, GDI32, Kernel32, Magnification API, and failsafe handlers.
"""

import sys
import signal
import atexit
import ctypes
import threading
from ctypes import wintypes

# Win32 Constants
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

SPI_SETCURSORS = 0x0057
IMAGE_CURSOR = 2
LR_LOADFROMFILE = 0x0010
LR_SHARED = 0x8000

# Standard 17 Windows OCR system cursor IDs
OCR_NORMAL = 32512       # Arrow
OCR_IBEAM = 32513        # I-Beam text
OCR_WAIT = 32514         # Wait / Busy
OCR_CROSS = 32515        # Crosshair / Precision
OCR_UP = 32516           # Up arrow / Alternate
OCR_SIZENWSE = 32642     # Diagonal Resize 1
OCR_SIZENESW = 32643     # Diagonal Resize 2
OCR_SIZEWE = 32644       # Horizontal Resize
OCR_SIZENS = 32645       # Vertical Resize
OCR_SIZEALL = 32646      # Move / Size All
OCR_NO = 32648           # Slashed circle / Unavailable
OCR_HAND = 32649         # Link Select
OCR_APPSTARTING = 32650  # Working in Background
OCR_HELP = 32651         # Help
OCR_NWPEN = 32631        # Handwriting / Pen
OCR_PIN = 32671          # Pin / Location
OCR_PERSON = 32672       # Person / Contact

# Complete 17 cursor mapping registry name -> (Internal Shape Key, OCR ID, Display Name En, Display Name Fa)
SYSTEM_CURSOR_DEFINITIONS = [
    ("Arrow", "ARROW", OCR_NORMAL, "Normal Select", "انتخاب معمولی"),
    ("Help", "HELP", OCR_HELP, "Help Select", "راهنما"),
    ("AppStarting", "APPSTARTING", OCR_APPSTARTING, "Working in Background", "درحال کار در پس‌زمینه"),
    ("Wait", "WAIT", OCR_WAIT, "Busy (Animated)", "مشغول (انیمیشن)"),
    ("Crosshair", "CROSS", OCR_CROSS, "Precision Select", "نشانه‌گیری دقیق"),
    ("IBeam", "IBEAM", OCR_IBEAM, "Text Select", "انتخاب متن"),
    ("NWPen", "NWPEN", OCR_NWPEN, "Handwriting", "قلم / دست‌نویس"),
    ("No", "NO", OCR_NO, "Unavailable", "غیرقابل دسترس"),
    ("SizeNS", "SIZENS", OCR_SIZENS, "Vertical Resize", "تغییر اندازه عمودی"),
    ("SizeWE", "SIZEWE", OCR_SIZEWE, "Horizontal Resize", "تغییر اندازه افقی"),
    ("SizeNWSE", "SIZENWSE", OCR_SIZENWSE, "Diagonal Resize 1", "تغییر اندازه مورب ۱"),
    ("SizeNESW", "SIZENESW", OCR_SIZENESW, "Diagonal Resize 2", "تغییر اندازه مورب ۲"),
    ("SizeAll", "SIZEALL", OCR_SIZEALL, "Move / Pan", "حرکت و جابجایی"),
    ("UpArrow", "UPARROW", OCR_UP, "Alternate Select", "انتخاب ثانویه"),
    ("Hand", "HAND", OCR_HAND, "Link Select", "لینک / اشاره"),
    ("Pin", "PIN", OCR_PIN, "Location Select", "موقعیت مکانی"),
    ("Person", "PERSON", OCR_PERSON, "Person Select", "شخص و مخاطب"),
    ("Pan", "GRAB", None, "Open Hand (Grab)", "دست باز (Grab)"),
    ("Grabbing", "GRABBING", None, "Closed Hand (Grabbing)", "دست بسته (Grabbing)"),
]

ALL_OCR_IDS = [
    OCR_NORMAL, OCR_IBEAM, OCR_WAIT, OCR_CROSS, OCR_UP,
    OCR_SIZENWSE, OCR_SIZENESW, OCR_SIZEWE, OCR_SIZENS,
    OCR_SIZEALL, OCR_NO, OCR_HAND, OCR_APPSTARTING, OCR_HELP,
    OCR_NWPEN, OCR_PIN, OCR_PERSON
]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('hCursor', wintypes.HANDLE),
        ('ptScreenPos', wintypes.POINT)
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ('fIcon', wintypes.BOOL),
        ('xHotspot', wintypes.DWORD),
        ('yHotspot', wintypes.DWORD),
        ('hbmMask', wintypes.HANDLE),
        ('hbmColor', wintypes.HANDLE)
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD)
    ]


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorInfo.restype = wintypes.BOOL

user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(ICONINFO)]
user32.GetIconInfo.restype = wintypes.BOOL

user32.DrawIconEx.argtypes = [
    wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HICON,
    ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.HBRUSH, wintypes.UINT
]
user32.DrawIconEx.restype = wintypes.BOOL

user32.LoadImageW.argtypes = [
    wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
    ctypes.c_int, ctypes.c_int, wintypes.UINT
]
user32.LoadImageW.restype = wintypes.HANDLE

user32.LoadCursorFromFileW.argtypes = [wintypes.LPCWSTR]
user32.LoadCursorFromFileW.restype = wintypes.HANDLE

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = wintypes.BOOL

user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
user32.FillRect.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH

gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ

gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.POINTER(BITMAPINFOHEADER), wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP


def get_virtual_desktop_rect():
    """Get the bounding rectangle of all connected displays."""
    vx = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    vy = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    vw = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    vh = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return vx, vy, vw, vh


def get_current_cursor_pos():
    """Get current global mouse cursor position via Win32 API."""
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def apply_click_through(hwnd: int):
    """Apply transparent click-through and non-activating styles to window."""
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    new_style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


class SystemCursorManager:
    """
    Manages global hiding and restoring of Windows hardware cursors using
    the official Windows Magnification API (`MagShowSystemCursor(False)`).
    """

    def __init__(self):
        self.is_hidden = False
        self._mag_initialized = False
        self._mag = getattr(ctypes.windll, "magnification", None)
        self._lock = threading.Lock()
        self._register_failsafes()

    def _register_failsafes(self):
        atexit.register(self.restore)
        try:
            signal.signal(signal.SIGINT, lambda s, f: self._emergency_exit())
            signal.signal(signal.SIGTERM, lambda s, f: self._emergency_exit())
        except Exception:
            pass

        orig_excepthook = sys.excepthook
        def custom_excepthook(exc_type, exc_val, exc_tb):
            self.restore()
            orig_excepthook(exc_type, exc_val, exc_tb)
        sys.excepthook = custom_excepthook

    def _emergency_exit(self):
        self.restore()
        sys.exit(0)

    def hide(self) -> bool:
        """Globally hides hardware cursors without modifying system handles."""
        with self._lock:
            if self._mag:
                try:
                    if not self._mag_initialized:
                        res = self._mag.MagInitialize()
                        self._mag_initialized = bool(res)
                    if self._mag_initialized:
                        self._mag.MagShowSystemCursor(False)
                        self.is_hidden = True
                        return True
                except Exception as e:
                    print(f"[GlideX] MagShowSystemCursor notice: {e}")

            self.is_hidden = True
            return True

    def restore(self) -> bool:
        """Instantly restores all native hardware and system cursors."""
        with self._lock:
            if self._mag and self._mag_initialized:
                try:
                    self._mag.MagShowSystemCursor(True)
                    self._mag.MagUninitialize()
                    self._mag_initialized = False
                except Exception:
                    pass

            user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            self.is_hidden = False
            return True
