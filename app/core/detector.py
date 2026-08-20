"""
MediaPipe Hand Detector Wrapper using MediaPipe Tasks API (v1.0+).
Extracts 21 3D hand landmarks and handedness per frame.
Designed to run on a dedicated background thread.
"""
import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from dataclasses import dataclass
from typing import Optional

from app.utils.logger import logger
from app.config import Config

# Standard 21 Hand Landmark connections for skeleton drawing
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Pinky
]

@dataclass
class HandResult:
    """Processed result from one video frame."""
    landmarks: list          # List of 21 np.ndarray [x, y, z] in [0..1]
    handedness: str          # "Left" or "Right"
    confidence: float        # Detection confidence score
    frame_rgb: np.ndarray    # Original frame
    annotated: np.ndarray    # Frame with skeleton drawn on it


class HandDetector:
    """
    Wraps MediaPipe HandLandmarker Tasks API.
    Call process_frame() with a BGR frame from OpenCV.
    """

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._landmarker: Optional[vision.HandLandmarker] = None
        self._model_path = self._resolve_model_path()
        self._init_model()

    def _resolve_model_path(self) -> str:
        # Check assets folder in workspace or app directory
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "hand_landmarker.task"),
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "hand_landmarker.task"),
            "assets/hand_landmarker.task",
        ]
        for path in candidates:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                return abs_path
        
        # If not found, fallback to downloading
        out_path = os.path.abspath(candidates[0])
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        logger.info(f"Downloading hand_landmarker model to {out_path}...")
        urllib.request.urlretrieve(url, out_path)
        return out_path

    def _init_model(self):
        logger.info(f"Initializing MediaPipe HandLandmarker Tasks API from {self._model_path} (max_hands={self._cfg.max_hands})")
        base_options = python.BaseOptions(model_asset_path=self._model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=self._cfg.max_hands,
            min_hand_detection_confidence=self._cfg.min_detection_confidence,
            min_hand_presence_confidence=self._cfg.min_detection_confidence,
            min_tracking_confidence=self._cfg.min_tracking_confidence,
            running_mode=vision.RunningMode.IMAGE
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def process_frame(self, bgr_frame: np.ndarray) -> Optional[HandResult]:
        """
        Detect hands in a BGR camera frame.
        Returns HandResult if a hand is found, otherwise None.
        """
        # Flip horizontally so movement matches a mirror view
        frame = cv2.flip(bgr_frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        detection_result = self._landmarker.detect(mp_image)

        annotated = frame.copy()
        h, w = frame.shape[:2]

        if not detection_result.hand_landmarks:
            return None

        target_hand = self._cfg.control_hand

        for idx, (hand_lms, handedness_cats) in enumerate(zip(
            detection_result.hand_landmarks,
            detection_result.handedness
        )):
            category = handedness_cats[0]
            label = category.category_name if hasattr(category, 'category_name') else category.display_name
            score = category.score

            # In flipped image, inverted handedness from model:
            detected = "Right" if label == "Left" else "Left"

            # Draw skeleton on annotated frame
            coords = []
            for lm in hand_lms:
                cx, cy = int(lm.x * w), int(lm.y * h)
                coords.append((cx, cy))
                cv2.circle(annotated, (cx, cy), 4, (0, 255, 0), -1)

            for start, end in HAND_CONNECTIONS:
                if start < len(coords) and end < len(coords):
                    cv2.line(annotated, coords[start], coords[end], (255, 200, 0), 2)

            # Filter for requested control hand
            if detected != target_hand and len(detection_result.hand_landmarks) > 1:
                continue

            lms = [
                np.array([lm.x, lm.y, lm.z], dtype=np.float32)
                for lm in hand_lms
            ]

            return HandResult(
                landmarks=lms,
                handedness=detected,
                confidence=score,
                frame_rgb=rgb,
                annotated=annotated,
            )

        # Fallback to first hand if control hand wasn't strictly matched
        if detection_result.hand_landmarks:
            hand_lms = detection_result.hand_landmarks[0]
            category = detection_result.handedness[0][0]
            label = category.category_name if hasattr(category, 'category_name') else category.display_name
            detected = "Right" if label == "Left" else "Left"
            lms = [
                np.array([lm.x, lm.y, lm.z], dtype=np.float32)
                for lm in hand_lms
            ]
            return HandResult(
                landmarks=lms,
                handedness=detected,
                confidence=category.score,
                frame_rgb=rgb,
                annotated=annotated,
            )

        return None

    def update_config(self, cfg: Config):
        """Hot-reload configuration."""
        self._cfg = cfg
        if self._landmarker:
            self._landmarker.close()
        self._init_model()

    def close(self):
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
