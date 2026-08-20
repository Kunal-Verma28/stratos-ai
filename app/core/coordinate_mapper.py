"""
Coordinate Mapper — maps hand landmark positions inside the Active Control Zone
to full-screen pixel coordinates.

The "Active Zone" is a centered sub-rectangle of the camera frame.
Moving the hand within this compact area maps to 100% of the PC screen,
so the user's hand NEVER leaves the camera frame.
"""
import ctypes
from app.config import Config


class CoordinateMapper:
    """
    Maps normalized (0..1) camera coordinates inside the configured Active Zone
    to absolute screen pixel positions.
    """

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._screen_w, self._screen_h = self._get_screen_size()
        # For multi-monitor: use virtual screen (all monitors combined)
        self._virtual_w = ctypes.windll.user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        self._virtual_h = ctypes.windll.user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        if self._virtual_w == 0:
            self._virtual_w = self._screen_w
            self._virtual_h = self._screen_h

    @staticmethod
    def _get_screen_size() -> tuple[int, int]:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    def map(self, nx: float, ny: float) -> tuple[int, int]:
        """
        Convert normalized (0..1) camera x, y to screen pixel coordinates.
        Maps the compact active zone across the entire desktop resolution.
        """
        cfg = self._cfg

        # Relative progress inside the active box: 0.0 (left/top) to 1.0 (right/bottom)
        zone_w = max(cfg.zone_right - cfg.zone_left, 0.20)
        zone_h = max(cfg.zone_bottom - cfg.zone_top, 0.20)

        rel_x = (nx - cfg.zone_left) / zone_w
        rel_y = (ny - cfg.zone_top)  / zone_h

        # Apply Sensitivity centered at 0.5 (center of box = center of screen)
        sx = 0.5 + (rel_x - 0.5) * cfg.cursor_sensitivity
        sy = 0.5 + (rel_y - 0.5) * cfg.cursor_sensitivity

        # Clamp cleanly to screen bounds
        sx = max(0.0, min(1.0, sx))
        sy = max(0.0, min(1.0, sy))

        px = int(sx * self._screen_w)
        py = int(sy * self._screen_h)
        return px, py

    def update_config(self, cfg: Config):
        self._cfg = cfg

    @property
    def screen_size(self) -> tuple[int, int]:
        return self._screen_w, self._screen_h
