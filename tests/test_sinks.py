"""Tests for VirtualCamSink / FrameOutput wiring."""

from __future__ import annotations

import numpy as np

from instant_transmission.output import FrameOutput


class _FakeSink:
    def __init__(self) -> None:
        self.frames: list[np.ndarray] = []
        self.closed = False

    @property
    def device_name(self) -> str:
        return "fake"

    def send(self, frame_bgr: np.ndarray) -> None:
        self.frames.append(frame_bgr)

    def close(self) -> None:
        self.closed = True


def test_frame_output_uses_injected_sink(monkeypatch) -> None:
    monkeypatch.setattr("instant_transmission.output.cv2.imshow", lambda *_a, **_k: None)
    monkeypatch.setattr("instant_transmission.output.cv2.destroyWindow", lambda *_a, **_k: None)
    sink = _FakeSink()
    out = FrameOutput(
        width=4,
        height=4,
        fps=30,
        show_preview=True,
        virtual_camera=False,
        sink=sink,
    )
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    out.send(frame)
    assert len(sink.frames) == 1
    out.close()
    assert sink.closed is True


def test_frame_output_preview_only_without_sink(monkeypatch) -> None:
    shown: list[object] = []
    monkeypatch.setattr(
        "instant_transmission.output.cv2.imshow",
        lambda *_a, **_k: shown.append(True),
    )
    monkeypatch.setattr("instant_transmission.output.cv2.destroyWindow", lambda *_a, **_k: None)
    out = FrameOutput(width=4, height=4, fps=30, show_preview=True, virtual_camera=False)
    out.send(np.zeros((4, 4, 3), dtype=np.uint8))
    assert shown
    out.close()
