"""
STRATOS™ AI — Configuration & Enterprise Settings
Production Edition v1.0.0-PRO
Optimized for high-speed spatial computing and ultra-responsive gesture detection.
"""
import json
import os
from dataclasses import dataclass, asdict

APP_NAME = "STRATOS™ AI"
APP_VERSION = "1.0.0-PRO"
APP_TAGLINE = "Spatial Computing & Touchless Desktop Engine"
APP_ORGANIZATION = "Stratos Spatial Technologies"
APP_COPYRIGHT = "© 2026 Stratos Technologies. All rights reserved."

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "user_profile.json"
)


@dataclass
class Config:
    # ── Operating Mode ──────────────────────────────────────────────────────
    operation_mode: str = "Desktop Navigation"

    # ── Camera ──────────────────────────────────────────────────────────────
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 30
    inference_width: int = 320    # Downscaled for 3x faster MediaPipe inference
    inference_height: int = 240

    # ── Active Control Zone (Compact box: reach 100% screen with 50% hand movement)
    zone_left: float = 0.20       # 20% margin from left
    zone_right: float = 0.80      # 80% from left (60% active width)
    zone_top: float = 0.15        # 15% margin from top
    zone_bottom: float = 0.75     # 75% from top (60% active height)

    # ── Cursor Kinetics ──────────────────────────────────────────────────────
    cursor_sensitivity: float = 1.6     # High sensitivity: covers full screen effortlessly
    smoothing_min_cutoff: float = 1.1   # One-Euro filter: responsiveness at low speeds
    smoothing_beta: float = 0.012       # One-Euro filter: zero lag at high speeds
    smoothing_d_cutoff: float = 1.0

    # ── Gesture Thresholds (Normalized Distance Units) ──────────────────────
    pinch_threshold: float = 0.14        # Index-Thumb pinch (< 0.14 = pinch active)
    right_click_threshold: float = 0.14  # Middle-Thumb pinch (< 0.14 = right pinch)
    scroll_fingers_threshold: float = 0.18 # Peace sign separation
    scroll_sensitivity: int = 4          # Scroll steps per movement tick
    swipe_velocity_threshold: float = 0.55 # Horizontal hand swipe threshold

    # ── Timing & Cooldowns ───────────────────────────────────────────────────
    click_lock_ms: int = 80             # Cursor anti-drift freeze on click (ms)
    click_cooldown_ms: int = 280         # Minimum interval between clicks
    double_click_window_ms: int = 400    # Window to perform double pinch
    drag_hold_ms: int = 350              # Pinch hold duration to engage drag
    fist_pause_hold_ms: int = 1200       # Fist hold to toggle standby
    gesture_cooldown_ms: int = 600       # Cooldown for screenshot / media hotkeys
    frame_skip: int = 2                  # 1 in 2 frames for CPU performance

    # ── Hand Detection ───────────────────────────────────────────────────────
    max_hands: int = 1
    min_detection_confidence: float = 0.55
    min_tracking_confidence: float = 0.50
    control_hand: str = "Right"

    # ── UI & HUD ─────────────────────────────────────────────────────────────
    show_camera_preview: bool = True
    show_hud_overlay: bool = True
    hud_opacity: float = 0.92
    dark_mode: bool = True

    # ── Global Hotkeys ────────────────────────────────────────────────────────
    pause_hotkey: str = "f8"
    quit_hotkey: str = "ctrl+shift+q"

    # ── Gesture Enable Flags ──────────────────────────────────────────────────
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

    # ── Custom Keybindings ────────────────────────────────────────────────────
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


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config
