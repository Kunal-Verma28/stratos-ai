"""
STRATOS™ AI — Gesture Recognition Engine & Multi-Mode State Machine
Features:
  - Desktop, Presentation, and Media operating modes
  - Dynamic swipe velocity analysis
  - Thumb orientation (Up/Down) & 3/4-finger posture detection
  - Cooldown timers, hysteresis, and anti-drift coordinate locking
"""
import time
from typing import Optional
from collections import deque

from app.config import Config
from app.utils.math_helpers import (
    LM, normalized_distance, finger_extended, thumb_extended,
    thumb_vertical_direction, get_finger_states, count_extended_fingers, palm_center
)
from app.gestures.gesture_types import GestureState, ActionType, GestureEvent, OperationMode


class GestureRecognizer:

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._state = GestureState.IDLE
        self._prev_state = GestureState.IDLE

        # Timing trackers (in seconds via perf_counter)
        self._pinch_start_t: float = 0.0
        self._pinch_release_t: float = 0.0
        self._last_click_t: float = 0.0
        self._last_right_click_t: float = 0.0
        self._fist_start_t: float = 0.0
        self._last_gesture_t: float = 0.0
        self._last_swipe_t: float = 0.0

        # State flags
        self._is_paused: bool = False
        self._drag_active: bool = False
        self._last_scroll_y: float = 0.0
        self._scroll_ref_y: float = 0.0
        self._pending_double_click: bool = False
        self._pinch_was_active: bool = False
        self._scroll_acc: float = 0.0

        # Palm position history for swipe velocity detection: deque of (x, timestamp)
        self._palm_history: deque = deque(maxlen=10)

        # Telemetry for calibration UI
        self._last_pinch_distance: float = 0.0

    @property
    def last_pinch_distance(self) -> float:
        """Exposes the latest normalized pinch distance for UI calibration gauges."""
        return self._last_pinch_distance

    def process(self, lms: list, screen_xy: tuple[int, int]) -> Optional[GestureEvent]:
        """
        Process hand landmarks according to current Operation Mode and emit GestureEvent.
        """
        now = time.perf_counter()
        cfg = self._cfg
        x, y = screen_xy

        # Track palm center for swipe detection
        palm_pt = palm_center(lms)
        self._palm_history.append((palm_pt[0], now))

        # ── 1. Global Standby (Fist Hold in Desktop Mode) ──────────────────────
        n_ext = count_extended_fingers(lms)
        mode = cfg.operation_mode

        if n_ext == 0:  # Closed Fist
            if self._fist_start_t == 0.0:
                self._fist_start_t = now
            elif (now - self._fist_start_t) * 1000 >= cfg.fist_pause_hold_ms:
                self._fist_start_t = 0.0
                if mode == "Desktop Navigation":
                    self._is_paused = not self._is_paused
                    self._state = GestureState.PAUSED if self._is_paused else GestureState.IDLE
                    return GestureEvent(
                        gesture=GestureState.PAUSED,
                        action=ActionType.TOGGLE_PAUSE,
                    )
                elif mode == "Presentation Remote":
                    return GestureEvent(gesture=GestureState.FIST, action=ActionType.CUSTOM_HOTKEY, custom_key="b")
                elif mode == "Media Controller":
                    if (now - self._last_gesture_t) * 1000 >= cfg.gesture_cooldown_ms:
                        self._last_gesture_t = now
                        return GestureEvent(gesture=GestureState.FIST, action=ActionType.MEDIA_PLAY_PAUSE)
        else:
            self._fist_start_t = 0.0

        if self._is_paused:
            return None

        # ── 2. Swipe Velocity Analysis (Fast horizontal movement) ──────────────
        if cfg.gesture_swipes and len(self._palm_history) >= 6:
            dt = self._palm_history[-1][1] - self._palm_history[0][1]
            if 0.08 < dt < 0.35:
                dx = self._palm_history[-1][0] - self._palm_history[0][0]
                velocity = dx / dt
                if abs(velocity) > cfg.swipe_velocity_threshold and (now - self._last_swipe_t) * 1000 >= 700:
                    self._last_swipe_t = now
                    self._palm_history.clear()
                    if velocity > 0:  # Swipe Right
                        if mode == "Presentation Remote":
                            return GestureEvent(gesture=GestureState.SWIPE_RIGHT, action=ActionType.NEXT_SLIDE)
                        else:
                            return GestureEvent(gesture=GestureState.SWIPE_RIGHT, action=ActionType.CUSTOM_HOTKEY, custom_key=cfg.custom_swipe_right)
                    else:  # Swipe Left
                        if mode == "Presentation Remote":
                            return GestureEvent(gesture=GestureState.SWIPE_LEFT, action=ActionType.PREV_SLIDE)
                        else:
                            return GestureEvent(gesture=GestureState.SWIPE_LEFT, action=ActionType.CUSTOM_HOTKEY, custom_key=cfg.custom_swipe_left)

        # ── 3. Biometric Measurements & Finger Extension Extraction ───────────
        pinch_l = normalized_distance(lms, LM.THUMB_TIP, LM.INDEX_TIP)
        pinch_r = normalized_distance(lms, LM.THUMB_TIP, LM.MIDDLE_TIP)
        self._last_pinch_distance = pinch_l

        t_ext, i_ext, m_ext, r_ext, p_ext = get_finger_states(lms)
        thumb_dir = thumb_vertical_direction(lms)

        is_pinching_l = pinch_l < cfg.pinch_threshold
        is_pinching_r = (pinch_r < cfg.right_click_threshold and not is_pinching_l and i_ext)

        # ── 4. Thumbs Up / Thumbs Down Detection ──────────────────────────────
        if cfg.gesture_thumbs and not (i_ext or m_ext or r_ext or p_ext):
            if thumb_dir == "up" and (now - self._last_gesture_t) * 1000 >= cfg.gesture_cooldown_ms:
                self._last_gesture_t = now
                if mode == "Presentation Remote":
                    return GestureEvent(gesture=GestureState.THUMBS_UP, action=ActionType.NEXT_SLIDE)
                else:
                    return GestureEvent(gesture=GestureState.THUMBS_UP, action=ActionType.CUSTOM_HOTKEY, custom_key=cfg.custom_thumbs_up)

            elif thumb_dir == "down" and (now - self._last_gesture_t) * 1000 >= cfg.gesture_cooldown_ms:
                self._last_gesture_t = now
                if mode == "Presentation Remote":
                    return GestureEvent(gesture=GestureState.THUMBS_DOWN, action=ActionType.PREV_SLIDE)
                else:
                    return GestureEvent(gesture=GestureState.THUMBS_DOWN, action=ActionType.CUSTOM_HOTKEY, custom_key=cfg.custom_thumbs_down)

        # ── 5. Three Fingers (Copy) & Four Fingers (Paste) ─────────────────────
        if cfg.gesture_three_four_fingers and mode == "Desktop Navigation":
            if i_ext and m_ext and r_ext and not p_ext and (now - self._last_gesture_t) * 1000 >= 600:
                self._last_gesture_t = now
                return GestureEvent(gesture=GestureState.THREE_FINGERS, action=ActionType.CUSTOM_HOTKEY, custom_key=cfg.custom_three_fingers)

            if i_ext and m_ext and r_ext and p_ext and not t_ext and (now - self._last_gesture_t) * 1000 >= 600:
                self._last_gesture_t = now
                return GestureEvent(gesture=GestureState.FOUR_FINGERS, action=ActionType.CUSTOM_HOTKEY, custom_key=cfg.custom_four_fingers)

        # ── 6. Open Palm (Screenshot / Reset) ──────────────────────────────────
        if n_ext == 5:
            if (now - self._last_gesture_t) * 1000 >= cfg.gesture_cooldown_ms and cfg.gesture_screenshot:
                self._last_gesture_t = now
                return GestureEvent(gesture=GestureState.OPEN_PALM, action=ActionType.SCREENSHOT)

        # ── 7. Scroll Mode (Peace Sign: Index + Middle) ────────────────────────
        peace_mode = (i_ext and m_ext and not r_ext and not p_ext and
                      normalized_distance(lms, LM.INDEX_TIP, LM.MIDDLE_TIP) < cfg.scroll_fingers_threshold)

        if peace_mode and cfg.gesture_scroll:
            mid_y = (lms[LM.INDEX_TIP][1] + lms[LM.MIDDLE_TIP][1]) / 2.0
            if self._state != GestureState.SCROLL_ACTIVE:
                self._state = GestureState.SCROLL_ACTIVE
                self._scroll_ref_y = mid_y
                self._scroll_acc = 0.0
            else:
                dy = (mid_y - self._scroll_ref_y) * 10.0
                self._scroll_acc += dy
                self._scroll_ref_y = mid_y
                steps = int(self._scroll_acc)
                if steps != 0:
                    self._scroll_acc -= steps
                    action = ActionType.SCROLL_DOWN if steps > 0 else ActionType.SCROLL_UP
                    return GestureEvent(
                        gesture=GestureState.SCROLL_ACTIVE,
                        action=action,
                        delta=abs(steps) * cfg.scroll_sensitivity,
                    )
            return None

        # ── 8. Left Pinch (Click, Double Click, Drag) ──────────────────────────
        if is_pinching_l and cfg.gesture_left_click:
            if not self._pinch_was_active:
                self._pinch_was_active = True
                self._pinch_start_t = now

                gap_ms = (now - self._last_click_t) * 1000
                if self._pending_double_click and gap_ms < cfg.double_click_window_ms:
                    self._pending_double_click = False
                    self._last_click_t = now
                    return GestureEvent(gesture=GestureState.DOUBLE_CLICK, action=ActionType.DOUBLE_CLICK, x=x, y=y)
                self._pending_double_click = True
            else:
                held_ms = (now - self._pinch_start_t) * 1000
                if held_ms >= cfg.drag_hold_ms and not self._drag_active and cfg.gesture_drag:
                    self._drag_active = True
                    self._pending_double_click = False
                    return GestureEvent(gesture=GestureState.DRAG_START, action=ActionType.MOUSE_DOWN, x=x, y=y)
                elif self._drag_active:
                    return GestureEvent(gesture=GestureState.DRAG_ACTIVE, action=ActionType.MOVE_MOUSE, x=x, y=y)
        else:
            if self._pinch_was_active:
                self._pinch_was_active = False
                if self._drag_active:
                    self._drag_active = False
                    return GestureEvent(gesture=GestureState.IDLE, action=ActionType.MOUSE_UP, x=x, y=y)
                else:
                    gap_ms = (now - self._last_click_t) * 1000
                    if gap_ms >= cfg.click_cooldown_ms:
                        self._last_click_t = now
                        return GestureEvent(gesture=GestureState.LEFT_CLICK, action=ActionType.LEFT_CLICK, x=x, y=y)

        # ── 9. Right Click (Middle-Thumb Pinch) ────────────────────────────────
        if is_pinching_r and cfg.gesture_right_click:
            gap_ms = (now - self._last_right_click_t) * 1000
            if gap_ms >= cfg.click_cooldown_ms:
                self._last_right_click_t = now
                return GestureEvent(gesture=GestureState.RIGHT_CLICK, action=ActionType.RIGHT_CLICK, x=x, y=y)

        # ── 10. Pointer Movement (Index Pointing) ──────────────────────────────
        if i_ext and not is_pinching_l:
            self._state = GestureState.POINTING
            return GestureEvent(gesture=GestureState.POINTING, action=ActionType.MOVE_MOUSE, x=x, y=y)

        self._state = GestureState.IDLE
        return None

    def toggle_pause(self):
        self._is_paused = not self._is_paused

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def current_state(self) -> GestureState:
        return self._state

    def update_config(self, cfg: Config):
        self._cfg = cfg
