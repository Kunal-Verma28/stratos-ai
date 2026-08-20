"""
STRATOS™ AI — Windows Keyboard Controller & Shortcut Dispatcher
Uses ctypes SendInput for core keys and keyboard library for complex combos.
"""
import ctypes
from ctypes import wintypes
import time
import keyboard

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
    "page_up":    0x21,
    "page_down":  0x22,
    "left":       0x25,
    "right":      0x27,
    "escape":     0x1B,
}

INPUT_KEYBOARD    = 1
KEYEVENTF_KEYUP   = 0x0002

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
    """
    High-speed keyboard automation dispatcher.
    Supports single virtual keys and arbitrary combination strings.
    """

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

    def dispatch_custom(self, key_combination: str):
        """
        Dispatches arbitrary shortcut strings like 'ctrl+c', 'page_down', 'win+tab', etc.
        """
        key_str = key_combination.strip().lower()
        if not key_str:
            return

        # Named shortcuts mapping
        if key_str in ("vol_up", "volume_up"):
            self.volume_up()
        elif key_str in ("vol_down", "volume_down"):
            self.volume_down()
        elif key_str in ("mute", "mute_toggle"):
            self.mute_toggle()
        elif key_str in ("media_play", "play_pause"):
            self.media_play_pause()
        elif key_str in ("next_track", "next_slide"):
            self.next_track()
        elif key_str in ("prev_track", "prev_slide"):
            self.prev_track()
        elif key_str in ("screenshot", "prtsc"):
            self.screenshot()
        else:
            try:
                keyboard.send(key_str)
                logger.info(f"Custom shortcut sent: {key_str}")
            except Exception as e:
                logger.warning(f"Failed to dispatch custom key '{key_str}': {e}")

    def next_slide(self):
        self.tap(VK["right"])
        logger.info("Action: Next Slide (Right Arrow)")

    def prev_slide(self):
        self.tap(VK["left"])
        logger.info("Action: Prev Slide (Left Arrow)")

    def blank_screen(self):
        # In PowerPoint, pressing 'B' toggles black screen
        keyboard.send("b")
        logger.info("Action: Toggle Blank Slide Screen")

    def screenshot(self):
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
