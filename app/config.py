"""
STRATOS™ AI — Configuration & Enterprise Settings
Production Edition v1.0.0-PRO
Copyright (c) 2026 Stratos Technologies. All rights reserved.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any

APP_NAME = "STRATOS™ AI"
APP_VERSION = "1.0.0-PRO"
APP_TAGLINE = "Spatial Computing & Touchless Desktop Engine"
APP_ORGANIZATION = "Stratos Spatial Technologies"
APP_COPYRIGHT = "© 2026 Stratos Technologies. All rights reserved."

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "user_profile.json")

@dataclass
class Config:
    # ── Operating Mode ─────────────────────────────────────
    operation_mode: str = "Desktop Navigation" # "Desktop Navigation", "Presentation Remote", "Media Controller"

    # ── Camera ─────────────────────────────────────────────
    camera_index: int = 0                # 0 = default webcam, 1+ = external USB
    camera_width: int = 1280
    camera_height: int = 720
    camera_fps: int = 30

    # ── Active Control Zone (fraction of frame) ─────────────
    zone_left: float = 0.10              # 10% from left edge
    zone_right: float = 0.90             # 90% from left edge
    zone_top: float = 0.15              # 15% from top
    zone_bottom: float = 0.85           # 85% from top

    # ── Cursor Kinetics ────────────────────────────────────
    cursor_sensitivity: float = 1.0      # Multiplier on cursor speed
    smoothing_min_cutoff: float = 0.8    # One-Euro filter: lower = smoother
    smoothing_beta: float = 0.006        # One-Euro filter: higher = less lag on fast moves
    smoothing_d_cutoff: float = 1.0

    # ── Gesture Thresholds ─────────────────────────────────
    pinch_threshold: float = 0.048       # Normalized index-thumb pinch distance
    right_click_threshold: float = 0.048 # Normalized middle-thumb pinch distance
    scroll_fingers_threshold: float = 0.065  # Max gap between index+middle to activate scroll
    scroll_sensitivity: int = 3          # Scroll lines per gesture tick
    swipe_velocity_threshold: float = 0.8 # Normalized X velocity for swipe detection

    # ── Timing & Cooldowns ────────────────────────────────
    click_lock_ms: int = 120             # Cursor freeze window during click (ms)
    click_cooldown_ms: int = 400         # Min ms between consecutive clicks
    double_click_window_ms: int = 350    # Max ms between two pinches for double-click
    drag_hold_ms: int = 350              # Pinch hold duration before drag starts
    fist_pause_hold_ms: int = 1000       # Hold fist this long to toggle pause
    gesture_cooldown_ms: int = 500       # General cooldown for system actions

    # ── Hand Detection ────────────────────────────────────
    max_hands: int = 1                   # 1 for MVP, 2 for advanced mode
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.6
    control_hand: str = "Right"          # "Right" or "Left"

    # ── UI & HUD ──────────────────────────────────────────
    show_camera_preview: bool = True
    show_hud_overlay: bool = True
    hud_opacity: float = 0.90
    dark_mode: bool = True

    # ── Hotkeys ──────────────────────────────────────────
    pause_hotkey: str = "f8"             # Global pause/resume key
    quit_hotkey: str = "ctrl+shift+q"

    # ── Gesture Enable Flags ──────────────────────────────
    gesture_left_click: bool = True
    gesture_right_click: bool = True
    gesture_double_click: bool = True
    gesture_drag: bool = True
    gesture_scroll: bool = True
    gesture_screenshot: bool = True
    gesture_volume: bool = True
    gesture_media: bool = True
    gesture_three_four_fingers: bool = True
    gesture_thumbs: bool = True
    gesture_swipes: bool = True

    # ── Custom Keybindings ────────────────────────────────
    custom_three_fingers: str = "ctrl+c"
    custom_four_fingers: str = "ctrl+v"
    custom_thumbs_up: str = "vol_up"
    custom_thumbs_down: str = "vol_down"
    custom_swipe_left: str = "prev_track"
    custom_swipe_right: str = "next_track"

    def save(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def load(cls) -> "Config":
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH) as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass
        return cls()


# Global singleton
_config: Config | None = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config
