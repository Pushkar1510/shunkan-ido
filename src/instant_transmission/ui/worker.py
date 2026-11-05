"""Background Instant Transmission loop for the launcher."""

from __future__ import annotations

import logging
import threading

from PySide6.QtCore import QObject, Signal

from instant_transmission.config import AppConfig
from instant_transmission.main import run as run_cam

_log = logging.getLogger(__name__)


class CamWorker(QObject):
    """Run ``main.run`` on a daemon thread; emit ``finished`` when it exits."""

    finished = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, config: AppConfig) -> bool:
        if self.running:
            return False

        def _target() -> None:
            code = 1
            try:
                code = run_cam(config)
            except Exception:
                _log.exception("Camera session failed")
                code = 1
            finally:
                self.finished.emit(code)

        self._thread = threading.Thread(target=_target, name="shunkan-cam", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Ask the cam loop to exit via the same flag used for Ctrl+C."""
        try:
            import instant_transmission.main as main_mod

            main_mod._stop_requested = True  # noqa: SLF001 — intentional soft stop
        except Exception:
            _log.warning("Could not signal camera stop", exc_info=True)
