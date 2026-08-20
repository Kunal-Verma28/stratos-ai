"""
Structured logging for the Hand Gesture Control application.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "gesture_control.log")


def setup_logger(name: str = "HandGesture", level: int = logging.DEBUG) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(level)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file handler (max 5MB × 3 backups)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


logger = setup_logger()
