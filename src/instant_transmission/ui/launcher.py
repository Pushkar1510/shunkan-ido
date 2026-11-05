"""Polished PySide6 launcher window for Shunkan-Ido."""

from __future__ import annotations

import logging
import sys
from enum import Enum

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from instant_transmission.config import AppConfig
from instant_transmission.ui.assets import background_path, icon_path, logo_path
from instant_transmission.ui.worker import CamWorker
from instant_transmission.virtual_cam import (
    LOOPBACK_LABEL,
    detect_linux_loopback,
    run_platform_setup,
)

_log = logging.getLogger(__name__)

_INK = "#0B0E14"
_GOLD = "#F5C542"
_GOLD_DIM = "#C9A227"
_TEXT = "#F4F0E6"
_MUTED = "#B8B0A4"


class CamStatus(str, Enum):
    READY = "Ready"
    NEEDS_SETUP = "Needs setup"
    RUNNING = "Running"
    ERROR = "Error"


class _SetupThread(QThread):
    finished_ok = Signal(bool, str)

    def run(self) -> None:
        try:
            result = run_platform_setup()
            self.finished_ok.emit(result.ok, result.message)
        except Exception as exc:
            _log.exception("Setup failed")
            self.finished_ok.emit(False, str(exc))


class _Background(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        path = background_path()
        if path is not None:
            pm = QPixmap(str(path))
            if not pm.isNull():
                self._pixmap = pm

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self._pixmap is not None:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(self.rect(), QColor(_INK))
        # Legibility veil
        painter.fillRect(self.rect(), QColor(8, 10, 16, 140))


class LauncherWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Shunkan-Ido")
        self.setMinimumSize(960, 600)
        self.resize(1100, 680)

        icon = icon_path()
        if icon is not None:
            self.setWindowIcon(QIcon(str(icon)))

        self._worker = CamWorker(self)
        self._worker.finished.connect(self._handle_worker_finished)
        self._setup_thread: _SetupThread | None = None
        self._status = CamStatus.NEEDS_SETUP

        root = _Background()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(0)

        glass = QFrame()
        glass.setObjectName("glass")
        glass.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        glass_layout = QVBoxLayout(glass)
        glass_layout.setContentsMargins(36, 32, 36, 32)
        glass_layout.setSpacing(18)

        top = QHBoxLayout()
        logo = QLabel()
        logo_file = logo_path()
        if logo_file is not None:
            pm = QPixmap(str(logo_file))
            if not pm.isNull():
                logo.setPixmap(
                    pm.scaledToHeight(72, Qt.TransformationMode.SmoothTransformation)
                )
        top.addWidget(logo, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        top.addStretch(1)
        self._status_chip = QLabel("Needs setup")
        self._status_chip.setObjectName("statusChip")
        self._status_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self._status_chip, alignment=Qt.AlignmentFlag.AlignRight)
        glass_layout.addLayout(top)

        title = QLabel("SHUNKAN-IDO")
        title.setObjectName("heroTitle")
        title_font = QFont()
        title_font.setPointSize(36)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
        title.setFont(title_font)
        glass_layout.addWidget(title)

        tagline = QLabel("Instant Transmission for your meetings")
        tagline.setObjectName("tagline")
        glass_layout.addWidget(tagline)

        self._message = QLabel("")
        self._message.setObjectName("message")
        self._message.setWordWrap(True)
        glass_layout.addWidget(self._message)

        buttons = QHBoxLayout()
        buttons.setSpacing(16)
        self._setup_btn = QPushButton("Setup virtual camera")
        self._setup_btn.setObjectName("secondaryBtn")
        self._setup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_btn.clicked.connect(self._on_setup)
        buttons.addWidget(self._setup_btn)

        self._start_btn = QPushButton("Start calibrating")
        self._start_btn.setObjectName("primaryBtn")
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self._on_start_stop)
        buttons.addWidget(self._start_btn)
        glass_layout.addLayout(buttons)

        hint = QLabel(
            f"After Start, pick the camera named “{LOOPBACK_LABEL}” in Meet / Zoom / Teams."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        glass_layout.addWidget(hint)

        layout.addStretch(1)
        layout.addWidget(glass, alignment=Qt.AlignmentFlag.AlignBottom)

        self.setStyleSheet(
            f"""
            QFrame#glass {{
                background: rgba(11, 14, 20, 0.72);
                border: 1px solid rgba(245, 197, 66, 0.28);
                border-radius: 18px;
            }}
            QLabel#heroTitle {{
                color: {_TEXT};
            }}
            QLabel#tagline {{
                color: {_GOLD};
                font-size: 16px;
            }}
            QLabel#message {{
                color: {_MUTED};
                font-size: 13px;
                min-height: 36px;
            }}
            QLabel#hint {{
                color: {_MUTED};
                font-size: 12px;
            }}
            QLabel#statusChip {{
                color: {_INK};
                background: {_GOLD_DIM};
                border-radius: 12px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#primaryBtn {{
                background: {_GOLD};
                color: {_INK};
                border: none;
                border-radius: 12px;
                padding: 16px 28px;
                font-size: 16px;
                font-weight: 700;
                min-width: 200px;
            }}
            QPushButton#primaryBtn:hover {{
                background: #FFD56A;
            }}
            QPushButton#primaryBtn:pressed {{
                background: {_GOLD_DIM};
            }}
            QPushButton#primaryBtn:disabled {{
                background: #5a5344;
                color: #9a9388;
            }}
            QPushButton#secondaryBtn {{
                background: transparent;
                color: {_TEXT};
                border: 1px solid rgba(244, 240, 230, 0.45);
                border-radius: 12px;
                padding: 14px 22px;
                font-size: 14px;
                font-weight: 600;
                min-width: 180px;
            }}
            QPushButton#secondaryBtn:hover {{
                border-color: {_GOLD};
                color: {_GOLD};
            }}
            QPushButton#secondaryBtn:disabled {{
                color: #6e675c;
                border-color: #3a3630;
            }}
            """
        )

        effect = QGraphicsOpacityEffect(glass)
        glass.setGraphicsEffect(effect)
        self._fade = QPropertyAnimation(effect, b"opacity", self)
        self._fade.setDuration(650)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.start()

        self.refresh_status()

    def refresh_status(self) -> None:
        if self._worker.running:
            self._set_status(CamStatus.RUNNING, "Preview + virtual camera are live.")
            return
        if sys.platform.startswith("linux"):
            loop = detect_linux_loopback()
            if loop.device is not None:
                note = f"Virtual camera ready ({loop.device})"
                if loop.notes:
                    note = f"{note}. {loop.notes}"
                self._set_status(CamStatus.READY, note)
                return
            self._set_status(
                CamStatus.NEEDS_SETUP,
                loop.notes or "Run Setup virtual camera once (may ask for your password).",
            )
            return
        self._set_status(
            CamStatus.NEEDS_SETUP,
            "This launcher targets Ubuntu first; use CLI setup on other platforms for now.",
        )

    def _set_status(self, status: CamStatus, message: str = "") -> None:
        self._status = status
        self._status_chip.setText(status.value)
        self._message.setText(message)
        colors = {
            CamStatus.READY: (_INK, _GOLD),
            CamStatus.NEEDS_SETUP: (_TEXT, "#5C4A2A"),
            CamStatus.RUNNING: (_INK, "#7DDE92"),
            CamStatus.ERROR: (_TEXT, "#8B2E2E"),
        }
        fg, bg = colors[status]
        self._status_chip.setStyleSheet(
            f"color: {fg}; background: {bg}; border-radius: 12px; "
            f"padding: 6px 14px; font-weight: 600; font-size: 12px;"
        )
        running = status == CamStatus.RUNNING
        self._setup_btn.setEnabled(not running and self._setup_thread is None)
        self._start_btn.setText("Stop" if running else "Start calibrating")

    def _on_setup(self) -> None:
        if self._worker.running or self._setup_thread is not None:
            return
        self._setup_btn.setEnabled(False)
        self._message.setText("Setting up virtual camera…")
        thread = _SetupThread(self)
        self._setup_thread = thread
        thread.finished_ok.connect(self._on_setup_done)
        thread.start()

    def _on_setup_done(self, ok: bool, message: str) -> None:
        self._setup_thread = None
        self._setup_btn.setEnabled(True)
        if ok:
            self.refresh_status()
            self._message.setText(message)
        else:
            self._set_status(CamStatus.ERROR, message)
            QMessageBox.warning(self, "Setup failed", message)

    def _on_start_stop(self) -> None:
        if self._worker.running:
            self._worker.stop()
            self._message.setText("Stopping… close the preview with q/Esc if it stays open.")
            return

        if self._status == CamStatus.NEEDS_SETUP:
            reply = QMessageBox.question(
                self,
                "Virtual camera not ready",
                "Virtual camera still needs setup. Start preview anyway?\n\n"
                "For Meet/Zoom, run Setup first so “Shunkan-Ido” appears as a camera.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        config = AppConfig(virtual_camera=True)
        if not self._worker.start(config):
            return
        self._set_status(
            CamStatus.RUNNING,
            "Step out of frame, then press Space in the preview to calibrate.",
        )

    def _handle_worker_finished(self, code: int) -> None:
        if code != 0:
            self._set_status(CamStatus.ERROR, f"Camera session ended with code {code}.")
        else:
            self.refresh_status()
            self._message.setText("Session stopped.")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker.running:
            self._worker.stop()
        event.accept()
