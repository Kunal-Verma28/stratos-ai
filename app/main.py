"""
Hand Gesture Control — Application Entry Point.

IMPORTANT: mediapipe and cv2 MUST be imported before PySide6 to avoid
the PySide6 shiboken `six`-module interceptor conflict with python-dateutil.
"""
import sys
import threading
import time
from typing import Optional

# ── CRITICAL: Import vision libs BEFORE PySide6 ───────────────────────────
import cv2                    # noqa: F401
import mediapipe              # noqa: F401  — must load before PySide6

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal, QObject
import keyboard               # global hotkeys

from app.config import get_config, Config
from app.core.camera import CameraManager
from app.core.detector import HandDetector
from app.core.filters import SmoothPoint
from app.core.coordinate_mapper import CoordinateMapper
from app.gestures.recognizer import GestureRecognizer
from app.gestures.gesture_types import GestureState, ActionType, GestureEvent
from app.controller.mouse_controller import MouseController
from app.controller.keyboard_controller import KeyboardController
from app.controller.system_controller import SystemController
from app.ui.main_window import MainWindow
from app.ui.hud_overlay import HUDOverlay
from app.ui.tray_icon import TrayIcon
from app.utils.logger import logger


# ─────────────────────────────────────────────────────────────────────────────
# Vision Pipeline Worker Thread
# Runs: camera read → detect → smooth → recognize → dispatch → HUD update
# ─────────────────────────────────────────────────────────────────────────────

class VisionWorker(QObject):
    """
    Full computer-vision pipeline running on a dedicated QThread.
    Communicates with the UI thread via Qt signals.
    """
    gesture_detected = Signal(GestureState)   # → HUD overlay
    paused_changed   = Signal(bool)            # → main window status
    error_occurred   = Signal(str)

    def __init__(self, cfg: Config):
        super().__init__()
        self._cfg = cfg
        self._running = False
        self._loop_thread: Optional[threading.Thread] = None
        self._camera    = CameraManager(cfg)
        self._detector  = HandDetector(cfg)
        self._smoother  = SmoothPoint(min_cutoff=cfg.smoothing_min_cutoff, beta=cfg.smoothing_beta)
        self._mapper    = CoordinateMapper(cfg)
        self._recognizer= GestureRecognizer(cfg)
        self._mouse     = MouseController()
        self._keyboard  = KeyboardController()
        self._system    = SystemController()
        self.camera     = self._camera       # expose for UI preview
        self.recognizer = self._recognizer   # expose for live calibration telemetry

    def start_pipeline(self):
        """Called from UI thread → starts camera then runs the vision loop in a thread."""
        if self._running:
            return
        if not self._camera.start():
            self.error_occurred.emit("Could not open webcam. Check camera connection and permissions.")
            return
        self._running = True
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True, name="VisionLoopThread")
        self._loop_thread.start()
        logger.info("Vision pipeline started.")

    def stop_pipeline(self):
        self._running = False
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=1.5)
        self._mouse.emergency_release()
        self._camera.stop()
        logger.info("Vision pipeline stopped.")

    def toggle_pause(self):
        self._recognizer.toggle_pause()
        paused = self._recognizer.is_paused
        if paused:
            self._mouse.emergency_release()
        self.paused_changed.emit(paused)
        self.gesture_detected.emit(GestureState.PAUSED if paused else GestureState.IDLE)

    def update_config(self, cfg: Config):
        self._cfg = cfg
        self._detector.update_config(cfg)
        self._mapper.update_config(cfg)
        self._recognizer.update_config(cfg)
        self._smoother.update_params(cfg.smoothing_min_cutoff, cfg.smoothing_beta)

    def _run_loop(self):
        """Main vision loop — runs until stop_pipeline() is called."""
        no_hand_frames = 0

        while self._running:
            frame = self._camera.frame
            if frame is None:
                time.sleep(0.005)
                continue

            # ── Hand Detection ────────────────────────────────────────────────
            result = self._detector.process_frame(frame)

            if result is None:
                no_hand_frames += 1
                if no_hand_frames > 30:
                    # Auto-release buttons if hand disappears
                    self._mouse.emergency_release()
                    no_hand_frames = 0
                time.sleep(0.005)
                continue
            no_hand_frames = 0

            lms = result.landmarks

            # ── Smooth index fingertip coordinates ────────────────────
            raw_x = lms[8][0]   # LM.INDEX_TIP x (normalized 0..1)
            raw_y = lms[8][1]   # LM.INDEX_TIP y
            sx, sy = self._smoother.filter(raw_x, raw_y)

            # ── Map to screen ─────────────────────────────────────────────────
            screen_x, screen_y = self._mapper.map(sx, sy)

            # ── Gesture Recognition ───────────────────────────────────────────
            event = self._recognizer.process(lms, (screen_x, screen_y))

            if event:
                self._dispatch(event)
                self.gesture_detected.emit(event.gesture)

    def _dispatch(self, event: GestureEvent):
        """Map GestureEvent → OS action."""
        a = event.action
        x, y = event.x, event.y
        cfg = self._cfg

        if a == ActionType.MOVE_MOUSE:
            self._mouse.move(x, y)

        elif a == ActionType.LEFT_CLICK:
            self._mouse.left_click(x, y, cfg.click_lock_ms)

        elif a == ActionType.RIGHT_CLICK:
            self._mouse.right_click(x, y, cfg.click_lock_ms)

        elif a == ActionType.DOUBLE_CLICK:
            self._mouse.double_click(x, y)

        elif a == ActionType.MOUSE_DOWN:
            self._mouse.mouse_down(x, y)

        elif a == ActionType.MOUSE_UP:
            self._mouse.mouse_up(x, y)

        elif a == ActionType.SCROLL_UP:
            self._mouse.scroll(-event.delta)

        elif a == ActionType.SCROLL_DOWN:
            self._mouse.scroll(event.delta)

        elif a == ActionType.NEXT_SLIDE:
            self._keyboard.next_slide()

        elif a == ActionType.PREV_SLIDE:
            self._keyboard.prev_slide()

        elif a == ActionType.CUSTOM_HOTKEY:
            self._keyboard.dispatch_custom(event.custom_key)

        elif a == ActionType.SCREENSHOT:
            self._system.screenshot()

        elif a == ActionType.VOLUME_UP:
            self._system.volume_up()

        elif a == ActionType.VOLUME_DOWN:
            self._system.volume_down()

        elif a == ActionType.MUTE_TOGGLE:
            self._system.mute_toggle()

        elif a == ActionType.MEDIA_PLAY_PAUSE:
            self._system.media_play_pause()

        elif a == ActionType.TOGGLE_PAUSE:
            self.toggle_pause()


