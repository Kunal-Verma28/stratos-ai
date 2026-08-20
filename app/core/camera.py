"""
OpenCV Camera Manager — handles camera selection, frame grabbing, and reconnection.
Runs on a dedicated background thread and exposes the latest frame via a thread-safe property.
"""
import cv2
import threading
import time
import numpy as np
from typing import Optional

from app.utils.logger import logger
from app.config import Config


class CameraManager:
    """
    Non-blocking camera capture using a daemon thread.
    Continuously reads frames in the background.
    """

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Open the camera and start the capture thread. Returns True on success."""
        if not self._open_camera():
            return False
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="CameraThread")
        self._thread.start()
        logger.info(f"Camera started: index={self._cfg.camera_index}")
        return True

    def stop(self):
        """Stop capture thread and release camera."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap and self._cap.isOpened():
            self._cap.release()
        logger.info("Camera stopped.")

    @property
    def frame(self) -> Optional[np.ndarray]:
        """Thread-safe access to the latest captured frame."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    @property
    def is_running(self) -> bool:
        return self._running

    def _open_camera(self) -> bool:
        idx = self._cfg.camera_index
        logger.info(f"Opening camera index {idx} ...")
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            logger.warning(f"Could not open camera {idx}, trying index 0 ...")
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                logger.error("No camera available.")
                return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self._cfg.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._cfg.camera_height)
        cap.set(cv2.CAP_PROP_FPS,          self._cfg.camera_fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)   # Minimize buffer to avoid stale frames
        self._cap = cap
        return True

    def _capture_loop(self):
        consecutive_failures = 0
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                logger.warning("Camera disconnected, attempting reconnect in 2s ...")
                time.sleep(2.0)
                self._open_camera()
                continue

            ret, frame = self._cap.read()
            if ret:
                with self._lock:
                    self._frame = frame
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures > 30:
                    logger.error("Camera feed lost. Attempting reconnect ...")
                    self._cap.release()
                    self._cap = None
                    consecutive_failures = 0

    @staticmethod
    def list_available_cameras(max_test: int = 5) -> list[int]:
        """Probe camera indices 0..max_test and return those that open successfully."""
        available = []
        for i in range(max_test):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
