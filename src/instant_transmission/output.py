from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

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
    ) -> None:
        self._width = width
        self._height = height
        self._show_preview = show_preview
        self._cam: Any = None

        if not virtual_camera:
            return
        try:
            import pyvirtualcam
            from pyvirtualcam import PixelFormat
            from pyvirtualcam.camera import BACKENDS

            # Unknown names raise inside Camera.__init__ before _backend exists,
            # and Camera.__del__ then prints an AttributeError. Reject them first.
            if virtual_backend and virtual_backend not in BACKENDS:
                available = ", ".join(sorted(BACKENDS)) or "none"
                raise RuntimeError(
                    f"unknown virtual camera backend {virtual_backend!r} "
                    f"(available: {available})"
                )

            kwargs: dict[str, str] = {}
            if virtual_backend:
                kwargs["backend"] = virtual_backend
            self._cam = pyvirtualcam.Camera(
                width,
                height,
                fps,
                fmt=PixelFormat.BGR,
                **kwargs,
            )
        except Exception as exc:
            # Backend errors must not take down the preview.
            self._cam = None
            _log.warning(
                "warning: virtual camera unavailable (%s); continuing preview-only",
                exc,
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