# ─────────────────────────────────────────────────────────────────────────────
# Application Bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("Hand Gesture Control — Starting up")
    logger.info("=" * 60)

    cfg = get_config()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # Keep running in tray when window closes

    # ── Worker + Thread setup ─────────────────────────────────────────────────
    worker = VisionWorker(cfg)
    vision_thread = QThread()
    worker.moveToThread(vision_thread)
    vision_thread.start()

    # ── UI Components ─────────────────────────────────────────────────────────
    hud    = HUDOverlay(opacity=cfg.hud_opacity)
    tray   = TrayIcon()
    window = MainWindow(cfg, worker.camera, worker.recognizer)

    if cfg.show_hud_overlay:
        hud.show_hud()
    tray.show()
    window.show()

    # ── Signal wiring ─────────────────────────────────────────────────────────
    # UI → Worker
    window.start_engine.connect(worker.start_pipeline)
    window.stop_engine.connect(worker.stop_pipeline)
    window.config_changed.connect(worker.update_config)

    # Worker → UI
    worker.gesture_detected.connect(hud.set_gesture)
    worker.paused_changed.connect(window.set_paused)
    worker.paused_changed.connect(tray.set_paused)
    worker.error_occurred.connect(
        lambda msg: logger.error(f"Vision error: {msg}")
    )

    # Tray
    tray.pause_toggled.connect(worker.toggle_pause)
    tray.open_settings.connect(window.show)
    tray.quit_requested.connect(app.quit)

    # ── Global Hotkeys (F8 = pause, Ctrl+Shift+Q = quit) ──────────────────────
    def _setup_hotkeys():
        try:
            keyboard.add_hotkey(cfg.pause_hotkey,   worker.toggle_pause,   suppress=False)
            keyboard.add_hotkey(cfg.quit_hotkey,    app.quit,              suppress=False)
            logger.info(f"Hotkeys registered: pause={cfg.pause_hotkey}, quit={cfg.quit_hotkey}")
        except Exception as e:
            logger.warning(f"Could not register hotkeys: {e} (run as administrator for global hotkeys)")

    hotkey_thread = threading.Thread(target=_setup_hotkeys, daemon=True)
    hotkey_thread.start()

    # ── Cleanup on exit ───────────────────────────────────────────────────────
    def _cleanup():
        logger.info("Shutting down...")
        worker.stop_pipeline()
        vision_thread.quit()
        vision_thread.wait(3000)
        cfg.save()

    app.aboutToQuit.connect(_cleanup)

    logger.info("UI ready. Waiting for user to start gesture control.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
