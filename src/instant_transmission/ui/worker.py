"""Camera session for the launcher.

OpenCV HighGUI (and its Qt backend) must run on a process main thread. Spawning
``shunkan-ido`` as a child process keeps the PySide launcher responsive and
avoids QBasicTimer / thread-affinity crashes from ``cv2.imshow`` in a worker
thread.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from instant_transmission.config import AppConfig

_log = logging.getLogger(__name__)


def cam_argv(config: AppConfig) -> list[str]:
    """Build argv for a child Instant Transmission process (no program name)."""
    args = [
        "--camera",
        str(config.camera),
        "--width",
        str(config.width),
        "--height",
        str(config.height),
        "--fps",
        str(config.fps),
        "--calibration-seconds",
        str(config.calibration_seconds),
        "--sfx",
        str(config.sfx_path),
    ]
    if config.virtual_camera:
        args.append("--virtual-camera")
    if config.virtual_backend:
        args.extend(["--virtual-backend", config.virtual_backend])
    if not config.sfx_enabled:
        args.append("--no-sfx")
    return args


def cam_program() -> tuple[str, list[str]]:
    """Return (program, prefix_args) to invoke the CLI with this interpreter.

    Do not resolve() ``sys.executable``: a venv ``python`` is often a symlink
    into ``/usr/bin``, and resolving would miss the sibling console script.
    """
    script = Path(sys.executable).parent / "shunkan-ido"
    if script.is_file():
        return str(script), []
    return sys.executable, ["-m", "instant_transmission.main"]


class CamWorker(QObject):
    """Run Instant Transmission in a child process; emit ``finished`` on exit."""

    finished = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._proc: QProcess | None = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning

    def start(self, config: AppConfig) -> bool:
        if self.running:
            return False

        program, prefix = cam_program()
        args = [*prefix, *cam_argv(config)]
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.ForwardedChannels)
        proc.finished.connect(self._on_finished)
        self._proc = proc
        _log.info("Starting camera session: %s %s", program, " ".join(args))
        proc.start(program, args)
        if not proc.waitForStarted(8000):
            err = proc.errorString()
            _log.error("Failed to start camera session: %s", err)
            self._proc = None
            self.finished.emit(1)
            return False
        return True

    def stop(self) -> None:
        """Ask the child to exit (SIGTERM → same soft-stop as Ctrl+C)."""
        if not self.running or self._proc is None:
            return
        _log.info("Stopping camera session (pid=%s)", self._proc.processId())
        self._proc.terminate()

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._proc = None
        self.finished.emit(int(exit_code))
