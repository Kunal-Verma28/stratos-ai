"""
System Controller — Windows volume, media, and brightness controls.
Uses Windows Core Audio API via ctypes for volume, and VK media keys.
"""
from app.controller.keyboard_controller import KeyboardController
from app.utils.logger import logger


class SystemController:
    """
    High-level system action dispatcher.
    Wraps KeyboardController for media/volume and provides screen brightness
    control via WMI (Windows Management Instrumentation) where available.
    """

    def __init__(self):
        self._kb = KeyboardController()

    def screenshot(self):
        """Capture screenshot via Print Screen key."""
        self._kb.screenshot()

    def volume_up(self):
        self._kb.volume_up()

    def volume_down(self):
        self._kb.volume_down()

    def mute_toggle(self):
        self._kb.mute_toggle()

    def media_play_pause(self):
        self._kb.media_play_pause()

    def media_next(self):
        self._kb.next_track()

    def media_prev(self):
        self._kb.prev_track()

    def set_brightness(self, level: int):
        """
        Set screen brightness 0–100 via WMI.
        Only works on laptops with WMI-compatible display drivers.
        """
        try:
            import wmi
            c = wmi.WMI(namespace="wmi")
            methods = c.WmiMonitorBrightnessMethods()[0]
            methods.WmiSetBrightness(level, 0)
            logger.info(f"Brightness set to {level}%")
        except Exception as e:
            logger.warning(f"Brightness control unavailable: {e}")
