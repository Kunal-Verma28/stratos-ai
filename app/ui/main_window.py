"""
SpatialPoint AI™ Pro — Enterprise Main Dashboard & Calibration Suite
Production Edition v1.0.0-PRO
Copyright (c) 2026 SpatialPoint Technologies. All rights reserved.
"""
import os
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QCheckBox, QComboBox,
    QGroupBox, QScrollArea, QFrame, QTabWidget, QSizePolicy,
    QSpinBox, QDoubleSpinBox, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPixmap, QFont, QIcon, QColor

from app.config import Config, APP_NAME, APP_VERSION, APP_TAGLINE, APP_ORGANIZATION, APP_COPYRIGHT
from app.core.camera import CameraManager

# Enterprise Dark Glassmorphism Theme
ENTERPRISE_STYLE = """
QMainWindow, QWidget {
    background-color: #0b0f17;
    color: #e2e8f0;
    font-family: "Segoe UI", "Inter", -apple-system, sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #1e293b;
    border-radius: 10px;
    background-color: #111827;
    margin-top: 14px;
    padding: 14px;
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #10b981;
}
QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 9px 18px;
    color: #f1f5f9;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #10b981;
}
QPushButton:pressed {
    background-color: #0f172a;
}
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
    color: #ffffff;
    border: none;
    font-size: 13px;
    font-weight: 700;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
}
QPushButton#danger {
    background: #dc2626;
    color: #ffffff;
    border: none;
    font-weight: 700;
}
QPushButton#danger:hover {
    background: #ef4444;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #10b981;
    border: 2px solid #ffffff;
    border-radius: 9px;
    width: 18px;
    height: 18px;
    margin: -6px 0;
}
QSlider::sub-page:horizontal {
    background: #10b981;
    border-radius: 3px;
}
QCheckBox {
    spacing: 8px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 1px solid #475569;
    background-color: #1e293b;
}
QCheckBox::indicator:checked {
    background-color: #10b981;
    border-color: #10b981;
}
QComboBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 7px;
    padding: 7px 12px;
    color: #f1f5f9;
}
QComboBox::drop-down {
    border: none;
}
QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 10px;
    background-color: #0f172a;
    padding: 6px;
}
QTabBar::tab {
    background: #111827;
    color: #64748b;
    padding: 10px 22px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #0f172a;
    color: #10b981;
    border-bottom: 2px solid #10b981;
}
QTabBar::tab:hover:!selected {
    background: #1e293b;
    color: #94a3b8;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
"""

