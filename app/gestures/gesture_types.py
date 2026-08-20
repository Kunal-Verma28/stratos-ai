"""
STRATOS™ AI — Gesture Types & Enums
Defines operation modes, gesture states, OS actions, and event structures.
"""
from enum import Enum, auto
from dataclasses import dataclass, field
import time


class OperationMode(Enum):
    """Active operating mode profile."""
    DESKTOP      = "Desktop Navigation"   # Standard mouse, clicks, scrolling, drag-drop
    PRESENTATION = "Presentation Remote"  # Slide next/prev, laser pointer, blank screen
    MEDIA        = "Media Controller"     # Play/pause, volume, seek, mute


class GestureState(Enum):
    """The currently recognized gesture or idle state."""
    IDLE           = auto()   # No recognized posture
    POINTING       = auto()   # Index finger extended → cursor control
    LEFT_CLICK     = auto()   # Index-Thumb pinch triggered
    RIGHT_CLICK    = auto()   # Middle-Thumb pinch triggered
    DOUBLE_CLICK   = auto()   # Two quick pinches
    DRAG_START     = auto()   # Pinch held > drag_hold_ms
    DRAG_ACTIVE    = auto()   # Currently dragging
    SCROLL_ACTIVE  = auto()   # Index + Middle peace sign → scroll
    PEACE_SIGN     = auto()   # Two fingers up
    THREE_FINGERS  = auto()   # 3 fingers (Index + Middle + Ring) → e.g. Copy
    FOUR_FINGERS   = auto()   # 4 fingers extended → e.g. Paste
    THUMBS_UP      = auto()   # Thumb pointing up, others folded
    THUMBS_DOWN    = auto()   # Thumb pointing down, others folded
    SWIPE_LEFT     = auto()   # Fast left hand swipe → Previous
    SWIPE_RIGHT    = auto()   # Fast right hand swipe → Next
    FIST           = auto()   # All fingers curled → pause/resume or play/pause
    OPEN_PALM      = auto()   # All fingers extended → screenshot / stop
    PAUSED         = auto()   # Tracking engine manually paused


class ActionType(Enum):
    """OS-level actions dispatched by the action engine."""
    NONE             = auto()
    MOVE_MOUSE       = auto()
    LEFT_CLICK       = auto()
    RIGHT_CLICK      = auto()
    DOUBLE_CLICK     = auto()
    MOUSE_DOWN       = auto()
    MOUSE_UP         = auto()
    SCROLL_UP        = auto()
    SCROLL_DOWN      = auto()
    SCROLL_LEFT      = auto()
    SCROLL_RIGHT     = auto()
    SCREENSHOT       = auto()
    VOLUME_UP        = auto()
    VOLUME_DOWN      = auto()
    MUTE_TOGGLE      = auto()
    MEDIA_PLAY_PAUSE = auto()
    MEDIA_NEXT       = auto()
    MEDIA_PREV       = auto()
    NEXT_SLIDE       = auto()
    PREV_SLIDE       = auto()
    CUSTOM_HOTKEY    = auto()
    TOGGLE_PAUSE     = auto()   # Pause / resume the tracking engine


@dataclass
class GestureEvent:
    """A recognized gesture event to be dispatched."""
    gesture: GestureState
    action:  ActionType
    x: int = 0                  # Screen x coordinate (if applicable)
    y: int = 0                  # Screen y coordinate (if applicable)
    delta: int = 0              # Scroll delta, volume steps, etc.
    custom_key: str = ""        # Key string for CUSTOM_HOTKEY (e.g. "ctrl+c")
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.perf_counter)
