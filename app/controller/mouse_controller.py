"""
Windows Mouse Controller — uses Win32 SendInput for zero-latency mouse injection.
Avoids PyAutoGUI's artificial delays.
"""
import ctypes
from ctypes import wintypes
import time

from app.utils.logger import logger

# ── Win32 struct definitions ────────────────────────────────────────────────
PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          wintypes.LONG),
        ("dy",          wintypes.LONG),
        ("mouseData",   wintypes.DWORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ii",   _INPUT_UNION),
    ]

INPUT_MOUSE          = 0
MOUSEEVENTF_MOVE     = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004
MOUSEEVENTF_RIGHTDOWN= 0x0008
MOUSEEVENTF_RIGHTUP  = 0x0010
MOUSEEVENTF_WHEEL    = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
SM_CXSCREEN          = 0
SM_CYSCREEN          = 1


class MouseController:
    """
    High-performance Windows mouse controller using SendInput.
    Supports: absolute move, click, right-click, double-click, drag, scroll.
    """

    def __init__(self):
        u32 = ctypes.windll.user32
        self._sw = u32.GetSystemMetrics(SM_CXSCREEN)
        self._sh = u32.GetSystemMetrics(SM_CYSCREEN)
        self._is_down = False
        self._lock_until: float = 0.0   # Coordinate lock expiry timestamp
        self._locked_x: int = 0
        self._locked_y: int = 0
        logger.info(f"MouseController ready. Screen: {self._sw}×{self._sh}")

    def _send(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0):
        extra = ctypes.c_ulong(0)
        inp = INPUT(
            ctypes.c_ulong(INPUT_MOUSE),
            _INPUT_UNION(mi=MOUSEINPUT(dx, dy, data, flags, 0, ctypes.pointer(extra)))
        )
        ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))

    def move(self, x: int, y: int):
        """Move cursor to absolute screen coordinates."""
        now = time.perf_counter()
        if now < self._lock_until:
            # Coordinate lock is active — don't move during click
            return
        x = max(0, min(self._sw - 1, x))
        y = max(0, min(self._sh - 1, y))
        nx = int(x * 65535 / self._sw)
        ny = int(y * 65535 / self._sh)
        self._send(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, nx, ny)

    def left_click(self, x: int, y: int, lock_ms: int = 120):
        """Move to position and click. Applies coordinate lock during execution."""
        self.move(x, y)
        # Start lock so cursor doesn't drift during click
        self._lock_until = time.perf_counter() + lock_ms / 1000.0
        self._locked_x, self._locked_y = x, y
        self._send(MOUSEEVENTF_LEFTDOWN)
        self._send(MOUSEEVENTF_LEFTUP)
        logger.debug(f"Left click @ ({x},{y})")

    def right_click(self, x: int, y: int, lock_ms: int = 120):
        self.move(x, y)
        self._lock_until = time.perf_counter() + lock_ms / 1000.0
        self._send(MOUSEEVENTF_RIGHTDOWN)
        self._send(MOUSEEVENTF_RIGHTUP)
        logger.debug(f"Right click @ ({x},{y})")

    def double_click(self, x: int, y: int, lock_ms: int = 200):
        self.move(x, y)
        self._lock_until = time.perf_counter() + lock_ms / 1000.0
        self._send(MOUSEEVENTF_LEFTDOWN)
        self._send(MOUSEEVENTF_LEFTUP)
        time.sleep(0.05)
        self._send(MOUSEEVENTF_LEFTDOWN)
        self._send(MOUSEEVENTF_LEFTUP)
        logger.debug(f"Double click @ ({x},{y})")

    def mouse_down(self, x: int, y: int):
        """Press and hold left mouse button (start drag)."""
        self.move(x, y)
        if not self._is_down:
            self._send(MOUSEEVENTF_LEFTDOWN)
            self._is_down = True
            logger.debug(f"Mouse DOWN @ ({x},{y})")

    def mouse_up(self, x: int, y: int):
        """Release left mouse button (end drag)."""
        if self._is_down:
            self.move(x, y)
            self._send(MOUSEEVENTF_LEFTUP)
            self._is_down = False
            logger.debug(f"Mouse UP @ ({x},{y})")

    def scroll(self, steps: int):
        """
        Scroll vertically. Positive = scroll down, negative = scroll up.
        steps is multiplied by 120 (one Windows scroll notch).
        """
        self._send(MOUSEEVENTF_WHEEL, data=-(steps * 120))

    def emergency_release(self):
        """Release any held mouse buttons — called on pause or panic stop."""
        if self._is_down:
            self._send(MOUSEEVENTF_LEFTUP)
            self._is_down = False