class MainWindow(QMainWindow):
    """
    Primary settings & control window.
    Tabs: Vision Workspace | Gesture Matrix | Precision Filters | System Diagnostics
    """
    start_engine   = Signal()
    stop_engine    = Signal()
    config_changed = Signal(Config)

    def __init__(self, cfg: Config, camera: CameraManager):
        super().__init__()
        self._cfg = cfg
        self._camera = camera
        self._engine_running = False
        self._preview_timer = QTimer()
        self._preview_timer.timeout.connect(self._update_preview)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(f"{APP_NAME} — {APP_TAGLINE}")
        self.setMinimumSize(960, 680)
        self.setStyleSheet(ENTERPRISE_STYLE)

        # Set application window icon if available
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── Professional Header ───────────────────────────────────────────────
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_row = QHBoxLayout()
        title = QLabel(APP_NAME)
        title.setFont(QFont("Segoe UI", 19, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff;")
        title_row.addWidget(title)

        badge = QLabel(f" {APP_VERSION} ")
        badge.setStyleSheet("""
            background-color: #064e3b;
            color: #34d399;
            border: 1px solid #059669;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 6px;
        """)
        title_row.addWidget(badge)
        title_row.addStretch()
        title_box.addLayout(title_row)

        tagline = QLabel(APP_TAGLINE)
        tagline.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        title_box.addWidget(tagline)
        header.addLayout(title_box)
        header.addStretch()

        # Engine Status Pill
        self._status_pill = QLabel("● ENGINE OFFLINE")
        self._status_pill.setStyleSheet("""
            background-color: #1e293b;
            color: #94a3b8;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 7px 18px;
            font-size: 12px;
            font-weight: 700;
        """)
        header.addWidget(self._status_pill)
        root.addLayout(header)

        # ── Control Action Bar ────────────────────────────────────────────────
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(12)

        self._start_btn = QPushButton("▶  Start Tracking Engine")
        self._start_btn.setObjectName("primary")
        self._start_btn.setMinimumHeight(44)
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self._start)
        btn_bar.addWidget(self._start_btn, 2)

        self._stop_btn = QPushButton("■  Stop Engine")
        self._stop_btn.setObjectName("danger")
        self._stop_btn.setMinimumHeight(44)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.clicked.connect(self._stop)
        btn_bar.addWidget(self._stop_btn, 1)
        root.addLayout(btn_bar)

        # ── Main Tabs ─────────────────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.addTab(self._build_preview_tab(),     "📷  Vision Workspace")
        tabs.addTab(self._build_gestures_tab(),    "🖐  Gesture Matrix")
        tabs.addTab(self._build_sensitivity_tab(), "⚡  Precision & Filters")
        tabs.addTab(self._build_about_tab(),       "ℹ  System & About")
        root.addWidget(tabs)

    # ── Tab 1: Vision Workspace ───────────────────────────────────────────────

    def _build_preview_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Video Preview Viewport
        self._cam_label = QLabel("Camera feed viewport — Click 'Start Tracking Engine' to activate")
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_label.setStyleSheet("""
            background-color: #020617;
            border: 2px dashed #1e293b;
            border-radius: 10px;
            color: #475569;
            font-size: 13px;
        """)
        self._cam_label.setMinimumHeight(380)
        layout.addWidget(self._cam_label)

        # Hardware Selector & Settings Row
        opts_row = QHBoxLayout()
        opts_row.setSpacing(16)

        cam_box = QHBoxLayout()
        cam_lbl = QLabel("Video Input Device:")
        cam_lbl.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        cam_box.addWidget(cam_lbl)
        
        self._cam_combo = QComboBox()
        self._cam_combo.addItems([f"Webcam {i} (DirectShow)" for i in range(4)])
        self._cam_combo.setCurrentIndex(self._cfg.camera_index)
        self._cam_combo.currentIndexChanged.connect(self._on_camera_change)
        cam_box.addWidget(self._cam_combo)
        opts_row.addLayout(cam_box)

        hand_box = QHBoxLayout()
        hand_lbl = QLabel("Active Control Hand:")
        hand_lbl.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        hand_box.addWidget(hand_lbl)

        self._hand_combo = QComboBox()
        self._hand_combo.addItems(["Right", "Left"])
        self._hand_combo.setCurrentText(self._cfg.control_hand)
        self._hand_combo.currentTextChanged.connect(self._on_hand_change)
        hand_box.addWidget(self._hand_combo)
        opts_row.addLayout(hand_box)

        opts_row.addStretch()
        layout.addLayout(opts_row)

        info_bar = QLabel("⚡ Active Workspace Zone: Position your hand inside the green bounded rectangle for full desktop reach.")
        info_bar.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(info_bar)
        return w

    # ── Tab 2: Gesture Control Matrix ─────────────────────────────────────────

    def _build_gestures_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        gestures = [
            ("gesture_left_click",   "👆 Left Click",         "Index + Thumb Pinch",           "Performs primary mouse click with anti-drift coordinate freeze."),
            ("gesture_right_click",  "✌ Right Click",        "Middle + Thumb Pinch",          "Opens context menu while index remains extended."),
            ("gesture_double_click", "⚡ Rapid Double Click", "2 Consecutive Pinches",         "Fast folder, app, or link execution within 350ms window."),
            ("gesture_drag",         "✊ Drag & Hold",        "Pinch held > 350ms",            "Window dragging, text selection, and object placement."),
            ("gesture_scroll",       "↕ Precision Scroll",   "Index + Middle Parallel Rise",   "Fluid vertical web and document scrolling."),
            ("gesture_screenshot",   "🖐 Instant Screenshot", "Open Palm (5 Extended Fingers)","Dispatches PrtSc snapshot with 500ms safety cooldown."),
            ("gesture_media",        "🎵 Media Hotkeys",      "Fist & Custom Triggers",        "Simulates Play/Pause and track advancement keys."),
        ]

        grp = QGroupBox("Active Gesture Recognition Mapping")
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(10)

        for key, label, trigger, desc in gestures:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(10, 6, 10, 6)

            cb = QCheckBox(label)
            cb.setStyleSheet("font-weight: 700; color: #f8fafc;")
            cb.setChecked(getattr(self._cfg, key))
            cb.stateChanged.connect(lambda v, k=key: self._toggle_gesture(k, bool(v)))
            card_layout.addWidget(cb, 2)

            trig_badge = QLabel(trigger)
            trig_badge.setStyleSheet("""
                background-color: #0f172a;
                color: #38bdf8;
                border: 1px solid #0284c7;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
            """)
            card_layout.addWidget(trig_badge, 2)

            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
            card_layout.addWidget(desc_lbl, 4)

            grp_layout.addWidget(card)

        layout.addWidget(grp)

        # Global Hotkey Safeguards
        hotkey_grp = QGroupBox("Safety Hotkeys & Emergency Standby")
        hk_layout = QGridLayout(hotkey_grp)
        hk_layout.addWidget(QLabel("Global Standby Toggle:"), 0, 0)
        hk_layout.addWidget(QLabel("<b>F8</b>  <i>(Freezes/resumes tracking instantly)</i>"), 0, 1)
        hk_layout.addWidget(QLabel("Physical Gesture Standby:"), 1, 0)
        hk_layout.addWidget(QLabel("<b>Closed Fist</b>  <i>(Hold 1.0 second)</i>"), 1, 1)
        hk_layout.addWidget(QLabel("Emergency Application Exit:"), 2, 0)
        hk_layout.addWidget(QLabel("<b>Ctrl + Shift + Q</b>"), 2, 1)
        layout.addWidget(hotkey_grp)

        layout.addStretch()
        scroll.setWidget(w)
        return scroll

    # ── Tab 3: Precision & Dynamic Filters ─────────────────────────────────────

    def _build_sensitivity_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        # Cursor Kinetics
        kin_grp = QGroupBox("Cursor Kinetics & Acceleration")
        kin_layout = QVBoxLayout(kin_grp)

        kin_layout.addWidget(QLabel("Cursor Velocity Multiplier:"))
        self._sens_slider = QSlider(Qt.Orientation.Horizontal)
        self._sens_slider.setRange(50, 300)
        self._sens_slider.setValue(int(self._cfg.cursor_sensitivity * 100))
        self._sens_label = QLabel(f"{self._cfg.cursor_sensitivity:.1f}×")
        self._sens_label.setStyleSheet("color: #10b981; font-weight: bold; min-width: 45px;")
        self._sens_slider.valueChanged.connect(
            lambda v: (setattr(self._cfg, "cursor_sensitivity", v/100),
                       self._sens_label.setText(f"{v/100:.1f}×"),
                       self.config_changed.emit(self._cfg))
        )
        row1 = QHBoxLayout()
        row1.addWidget(self._sens_slider)
        row1.addWidget(self._sens_label)
        kin_layout.addLayout(row1)

        kin_layout.addWidget(QLabel("One-Euro Adaptive Smoothing (Lower = Ultra Smooth):"))
        self._smooth_slider = QSlider(Qt.Orientation.Horizontal)
        self._smooth_slider.setRange(10, 300)
        self._smooth_slider.setValue(int(self._cfg.smoothing_min_cutoff * 100))
        self._smooth_label = QLabel(f"{self._cfg.smoothing_min_cutoff:.2f}")
        self._smooth_label.setStyleSheet("color: #10b981; font-weight: bold; min-width: 45px;")
        self._smooth_slider.valueChanged.connect(
            lambda v: (setattr(self._cfg, "smoothing_min_cutoff", v/100),
                       self._smooth_label.setText(f"{v/100:.2f}"),
                       self.config_changed.emit(self._cfg))
        )
        row2 = QHBoxLayout()
        row2.addWidget(self._smooth_slider)
        row2.addWidget(self._smooth_label)
        kin_layout.addLayout(row2)
        layout.addWidget(kin_grp)

        # Pinch Biometrics
        bio_grp = QGroupBox("Pinch Biometric Activation")
        bio_layout = QVBoxLayout(bio_grp)
        bio_layout.addWidget(QLabel("Pinch Activation Proximity (Normalized Distance Threshold):"))
        self._pinch_slider = QSlider(Qt.Orientation.Horizontal)
        self._pinch_slider.setRange(20, 120)
        self._pinch_slider.setValue(int(self._cfg.pinch_threshold * 1000))
        self._pinch_label = QLabel(f"{self._cfg.pinch_threshold:.3f}")
        self._pinch_label.setStyleSheet("color: #10b981; font-weight: bold; min-width: 45px;")
        self._pinch_slider.valueChanged.connect(
            lambda v: (setattr(self._cfg, "pinch_threshold", v/1000),
                       self._pinch_label.setText(f"{v/1000:.3f}"),
                       self.config_changed.emit(self._cfg))
        )
        row3 = QHBoxLayout()
        row3.addWidget(self._pinch_slider)
        row3.addWidget(self._pinch_label)
        bio_layout.addLayout(row3)
        layout.addWidget(bio_grp)

        # Save Action Button
        save_btn = QPushButton("💾  Save Enterprise Profile")
        save_btn.setObjectName("primary")
        save_btn.setMinimumHeight(40)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        layout.addStretch()
        return w

    # ── Tab 4: System & About ─────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        about_grp = QGroupBox("Software Architecture & Telemetry")
        abt_layout = QVBoxLayout(about_grp)
        abt_layout.setSpacing(8)

        abt_layout.addWidget(QLabel(f"<b>Application:</b> {APP_NAME} ({APP_VERSION})"))
        abt_layout.addWidget(QLabel(f"<b>Organization:</b> {APP_ORGANIZATION}"))
        abt_layout.addWidget(QLabel("<b>Vision Engine:</b> Google MediaPipe Tasks API v1.0.1 (21 3D Landmarks)"))
        abt_layout.addWidget(QLabel("<b>Input Subsystem:</b> Windows Direct User32 SendInput (Zero-Latency)"))
        abt_layout.addWidget(QLabel("<b>Signal Processing:</b> Adaptive One-Euro ($1€$) Velocity Filter"))
        abt_layout.addWidget(QLabel("<b>Privacy Guarantee:</b> 100% Local On-Device Inference. Zero Cloud Uploads."))
        layout.addWidget(about_grp)

        lic_grp = QGroupBox("Legal & Compliance")
        lic_layout = QVBoxLayout(lic_grp)
        lic_layout.addWidget(QLabel(APP_COPYRIGHT))
        lic_layout.addWidget(QLabel("Licensed for Enterprise, Personal, and Accessibility Use."))
        layout.addWidget(lic_grp)

        layout.addStretch()
        return w

    # ── Internal Actions & Slots ──────────────────────────────────────────────

    def _start(self):
        self._engine_running = True
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_pill.setText("● ENGINE ACTIVE")
        self._status_pill.setStyleSheet("""
            background-color: #064e3b;
            color: #34d399;
            border: 1px solid #059669;
            border-radius: 16px;
            padding: 7px 18px;
            font-size: 12px;
            font-weight: 700;
        """)
        self._preview_timer.start(33)
        self.start_engine.emit()

    def _stop(self):
        self._engine_running = False
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_pill.setText("● ENGINE OFFLINE")
        self._status_pill.setStyleSheet("""
            background-color: #1e293b;
            color: #94a3b8;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 7px 18px;
            font-size: 12px;
            font-weight: 700;
        """)
        self._preview_timer.stop()
        self.stop_engine.emit()

    def _on_camera_change(self, idx: int):
        self._cfg.camera_index = idx
        self.config_changed.emit(self._cfg)

    def _on_hand_change(self, hand: str):
        self._cfg.control_hand = hand
        self.config_changed.emit(self._cfg)

    def _toggle_gesture(self, key: str, val: bool):
        setattr(self._cfg, key, val)
        self.config_changed.emit(self._cfg)

    def _save_settings(self):
        self._cfg.save()
        QMessageBox.information(self, "Profile Saved", "Enterprise settings profile successfully updated.")

    @Slot()
    def _update_preview(self):
        """Grab latest camera frame and display in viewport."""
        frame = self._camera.frame
        if frame is None:
            return
        h, w = frame.shape[:2]
        cfg = self._cfg
        x1 = int(cfg.zone_left   * w)
        y1 = int(cfg.zone_top    * h)
        x2 = int(cfg.zone_right  * w)
        y2 = int(cfg.zone_bottom * h)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (16, 185, 129), 2)
        cv2.putText(frame, "SPATIAL ACTIVE ZONE", (x1 + 6, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (16, 185, 129), 1)

        rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
        h2, w2, ch = rgb.shape
        qt_img = QImage(rgb.data, w2, h2, ch * w2, QImage.Format.Format_RGB888)
        scaled = qt_img.scaled(
            self._cam_label.width(), self._cam_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._cam_label.setPixmap(QPixmap.fromImage(scaled))

    def set_paused(self, paused: bool):
        if paused:
            self._status_pill.setText("⏸ ENGINE STANDBY")
            self._status_pill.setStyleSheet("""
                background-color: #78350f;
                color: #fbbf24;
                border: 1px solid #d97706;
                border-radius: 16px;
                padding: 7px 18px;
                font-size: 12px;
                font-weight: 700;
            """)
        else:
            self._status_pill.setText("● ENGINE ACTIVE")
            self._status_pill.setStyleSheet("""
                background-color: #064e3b;
                color: #34d399;
                border: 1px solid #059669;
                border-radius: 16px;
                padding: 7px 18px;
                font-size: 12px;
                font-weight: 700;
            """)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
