from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

from instant_transmission.virtual_cam import (
    detect_obs,
    format_setup_guidance,
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
    ) -> None:
        self._width = width
        self._height = height
        self._show_preview = show_preview
        self._cam: Any = None
        self._fps = fps
        self._virtual_backend = virtual_backend

        if not virtual_camera:
            return
        if not self._try_open_virtual_camera():
            self._handle_open_failure(auto_prime=auto_prime)

    def _try_open_virtual_camera(self) -> bool:
        try:
            import pyvirtualcam
            from pyvirtualcam import PixelFormat
            from pyvirtualcam.camera import BACKENDS

            # Unknown names raise inside Camera.__init__ before _backend exists,
            # and Camera.__del__ then prints an AttributeError. Reject them first.
            if self._virtual_backend and self._virtual_backend not in BACKENDS:
                available = ", ".join(sorted(BACKENDS)) or "none"
                raise RuntimeError(
                    f"unknown virtual camera backend {self._virtual_backend!r} "
                    f"(available: {available})"
                )

            kwargs: dict[str, str] = {}
            if self._virtual_backend:
                kwargs["backend"] = self._virtual_backend
            self._cam = pyvirtualcam.Camera(
                self._width,
                self._height,
                self._fps,
                fmt=PixelFormat.BGR,
                **kwargs,
            )
            _log.info(
                "Virtual camera ready (%s). In Zoom/Teams/Meet pick "
                "OBS Virtual Camera (or your loopback device on Linux).",
                getattr(self._cam, "device", "active"),
            )
            return True
        except Exception as exc:
            self._cam = None
            self._last_open_error = exc
            return False

    def _handle_open_failure(self, *, auto_prime: bool) -> None:
        exc = getattr(self, "_last_open_error", None)
        status = detect_obs()
        if (
            auto_prime
            and status.installed
            and status.platform in ("darwin", "win32")
        ):
            _log.warning(
                "warning: virtual camera unavailable (%s); attempting one-time OBS prime…",
                exc,
            )
            if prime_obs_virtual_camera(status) and self._try_open_virtual_camera():
                return
            exc = getattr(self, "_last_open_error", exc)

        self._cam = None
        _log.warning(
            "warning: virtual camera unavailable (%s); continuing preview-only\n%s",
            exc,
            format_setup_guidance(status, open_failed=True),
        )

    def send(self, frame_bgr: np.ndarray) -> None:
        frame = frame_bgr
        height, width = frame.shape[:2]
        if width != self._width or height != self._height:
            frame = cv2.resize(frame, (self._width, self._height))

        if self._show_preview:
            cv2.imshow(_PREVIEW_WINDOW, frame)

        if self._cam is None:
            return
        try:
            self._cam.send(np.ascontiguousarray(frame))
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
        cam = self._cam
        self._cam = None
        if exc is not None:
            _log.warning(
                "warning: virtual camera unavailable (%s); continuing preview-only",
                exc,
            )
        if cam is None:
            return
        try:
            cam.close()
        except Exception:
            _log.warning("warning: failed to close virtual camera", exc_info=True)
