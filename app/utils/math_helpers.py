"""
Math helpers — normalized distance and angle calculations for gesture recognition.
All distances are normalized relative to the hand's reference bone length,
making them invariant to how close/far the hand is from the camera.
"""
import math
import numpy as np
from typing import Sequence


# ── MediaPipe hand landmark indices ──────────────────────────────────────────
class LM:
    """MediaPipe 21-point hand landmark indices."""
    WRIST             = 0
    THUMB_CMC         = 1
    THUMB_MCP         = 2
    THUMB_IP          = 3
    THUMB_TIP         = 4
    INDEX_MCP         = 5
    INDEX_PIP         = 6
    INDEX_DIP         = 7
    INDEX_TIP         = 8
    MIDDLE_MCP        = 9
    MIDDLE_PIP        = 10
    MIDDLE_DIP        = 11
    MIDDLE_TIP        = 12
    RING_MCP          = 13
    RING_PIP          = 14
    RING_DIP          = 15
    RING_TIP          = 16
    PINKY_MCP         = 17
    PINKY_PIP         = 18
    PINKY_DIP         = 19
    PINKY_TIP         = 20


def landmark_to_array(lm) -> np.ndarray:
    """Convert a single MediaPipe NormalizedLandmark to numpy [x, y, z]."""
    return np.array([lm.x, lm.y, lm.z], dtype=np.float32)


def landmarks_to_list(hand_landmarks) -> list[np.ndarray]:
    """Convert all 21 landmarks to list of numpy arrays."""
    return [landmark_to_array(lm) for lm in hand_landmarks.landmark]


def euclidean_2d(a: np.ndarray, b: np.ndarray) -> float:
    """2D Euclidean distance between two landmark arrays (uses x, y only)."""
    return float(math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))


def euclidean_3d(a: np.ndarray, b: np.ndarray) -> float:
    """3D Euclidean distance between two landmark arrays."""
    return float(np.linalg.norm(a - b))


def hand_scale(lms: list[np.ndarray]) -> float:
    """
    Reference hand bone length: Wrist → Middle MCP.
    Divide all distance measurements by this to normalize for camera distance.
    """
    return max(euclidean_2d(lms[LM.WRIST], lms[LM.MIDDLE_MCP]), 1e-6)


def normalized_distance(lms: list[np.ndarray], idx_a: int, idx_b: int) -> float:
    """
    Distance between two landmarks, normalized by hand scale.
    Invariant to distance from camera.
    """
    scale = hand_scale(lms)
    return euclidean_2d(lms[idx_a], lms[idx_b]) / scale


def finger_extended(lms: list[np.ndarray], tip: int, pip: int, mcp: int) -> bool:
    """
    Return True if a finger is extended (tip is farther from wrist than pip).
    Uses Y-axis: smaller Y = higher on screen = farther from wrist in selfie view.
    """
    # tip above pip above mcp (in normalized image coords, y decreases upward)
    return lms[tip][1] < lms[pip][1] < lms[mcp][1]


def thumb_extended(lms: list[np.ndarray]) -> bool:
    """Return True if thumb tip is far from index MCP (simple heuristic)."""
    return euclidean_2d(lms[LM.THUMB_TIP], lms[LM.INDEX_MCP]) > \
           euclidean_2d(lms[LM.THUMB_IP],  lms[LM.INDEX_MCP])


def count_extended_fingers(lms: list[np.ndarray]) -> int:
    """Return number of fingers currently extended (0-5)."""
    fingers = [
        finger_extended(lms, LM.INDEX_TIP,  LM.INDEX_PIP,  LM.INDEX_MCP),
        finger_extended(lms, LM.MIDDLE_TIP, LM.MIDDLE_PIP, LM.MIDDLE_MCP),
        finger_extended(lms, LM.RING_TIP,   LM.RING_PIP,   LM.RING_MCP),
        finger_extended(lms, LM.PINKY_TIP,  LM.PINKY_PIP,  LM.PINKY_MCP),
    ]
    return int(thumb_extended(lms)) + sum(fingers)


def palm_center(lms: list[np.ndarray]) -> np.ndarray:
    """Average of palm landmarks (rough center of palm)."""
    palm_ids = [LM.WRIST, LM.INDEX_MCP, LM.MIDDLE_MCP, LM.RING_MCP, LM.PINKY_MCP]
    pts = np.stack([lms[i] for i in palm_ids])
    return pts.mean(axis=0)
