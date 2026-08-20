"""
Keyboard Controller — simulates Windows key presses and shortcuts.
Uses ctypes SendInput for compatibility with all Windows applications.
"""
import ctypes
from ctypes import wintypes
import time

from app.utils.logger import logger

# ── Virtual key codes ───────────────────────────────────────────────────────
VK = {
    "screenshot": 0x2C,         # Print Screen (VK_SNAPSHOT)
    "copy":       ord("C"),
    "paste":      ord("V"),
    "cut":        ord("X"),
    "undo":       ord("Z"),
    "redo":       ord("Y"),
    "ctrl":       0x11,
    "alt":        0x12,
    "shift":      0x10,
    "win":        0x5B,
    "tab":        0x09,
    "f4":         0x73,
    "back":       0x08,
    "media_play": 0xB3,         # VK_MEDIA_PLAY_PAUSE
    "vol_up":     0xAF,         # VK_VOLUME_UP
    "vol_down":   0xAE,         # VK_VOLUME_DOWN
    "mute":       0xAD,         # VK_VOLUME_MUTE
    "next_track": 0xB0,
    "prev_track": 0xB1,
    "brightness_up":   None,    # Requires OEM key — handled by system controller
    "brightness_down": None,
}

INPUT_KEYBOARD    = 1
KEYEVENTF_KEYUP   = 0x0002
KEYEVENTF_UNICODE = 0x0004

PUL = ctypes.POINTER(ctypes.c_ulong)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         wintypes.WORD),
        ("wScan",       wintypes.WORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ii",   _INPUT_UNION),
    ]


class KeyboardController:

    def _send_key(self, vk: int, flags: int = 0):
        extra = ctypes.c_ulong(0)
        inp = INPUT(
            ctypes.c_ulong(INPUT_KEYBOARD),
            _INPUT_UNION(ki=KEYBDINPUT(vk, 0, flags, 0, ctypes.pointer(extra)))
        )
        ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))

    def press(self, vk: int):
        self._send_key(vk, 0)

    def release(self, vk: int):
        self._send_key(vk, KEYEVENTF_KEYUP)

    def tap(self, vk: int, delay: float = 0.02):
        self.press(vk)
        time.sleep(delay)
        self.release(vk)

    def hotkey(self, *vks: int, delay: float = 0.02):
        """Press multiple keys simultaneously then release."""
        for vk in vks:
            self.press(vk)
        time.sleep(delay)
        for vk in reversed(vks):
            self.release(vk)

    def screenshot(self):
        """Send Print Screen key."""
        self.tap(VK["screenshot"])
        logger.info("Action: Screenshot (PrtSc)")

    def copy(self):
        self.hotkey(VK["ctrl"], VK["copy"])
        logger.info("Action: Copy (Ctrl+C)")

    def paste(self):
        self.hotkey(VK["ctrl"], VK["paste"])
        logger.info("Action: Paste (Ctrl+V)")

    def media_play_pause(self):
        self.tap(VK["media_play"])
        logger.info("Action: Media Play/Pause")

    def volume_up(self):
        self.tap(VK["vol_up"])
        logger.info("Action: Volume Up")

    def volume_down(self):
        self.tap(VK["vol_down"])
        logger.info("Action: Volume Down")

    def mute_toggle(self):
        self.tap(VK["mute"])
        logger.info("Action: Mute Toggle")

    def next_track(self):
        self.tap(VK["next_track"])

    def prev_track(self):
        self.tap(VK["prev_track"])
