from __future__ import annotations

import logging
import sys

import cv2
import numpy as np

from instant_transmission.sinks import PyVirtualCamSink, VirtualCamSink, open_pyvirtualcam_sink
from instant_transmission.virtual_cam import (
    detect_obs,
    format_setup_guidance,
    preferred_backend,
    preferred_linux_device,
    prime_obs_virtual_camera,
)

_log = logging.getLogger(__name__)
_PREVIEW_WINDOW = "shunkan-ido"


class FrameOutput:
    def __init__(
        self,
        width: int,
        height: int,
        fps: int,
        show_preview: bool = True,
        virtual_camera: bool = False,
        virtual_backend: str | None = None,
        *,
        auto_prime: bool = True,
        sink: VirtualCamSink | None = None,
    ) -> None:
        self._width = width
        self._height = height
        self._show_preview = show_preview
        self._fps = fps
        self._virtual_backend = virtual_backend
        self._sink: VirtualCamSink | None = None
        self._last_open_error: BaseException | None = None

        if sink is not None:
            self._sink = sink
            return
        if not virtual_camera:
            return
        if not self._try_open_virtual_camera():
            self._handle_open_failure(auto_prime=auto_prime)

    def _resolve_backend_and_device(self) -> tuple[str | None, str | None]:
        if sys.platform.startswith("linux"):
            backend = self._virtual_backend or "v4l2loopback"
            return backend, preferred_linux_device()
        backend = self._virtual_backend or preferred_backend()
        return backend, None

    def _try_open_virtual_camera(self) -> bool:
        try:
            backend, device = self._resolve_backend_and_device()
            self._sink = open_pyvirtualcam_sink(
                self._width,
                self._height,
                self._fps,
                backend=backend,
                device=device,
            )
            _log.info(
                "Virtual camera ready (%s). In Zoom/Teams/Meet pick this device.",
                self._sink.device_name,
            )
            return True
        except Exception as exc:
            self._sink = None
            self._last_open_error = exc
            return False

    def _handle_open_failure(self, *, auto_prime: bool) -> None:
        exc = self._last_open_error
        if auto_prime and sys.platform == "win32":
            status = detect_obs()
            if status.installed:
                _log.warning(
                    "warning: virtual camera unavailable (%s); attempting one-time OBS prime…",
                    exc,
                )
                if prime_obs_virtual_camera(status) and self._try_open_virtual_camera():
                    return
                exc = self._last_open_error

        self._sink = None
        _log.warning(
            "warning: virtual camera unavailable (%s); continuing preview-only\n%s",
            exc,
            format_setup_guidance(open_failed=True),
        )

    def send(self, frame_bgr: np.ndarray) -> None:
        frame = frame_bgr
        height, width = frame.shape[:2]
        if width != self._width or height != self._height:
            frame = cv2.resize(frame, (self._width, self._height))

        if self._show_preview:
            cv2.imshow(_PREVIEW_WINDOW, frame)

        if self._sink is None:
            return
        try:
            self._sink.send(frame)
        except Exception as exc:
            self._disable_virtual_camera(exc)

    def close(self) -> None:
        self._disable_virtual_camera(None)
        if self._show_preview:
            try:
                cv2.destroyWindow(_PREVIEW_WINDOW)
            except cv2.error:
                pass

    def _disable_virtual_camera(self, exc: BaseException | None) -> None:
        sink = self._sink
        self._sink = None
        if exc is not None:
            _log.warning(
                "warning: virtual camera unavailable (%s); continuing preview-only",
                exc,
            )
        if sink is None:
            return
        try:
            sink.close()
        except Exception:
            _log.warning("warning: failed to close virtual camera", exc_info=True)


# Re-export for type checkers / tests that may patch the sink class.
__all__ = ["FrameOutput", "PyVirtualCamSink"]
