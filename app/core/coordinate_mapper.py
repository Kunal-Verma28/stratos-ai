"""
Coordinate Mapper — maps hand landmark positions inside the Active Control Zone
to full-screen pixel coordinates.

The "Active Zone" is a sub-rectangle of the camera frame where the user positions
their hand. This prevents the need to move the hand to extreme frame edges,
reducing fatigue while still covering the full screen.
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

        nx, ny — normalized landmark coordinates from MediaPipe (0=left/top, 1=right/bottom).
        The mapping clips to the active zone and stretches it across the full screen.
        """
        cfg = self._cfg

        # Clamp to active zone
        zx = max(cfg.zone_left, min(cfg.zone_right,  nx))
        zy = max(cfg.zone_top,  min(cfg.zone_bottom, ny))

        # Map zone range → [0, 1]
        zone_w = max(cfg.zone_right  - cfg.zone_left, 1e-6)
        zone_h = max(cfg.zone_bottom - cfg.zone_top,  1e-6)
        rel_x = (zx - cfg.zone_left) / zone_w
        rel_y = (zy - cfg.zone_top)  / zone_h

        # Apply sensitivity (centered around 0.5)
        sx = 0.5 + (rel_x - 0.5) * cfg.cursor_sensitivity
        sy = 0.5 + (rel_y - 0.5) * cfg.cursor_sensitivity
        sx = max(0.0, min(1.0, sx))
        sy = max(0.0, min(1.0, sy))

        # Scale to screen
        px = int(sx * self._screen_w)
        py = int(sy * self._screen_h)
        return px, py

    def update_config(self, cfg: Config):
        self._cfg = cfg

    @property
    def screen_size(self) -> tuple[int, int]:
        return self._screen_w, self._screen_h
