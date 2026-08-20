"""
Gesture Recognizer — Full rule-based geometric state machine.

Each frame:
  1. Compute normalized distances & finger states from hand landmarks.
  2. Feed into the state machine which tracks timing, debounce & hysteresis.
  3. Emit zero or one GestureEvent per frame.

Design principles:
  - Normalized distances: immune to hand-camera distance variation.
  - State hysteresis: gesture must cross threshold + confirmation gap before changing state.
  - Cooldown timers: prevent trigger spam / accidental double-fires.
  - Coordinate Lock: freeze cursor on pinch initiation to prevent click-drift.
"""
import time
from typing import Optional

from app.config import Config
from app.utils.math_helpers import (
    LM, normalized_distance, finger_extended, thumb_extended,
    count_extended_fingers, palm_center
)
from app.gestures.gesture_types import GestureState, ActionType, GestureEvent


class GestureRecognizer:

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._state = GestureState.IDLE
        self._prev_state = GestureState.IDLE

        # Timing trackers (all in seconds via perf_counter)
        self._pinch_start_t: float = 0.0
        self._pinch_release_t: float = 0.0
        self._last_click_t: float = 0.0
        self._last_right_click_t: float = 0.0
        self._fist_start_t: float = 0.0
        self._last_gesture_t: float = 0.0        # general cooldown

        # State flags
        self._is_paused: bool = False
        self._drag_active: bool = False
        self._last_scroll_y: float = 0.0
        self._scroll_ref_y: float = 0.0
        self._pending_double_click: bool = False
        self._pinch_was_active: bool = False

        # Scroll accumulator for smooth scrolling
        self._scroll_acc: float = 0.0

    def process(self, lms: list, screen_xy: tuple[int, int]) -> Optional[GestureEvent]:
        """
        Process one frame's landmarks and return a GestureEvent (or None).

        lms       — list of 21 np.ndarray [x, y, z]  (normalized 0..1)
        screen_xy — already mapped (x, y) screen pixel coordinates
        """
        now = time.perf_counter()
        cfg = self._cfg
        x, y = screen_xy

        # ── Pause/Resume via fist ──────────────────────────────────────────────
        n_ext = count_extended_fingers(lms)
        if n_ext == 0:  # Fist
            if self._fist_start_t == 0.0:
                self._fist_start_t = now
            elif (now - self._fist_start_t) * 1000 >= cfg.fist_pause_hold_ms:
                self._fist_start_t = 0.0
                self._is_paused = not self._is_paused
                self._state = GestureState.PAUSED if self._is_paused else GestureState.IDLE
                return GestureEvent(
                    gesture=GestureState.PAUSED,
                    action=ActionType.TOGGLE_PAUSE,
                )
        else:
            self._fist_start_t = 0.0

        if self._is_paused:
            return None

        # ── Compute normalized pinch distances ─────────────────────────────────
        pinch_l = normalized_distance(lms, LM.THUMB_TIP, LM.INDEX_TIP)   # Left click
        pinch_r = normalized_distance(lms, LM.THUMB_TIP, LM.MIDDLE_TIP)  # Right click

        idx_ext    = finger_extended(lms, LM.INDEX_TIP,  LM.INDEX_PIP,  LM.INDEX_MCP)
        mid_ext    = finger_extended(lms, LM.MIDDLE_TIP, LM.MIDDLE_PIP, LM.MIDDLE_MCP)
        ring_ext   = finger_extended(lms, LM.RING_TIP,   LM.RING_PIP,   LM.RING_MCP)
        pinky_ext  = finger_extended(lms, LM.PINKY_TIP,  LM.PINKY_PIP,  LM.PINKY_MCP)
        thumb_ext  = thumb_extended(lms)

        is_pinching_l = pinch_l < cfg.pinch_threshold
        is_pinching_r = (pinch_r < cfg.right_click_threshold
                         and not is_pinching_l
                         and idx_ext)

        peace_mode = (idx_ext and mid_ext
                      and not ring_ext and not pinky_ext
                      and normalized_distance(lms, LM.INDEX_TIP, LM.MIDDLE_TIP) < cfg.scroll_fingers_threshold)

        # ── Open Palm → Screenshot ─────────────────────────────────────────────
        if n_ext == 5:
            if (now - self._last_gesture_t) * 1000 >= cfg.gesture_cooldown_ms and cfg.gesture_screenshot:
                self._last_gesture_t = now
                return GestureEvent(
                    gesture=GestureState.OPEN_PALM,
                    action=ActionType.SCREENSHOT,
                )

        # ── Scroll Mode (Peace Sign: Index + Middle together) ─────────────────
        if peace_mode and cfg.gesture_scroll:
            mid_y = (lms[LM.INDEX_TIP][1] + lms[LM.MIDDLE_TIP][1]) / 2.0
            if self._state != GestureState.SCROLL_ACTIVE:
                self._state = GestureState.SCROLL_ACTIVE
                self._scroll_ref_y = mid_y
                self._scroll_acc = 0.0
            else:
                dy = (mid_y - self._scroll_ref_y) * 10.0   # scale
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

        # ── Left Pinch Logic (Click, Double Click, Drag) ───────────────────────
        if is_pinching_l and cfg.gesture_left_click:
            if not self._pinch_was_active:
                # Pinch just started
                self._pinch_was_active = True
                self._pinch_start_t = now

                # Double-click detection
                gap_ms = (now - self._last_click_t) * 1000
                if self._pending_double_click and gap_ms < cfg.double_click_window_ms:
                    self._pending_double_click = False
                    self._last_click_t = now
                    return GestureEvent(
                        gesture=GestureState.DOUBLE_CLICK,
                        action=ActionType.DOUBLE_CLICK,
                        x=x, y=y,
                    )
                self._pending_double_click = True

            else:
                # Pinch held — check for drag
                held_ms = (now - self._pinch_start_t) * 1000
                if held_ms >= cfg.drag_hold_ms and not self._drag_active and cfg.gesture_drag:
                    self._drag_active = True
                    self._pending_double_click = False
                    return GestureEvent(
                        gesture=GestureState.DRAG_START,
                        action=ActionType.MOUSE_DOWN,
                        x=x, y=y,
                    )
                elif self._drag_active:
                    return GestureEvent(
                        gesture=GestureState.DRAG_ACTIVE,
                        action=ActionType.MOVE_MOUSE,
                        x=x, y=y,
                    )
        else:
            if self._pinch_was_active:
                # Pinch just released
                self._pinch_was_active = False
                if self._drag_active:
                    self._drag_active = False
                    return GestureEvent(
                        gesture=GestureState.IDLE,
                        action=ActionType.MOUSE_UP,
                        x=x, y=y,
                    )
                else:
                    # Regular click on release
                    gap_ms = (now - self._last_click_t) * 1000
                    if gap_ms >= cfg.click_cooldown_ms:
                        self._last_click_t = now
                        return GestureEvent(
                            gesture=GestureState.LEFT_CLICK,
                            action=ActionType.LEFT_CLICK,
                            x=x, y=y,
                        )

        # ── Right Click (Middle-Thumb Pinch) ───────────────────────────────────
        if is_pinching_r and cfg.gesture_right_click:
            gap_ms = (now - self._last_right_click_t) * 1000
            if gap_ms >= cfg.click_cooldown_ms:
                self._last_right_click_t = now
                return GestureEvent(
                    gesture=GestureState.RIGHT_CLICK,
                    action=ActionType.RIGHT_CLICK,
                    x=x, y=y,
                )

        # ── Cursor Move (Index Pointing) ───────────────────────────────────────
        if idx_ext and not is_pinching_l:
            self._state = GestureState.POINTING
            return GestureEvent(
                gesture=GestureState.POINTING,
                action=ActionType.MOVE_MOUSE,
                x=x, y=y,
            )

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
