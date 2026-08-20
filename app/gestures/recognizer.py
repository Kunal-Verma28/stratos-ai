"""
STRATOS™ AI — High-Precision Gesture Recognition State Machine
Production-tuned thresholds and robust multi-mode action dispatching.
"""
import time
from collections import deque
from typing import Optional

from app.config import Config
from app.utils.math_helpers import (
    LM, normalized_distance, get_finger_states, count_extended_fingers,
    palm_center, thumb_vertical_direction, thumb_extended, cursor_control_point
)
from app.gestures.gesture_types import GestureState, ActionType, GestureEvent, OperationMode


class GestureRecognizer:

    def __init__(self, cfg: Config):
        self._cfg = cfg

        # Timers (perf_counter seconds)
        self._pinch_start_t:       float = 0.0
        self._last_click_t:        float = 0.0
        self._last_right_click_t:  float = 0.0
        self._fist_start_t:        float = 0.0
        self._last_action_t:       float = 0.0
        self._last_swipe_t:        float = 0.0

        # State flags
        self._is_paused:           bool  = False
        self._drag_active:         bool  = False
        self._pinch_was_active:    bool  = False
        self._pending_dbl_click:   bool  = False
        self._state                       = GestureState.IDLE

        # Scroll accumulator
        self._scroll_ref_y:        float = 0.0
        self._scroll_acc:          float = 0.0

        # Palm history for swipe velocity (deque of (x, timestamp))
        self._palm_hist: deque = deque(maxlen=12)

        # Exposed telemetry for Calibration Wizard & UI meters
        self._last_pinch_dist:     float = 0.0

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def last_pinch_distance(self) -> float:
        return self._last_pinch_dist

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def current_state(self) -> GestureState:
        return self._state

    def toggle_pause(self):
        self._is_paused = not self._is_paused
        self._state = GestureState.PAUSED if self._is_paused else GestureState.IDLE

    def update_config(self, cfg: Config):
        self._cfg = cfg

    # ── Main Process Loop ──────────────────────────────────────────────────────

    def process(self, lms: list, screen_xy: tuple) -> Optional[GestureEvent]:
        """
        Consume 21 MediaPipe landmarks + mapped screen (x, y).
        Returns a GestureEvent or None.
        """
        now  = time.perf_counter()
        cfg  = self._cfg
        x, y = screen_xy
        mode = cfg.operation_mode

        # ── Track palm for swipe detection ────────────────────────────────────
        pc = palm_center(lms)
        self._palm_hist.append((float(pc[0]), now))

        # ── Finger & pinch measurements ───────────────────────────────────────
        t_ext, i_ext, m_ext, r_ext, p_ext = get_finger_states(lms)
        n_ext = sum((t_ext, i_ext, m_ext, r_ext, p_ext))

        pinch_l = normalized_distance(lms, LM.THUMB_TIP, LM.INDEX_TIP)
        pinch_r = normalized_distance(lms, LM.THUMB_TIP, LM.MIDDLE_TIP)
        self._last_pinch_dist = pinch_l

        is_pinch_l = pinch_l < cfg.pinch_threshold
        # Right pinch: Middle touches thumb while Index finger is UP
        is_pinch_r = (pinch_r < cfg.right_click_threshold and pinch_l > (cfg.pinch_threshold * 1.1) and i_ext)

        # ════ 1. FIST HOLD — Standby / Mode Action ════════════════════════════
        if n_ext == 0 and not is_pinch_l:
            if self._fist_start_t == 0.0:
                self._fist_start_t = now
            elif (now - self._fist_start_t) * 1000 >= cfg.fist_pause_hold_ms:
                self._fist_start_t = 0.0
                if mode == "Desktop Navigation":
                    self._is_paused = not self._is_paused
                    self._state = GestureState.PAUSED if self._is_paused else GestureState.IDLE
                    return GestureEvent(gesture=GestureState.PAUSED, action=ActionType.TOGGLE_PAUSE)
                elif mode == "Presentation Remote":
                    return GestureEvent(gesture=GestureState.FIST, action=ActionType.CUSTOM_HOTKEY, custom_key="b")
                elif mode == "Media Controller":
                    if (now - self._last_action_t) * 1000 >= cfg.gesture_cooldown_ms:
                        self._last_action_t = now
                        return GestureEvent(gesture=GestureState.FIST, action=ActionType.MEDIA_PLAY_PAUSE)
        else:
            self._fist_start_t = 0.0

        if self._is_paused:
            return None

        # ════ 2. OPEN PALM (4 or 5 fingers extended) — Screenshot ══════════════
        if (n_ext >= 4 and i_ext and m_ext and r_ext and p_ext and not is_pinch_l):
            if cfg.gesture_screenshot and (now - self._last_action_t) * 1000 >= cfg.gesture_cooldown_ms:
                self._last_action_t = now
                self._state = GestureState.OPEN_PALM
                return GestureEvent(gesture=GestureState.OPEN_PALM, action=ActionType.SCREENSHOT)

        # ════ 3. SWIPE (fast horizontal palm displacement) ════════════════════
        if cfg.gesture_swipes and len(self._palm_hist) >= 6:
            dt = self._palm_hist[-1][1] - self._palm_hist[0][1]
            if 0.06 < dt < 0.40:
                dx       = self._palm_hist[-1][0] - self._palm_hist[0][0]
                velocity = dx / dt
                if (abs(velocity) > cfg.swipe_velocity_threshold
                        and (now - self._last_swipe_t) * 1000 >= 750):
                    self._last_swipe_t = now
                    self._palm_hist.clear()
                    if velocity > 0:
                        action = ActionType.NEXT_SLIDE if mode == "Presentation Remote" else ActionType.CUSTOM_HOTKEY
                        return GestureEvent(gesture=GestureState.SWIPE_RIGHT, action=action,
                                            custom_key=cfg.custom_swipe_right)
                    else:
                        action = ActionType.PREV_SLIDE if mode == "Presentation Remote" else ActionType.CUSTOM_HOTKEY
                        return GestureEvent(gesture=GestureState.SWIPE_LEFT, action=action,
                                            custom_key=cfg.custom_swipe_left)

        # ════ 4. THUMBS UP / DOWN ═════════════════════════════════════════════
        if cfg.gesture_thumbs and t_ext and not (i_ext or m_ext or r_ext or p_ext):
            thumb_dir = thumb_vertical_direction(lms)
            cd = (now - self._last_action_t) * 1000 >= cfg.gesture_cooldown_ms
            if thumb_dir == "up" and cd:
                self._last_action_t = now
                action = ActionType.NEXT_SLIDE if mode == "Presentation Remote" else ActionType.CUSTOM_HOTKEY
                return GestureEvent(gesture=GestureState.THUMBS_UP, action=action,
                                    custom_key=cfg.custom_thumbs_up)
            if thumb_dir == "down" and cd:
                self._last_action_t = now
                action = ActionType.PREV_SLIDE if mode == "Presentation Remote" else ActionType.CUSTOM_HOTKEY
                return GestureEvent(gesture=GestureState.THUMBS_DOWN, action=action,
                                    custom_key=cfg.custom_thumbs_down)

        # ════ 5. THREE / FOUR FINGERS (Desktop shortcuts: Copy/Paste) ═════════
        if cfg.gesture_three_four_fingers and mode == "Desktop Navigation":
            cd = (now - self._last_action_t) * 1000 >= 650
            if i_ext and m_ext and r_ext and not p_ext and not t_ext and cd:
                self._last_action_t = now
                return GestureEvent(gesture=GestureState.THREE_FINGERS,
                                    action=ActionType.CUSTOM_HOTKEY,
                                    custom_key=cfg.custom_three_fingers)
            if i_ext and m_ext and r_ext and p_ext and not t_ext and cd:
                self._last_action_t = now
                return GestureEvent(gesture=GestureState.FOUR_FINGERS,
                                    action=ActionType.CUSTOM_HOTKEY,
                                    custom_key=cfg.custom_four_fingers)

        # ════ 6. SCROLL — Peace sign (Index + Middle extended together) ════════
        peace_mode = (i_ext and m_ext and not r_ext and not p_ext
                      and normalized_distance(lms, LM.INDEX_TIP, LM.MIDDLE_TIP) < cfg.scroll_fingers_threshold)

        if peace_mode and cfg.gesture_scroll:
            mid_y = (lms[LM.INDEX_TIP][1] + lms[LM.MIDDLE_TIP][1]) * 0.5
            if self._state != GestureState.SCROLL_ACTIVE:
                self._state        = GestureState.SCROLL_ACTIVE
                self._scroll_ref_y = mid_y
                self._scroll_acc   = 0.0
            else:
                dy = (mid_y - self._scroll_ref_y) * 14.0
                self._scroll_acc  += dy
                self._scroll_ref_y = mid_y
                steps = int(self._scroll_acc)
                if steps != 0:
                    self._scroll_acc -= steps
                    action = ActionType.SCROLL_DOWN if steps > 0 else ActionType.SCROLL_UP
                    return GestureEvent(gesture=GestureState.SCROLL_ACTIVE,
                                        action=action,
                                        delta=abs(steps) * cfg.scroll_sensitivity)
            return None

        # ════ 7. RIGHT PINCH — Context Menu Click ═════════════════════════════
        if is_pinch_r and cfg.gesture_right_click:
            gap_ms = (now - self._last_right_click_t) * 1000
            if gap_ms >= cfg.click_cooldown_ms:
                self._last_right_click_t = now
                self._state = GestureState.RIGHT_CLICK
                return GestureEvent(gesture=GestureState.RIGHT_CLICK,
                                    action=ActionType.RIGHT_CLICK, x=x, y=y)
            return None

        # ════ 8. LEFT PINCH — Click / Double-Click / Drag & Drop ═══════════════
        if is_pinch_l and cfg.gesture_left_click:
            if not self._pinch_was_active:
                self._pinch_was_active = True
                self._pinch_start_t    = now
                gap_ms = (now - self._last_click_t) * 1000
                if self._pending_dbl_click and gap_ms < cfg.double_click_window_ms:
                    self._pending_dbl_click = False
                    self._last_click_t = now
                    self._state = GestureState.DOUBLE_CLICK
                    return GestureEvent(gesture=GestureState.DOUBLE_CLICK,
                                        action=ActionType.DOUBLE_CLICK, x=x, y=y)
                self._pending_dbl_click = True
            else:
                held_ms = (now - self._pinch_start_t) * 1000
                if held_ms >= cfg.drag_hold_ms and not self._drag_active and cfg.gesture_drag:
                    self._drag_active       = True
                    self._pending_dbl_click = False
                    self._state = GestureState.DRAG_ACTIVE
                    return GestureEvent(gesture=GestureState.DRAG_START,
                                        action=ActionType.MOUSE_DOWN, x=x, y=y)
                if self._drag_active:
                    self._state = GestureState.DRAG_ACTIVE
                    return GestureEvent(gesture=GestureState.DRAG_ACTIVE,
                                        action=ActionType.MOVE_MOUSE, x=x, y=y)
            return None  # Pinching actively: cursor stays locked in place

        else:
            if self._pinch_was_active:
                self._pinch_was_active = False
                if self._drag_active:
                    self._drag_active = False
                    self._state = GestureState.IDLE
                    return GestureEvent(gesture=GestureState.IDLE,
                                        action=ActionType.MOUSE_UP, x=x, y=y)
                gap_ms = (now - self._last_click_t) * 1000
                if gap_ms >= cfg.click_cooldown_ms:
                    self._last_click_t = now
                    self._state = GestureState.LEFT_CLICK
                    return GestureEvent(gesture=GestureState.LEFT_CLICK,
                                        action=ActionType.LEFT_CLICK, x=x, y=y)

        # ════ 9. POINTING — Smooth Cursor Navigation ══════════════════════════
        if i_ext and not is_pinch_l:
            self._state = GestureState.POINTING
            return GestureEvent(gesture=GestureState.POINTING,
                                action=ActionType.MOVE_MOUSE, x=x, y=y)

        self._state = GestureState.IDLE
        return None
