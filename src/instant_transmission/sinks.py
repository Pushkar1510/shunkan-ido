"""Virtual camera sink abstractions.

``FrameOutput`` always shows a preview. When ``--virtual-camera`` is enabled it
also opens a ``VirtualCamSink`` that meeting apps can select as a webcam.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

import numpy as np

_log = logging.getLogger(__name__)


class VirtualCamSink(Protocol):
    """Sends processed BGR frames to a system virtual webcam."""

    @property
    def device_name(self) -> str: ...

    def send(self, frame_bgr: np.ndarray) -> None: ...

    def close(self) -> None: ...


class PyVirtualCamSink:
    """``pyvirtualcam`` backend (v4l2loopback on Linux, OBS/Unity on Windows)."""

    def __init__(
        self,
        width: int,
        height: int,
        fps: int,
        *,
        backend: str | None = None,
        device: str | None = None,
    ) -> None:
        import pyvirtualcam
        from pyvirtualcam import PixelFormat
        from pyvirtualcam.camera import BACKENDS

        if backend and backend not in BACKENDS:
            available = ", ".join(sorted(BACKENDS)) or "none"
            raise RuntimeError(
                f"unknown virtual camera backend {backend!r} (available: {available})"
            )

        kwargs: dict[str, Any] = {}
        if backend:
            kwargs["backend"] = backend
        if device:
            kwargs["device"] = device

        self._cam = pyvirtualcam.Camera(
            width,
            height,
            fps,
            fmt=PixelFormat.BGR,
            **kwargs,
        )
        self._device_name = str(getattr(self._cam, "device", backend or "virtual-camera"))

    @property
    def device_name(self) -> str:
        return self._device_name

    def send(self, frame_bgr: np.ndarray) -> None:
        self._cam.send(np.ascontiguousarray(frame_bgr))

    def close(self) -> None:
        cam = self._cam
        self._cam = None
        if cam is None:
            return
        try:
            cam.close()
        except Exception:
            _log.warning("warning: failed to close virtual camera", exc_info=True)


def open_pyvirtualcam_sink(
    width: int,
    height: int,
    fps: int,
    *,
    backend: str | None = None,
    device: str | None = None,
) -> PyVirtualCamSink:
    return PyVirtualCamSink(
        width,
        height,
        fps,
        backend=backend,
        device=device,
    )
