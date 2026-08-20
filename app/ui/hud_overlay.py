"""
STRATOS™ AI — Enterprise Real-Time HUD Overlay
Transparent, click-through, always-on-top gesture telemetry status pill.
"""
from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from app.gestures.gesture_types import GestureState

# Executive color-coded status badges
GESTURE_INFO: dict[GestureState, tuple[str, str, str]] = {
    GestureState.IDLE:          ("●  STRATOS READY",      "#475569", "#0f172a"),
    GestureState.POINTING:      ("☝  CURSOR ACTIVE",     "#10b981", "#064e3b"),
    GestureState.LEFT_CLICK:    ("👆 PRIMARY CLICK",      "#38bdf8", "#0369a1"),
    GestureState.RIGHT_CLICK:   ("✌  CONTEXT CLICK",     "#f59e0b", "#78350f"),
    GestureState.DOUBLE_CLICK:  ("⚡ DOUBLE CLICK",       "#a855f7", "#581c87"),
    GestureState.DRAG_START:    ("✊ DRAG ENGAGED",       "#ef4444", "#7f1d1d"),
    GestureState.DRAG_ACTIVE:   ("✊ DRAGGING OBJECT",    "#ef4444", "#7f1d1d"),
    GestureState.SCROLL_ACTIVE: ("↕  PRECISION SCROLL",  "#06b6d4", "#164e63"),
    GestureState.PEACE_SIGN:    ("✌  SCROLL MODE",        "#06b6d4", "#164e63"),
    GestureState.THREE_FINGERS: ("📋 3-FINGER (COPY)",    "#10b981", "#064e3b"),
    GestureState.FOUR_FINGERS:  ("📋 4-FINGER (PASTE)",   "#38bdf8", "#0369a1"),
    GestureState.THUMBS_UP:     ("👍 THUMBS UP",          "#10b981", "#064e3b"),
    GestureState.THUMBS_DOWN:   ("👎 THUMBS DOWN",        "#f59e0b", "#78350f"),
    GestureState.SWIPE_LEFT:    ("◀ SWIPE PREVIOUS",     "#a855f7", "#581c87"),
    GestureState.SWIPE_RIGHT:   ("▶ SWIPE NEXT",         "#a855f7", "#581c87"),
    GestureState.FIST:          ("✊ STANDBY HOLD",       "#f97316", "#7c2d12"),
    GestureState.OPEN_PALM:     ("🖐 SNAPSHOT CAPTURED",  "#10b981", "#064e3b"),
    GestureState.PAUSED:        ("⏸  STANDBY (PAUSED)",   "#ef4444", "#450a0a"),
}


class HUDOverlay(QWidget):
    """
    Transparent floating gesture status pill.
    Always on top, click-through, zero window focus stealing.
    """

    update_signal = Signal(GestureState)

    def __init__(self, opacity: float = 0.90):
        super().__init__()
        self._current_state = GestureState.IDLE
        self._opacity = opacity
        self._setup_window()
        self._setup_label()
        self.update_signal.connect(self._on_gesture_update)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowOpacity(self._opacity)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.width() - 260, 24, 240, 48)

    def _setup_label(self):
        self._label = QLabel("●  STRATOS READY", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._label.setStyleSheet("""
            QLabel {
                color: #f1f5f9;
                background-color: rgba(15, 23, 42, 220);
                border: 1px solid #334155;
                border-radius: 24px;
                padding: 6px 16px;
                letter-spacing: 0.5px;
            }
        """)
        self._label.setGeometry(0, 0, 240, 48)

    @Slot(GestureState)
    def _on_gesture_update(self, state: GestureState):
        self._current_state = state
        text, border_color, bg_color = GESTURE_INFO.get(state, ("●  UNKNOWN", "#475569", "#0f172a"))
        self._label.setText(text)
        self._label.setStyleSheet(f"""
            QLabel {{
                color: #ffffff;
                background-color: rgba(11, 15, 23, 235);
                border: 2px solid {border_color};
                border-radius: 24px;
                padding: 6px 16px;
                letter-spacing: 0.5px;
            }}
        """)

    def set_gesture(self, state: GestureState):
        """Thread-safe update from background vision pipeline."""
        self.update_signal.emit(state)

    def show_hud(self):
        self.show()

    def hide_hud(self):
        self.hide()
