"""
SpatialPoint AI™ Pro — Windows System Tray Integration
Provides background residency, instant standby toggling, and fast preferences access.
"""
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtCore import Signal

from app.config import APP_NAME, APP_VERSION


def _make_icon(color: str = "#10b981") -> QIcon:
    """Generate high-DPI colored indicator icon for the Windows taskbar tray."""
    pix = QPixmap(32, 32)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(QColor("#ffffff"))
    painter.drawEllipse(3, 3, 26, 26)
    painter.end()
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    """
    Windows system tray icon with context menu.
    """
    pause_toggled  = Signal()
    open_settings  = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = False
        self._active_icon = _make_icon("#10b981")   # Emerald = active
        self._paused_icon = _make_icon("#ef4444")   # Crimson = standby
        self.setIcon(self._active_icon)
        self.setToolTip(f"{APP_NAME} ({APP_VERSION}) — Active")
        self._build_menu()
        self.activated.connect(self._on_activate)

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
                padding: 6px;
                border-radius: 8px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1e293b;
                color: #10b981;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 4px 8px;
            }
        """)

        # App Title item (disabled header)
        header_action = menu.addAction(f"✋ {APP_NAME}")
        header_action.setEnabled(False)
        menu.addSeparator()

        self._pause_action = menu.addAction("⏸  Standby (Pause Tracking)")
        self._pause_action.triggered.connect(self._toggle_pause)

        menu.addSeparator()
        settings_action = menu.addAction("⚙  Preferences & Dashboard")
        settings_action.triggered.connect(self.open_settings.emit)

        menu.addSeparator()
        quit_action = menu.addAction("✕  Exit Application")
        quit_action.triggered.connect(self.quit_requested.emit)

        self.setContextMenu(menu)

    def _toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self.setIcon(self._paused_icon)
            self.setToolTip(f"{APP_NAME} — STANDBY")
            self._pause_action.setText("▶  Resume Tracking Engine")
        else:
            self.setIcon(self._active_icon)
            self.setToolTip(f"{APP_NAME} — Active")
            self._pause_action.setText("⏸  Standby (Pause Tracking)")
        self.pause_toggled.emit()

    def _on_activate(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_pause()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings.emit()

    def set_paused(self, paused: bool):
        if paused != self._paused:
            self._toggle_pause()
