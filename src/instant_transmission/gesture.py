# src/instant_transmission/gesture.py
"""Instant Transmission pose from hand and face landmarks.

Finger extension is a ratio, so it does not depend on frame size.
``FOREHEAD_RADIUS`` and ``FINGER_TOGETHER_DIST`` are pixels on a 1280×720
frame. Those two comparisons are mapped back onto that baseline, so the same
normalized landmarks match at other resolutions. ``image_size`` is
``(width, height)``.

Values below were checked against ``tests/test_gesture.py`` on a 1280×720
frame:

- index tip sits about 7 px from forehead landmark 10; middle tip about 27 px
- index and middle tips sit about 26 px apart
- the far-from-forehead fixture is more than 500 px from that landmark
- extended index/middle project about 1.8 times the wrist→PIP segment
- folded ring/pinky project about 0.65–0.72 times that same segment
"""

from __future__ import annotations

import math
import time
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Both index and middle tips must fall inside this radius of the forehead.
# Pixels on a 1280×720 frame; scaled to the current frame before compare.
FOREHEAD_RADIUS = 90.0
# Index tip and middle tip must be at least this close (fingers together).
# Pixels on a 1280×720 frame; scaled to the current frame before compare.
FINGER_TOGETHER_DIST = 70.0
_BASELINE_WIDTH = 1280.0
_BASELINE_HEIGHT = 720.0
# Tip projection onto the wrist→PIP axis, divided by that segment's length.
# Above EXTENDED_REACH the fingertip is past the PIP (finger extended).
# Below FOLDED_REACH the fingertip is short of the PIP (finger folded).
EXTENDED_REACH = 1.25
FOLDED_REACH = 0.90

# MediaPipe Hands landmark indices.
_WRIST = 0
_THUMB_TIP = 4
_INDEX_MCP = 5
_INDEX_PIP = 6
_INDEX_TIP = 8
_MIDDLE_PIP = 10
_MIDDLE_TIP = 12
_RING_PIP = 14
_RING_TIP = 16
_PINKY_MCP = 17
_PINKY_PIP = 18
_PINKY_TIP = 20
# MediaPipe Face Mesh / Face Landmarker forehead landmark.
_FOREHEAD = 10

_MODEL_DIR = Path.home() / ".cache" / "shunkan-ido"
_HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
_FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
# Per-read socket timeout so stop callbacks are polled every few seconds.
_READ_TIMEOUT_S = 3.0


class _Landmark(Protocol):
    x: float
    y: float


def _pixel(landmark: _Landmark, width: int, height: int) -> tuple[float, float]:
    return (landmark.x * width, landmark.y * height)


@dataclass(frozen=True)
class HandSample:
    """One hand from the current frame.

    ``landmarks`` are MediaPipe-style points with normalized ``x`` and ``y``.
    ``width`` and ``height`` are the frame size in pixels.
    """

    hand_id: int
    landmarks: Sequence[_Landmark]
    width: int
    height: int

    def tip_distance_thumb_middle(self) -> float:
        """Thumb tip to middle tip in normalized image space."""
        thumb = self.landmarks[_THUMB_TIP]
        middle = self.landmarks[_MIDDLE_TIP]
        return math.hypot(thumb.x - middle.x, thumb.y - middle.y)

    def palm_xy(self) -> tuple[float, float]:
        """Pixel palm: average of wrist, index MCP, and pinky MCP."""
        total_x = 0.0
        total_y = 0.0
        for index in (_WRIST, _INDEX_MCP, _PINKY_MCP):
            x, y = _pixel(self.landmarks[index], self.width, self.height)
            total_x += x
            total_y += y
        return (total_x / 3.0, total_y / 3.0)


@dataclass(frozen=True)
class FrameGestureResult:
    """Instant Transmission decision and every hand from one landmark pass."""

    instant_transmission: bool
    hands: tuple[HandSample, ...]


def _baseline_distance(
    a: tuple[float, float],
    b: tuple[float, float],
    width: int,
    height: int,
) -> float:
    """Distance in 1280×720 pixels, independent of the current frame size.

    ``a`` and ``b`` are pixels in the current frame. Scaling each axis by the
    baseline over the frame size keeps a normalized landmark gap on the same
    threshold at 720p and at other resolutions.
    """
    sx = _BASELINE_WIDTH / width
    sy = _BASELINE_HEIGHT / height
    return math.hypot((a[0] - b[0]) * sx, (a[1] - b[1]) * sy)


def _axis_reach(
    tip: tuple[float, float],
    pip: tuple[float, float],
    wrist: tuple[float, float],
) -> float:
    """How far the tip lies along the wrist→PIP axis, in units of that segment.

    ``1`` is exactly at the PIP. Larger values are beyond it (extended);
    smaller values are closer to the wrist (folded).
    """
    axis_x = pip[0] - wrist[0]
    axis_y = pip[1] - wrist[1]
    length_sq = axis_x * axis_x + axis_y * axis_y
    if length_sq < 1e-6:
        return 0.0
    tip_x = tip[0] - wrist[0]
    tip_y = tip[1] - wrist[1]
    return (tip_x * axis_x + tip_y * axis_y) / length_sq


def is_instant_transmission(
    hand_landmarks: list[_Landmark],
    face_landmarks: list[_Landmark],
    image_size: tuple[int, int],
) -> bool:
    """Return True when the hand matches the Instant Transmission pose.

    Index and middle are extended and together, near the forehead. Ring and
    pinky are folded. ``image_size`` is ``(width, height)``.
    """
    if not hand_landmarks or not face_landmarks:
        return False
    if len(hand_landmarks) <= _PINKY_TIP or len(face_landmarks) <= _FOREHEAD:
        return False
    width, height = image_size
    if width <= 0 or height <= 0:
        return False

    wrist = _pixel(hand_landmarks[_WRIST], width, height)
    index_pip = _pixel(hand_landmarks[_INDEX_PIP], width, height)
    index_tip = _pixel(hand_landmarks[_INDEX_TIP], width, height)
    middle_pip = _pixel(hand_landmarks[_MIDDLE_PIP], width, height)
    middle_tip = _pixel(hand_landmarks[_MIDDLE_TIP], width, height)
    ring_pip = _pixel(hand_landmarks[_RING_PIP], width, height)
    ring_tip = _pixel(hand_landmarks[_RING_TIP], width, height)
    pinky_pip = _pixel(hand_landmarks[_PINKY_PIP], width, height)
    pinky_tip = _pixel(hand_landmarks[_PINKY_TIP], width, height)
    forehead = _pixel(face_landmarks[_FOREHEAD], width, height)

    if _axis_reach(index_tip, index_pip, wrist) < EXTENDED_REACH:
        return False
    if _axis_reach(middle_tip, middle_pip, wrist) < EXTENDED_REACH:
        return False
    if _axis_reach(ring_tip, ring_pip, wrist) > FOLDED_REACH:
        return False
    if _axis_reach(pinky_tip, pinky_pip, wrist) > FOLDED_REACH:
        return False
    if _baseline_distance(index_tip, forehead, width, height) > FOREHEAD_RADIUS:
        return False
    if _baseline_distance(middle_tip, forehead, width, height) > FOREHEAD_RADIUS:
        return False
    if _baseline_distance(index_tip, middle_tip, width, height) > FINGER_TOGETHER_DIST:
        return False
    return True


def _download_model(
    url: str,
    dest: Path,
    *,
    read_timeout: float = _READ_TIMEOUT_S,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    """Write ``url`` to ``dest``. Raises RuntimeError on timeout or HTTP failure.

    Each socket read uses ``read_timeout`` so ``should_stop`` is checked often.
    KeyboardInterrupt and download cancellation are not wrapped.
    """
    try:
        with urllib.request.urlopen(url, timeout=read_timeout) as response:
            with dest.open("wb") as handle:
                while True:
                    if should_stop is not None and should_stop():
                        raise RuntimeError("download cancelled")
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    handle.write(chunk)
                    if should_stop is not None and should_stop():
                        raise RuntimeError("download cancelled")
    except KeyboardInterrupt:
        raise
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to download model from {url}: {exc}") from exc


def _cached_model(
    url: str,
    filename: str,
    *,
    should_stop: Callable[[], bool] | None = None,
) -> Path:
    dest = _MODEL_DIR / filename
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    if should_stop is not None and should_stop():
        raise RuntimeError("download cancelled")
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(".part")
    try:
        _download_model(url, partial, should_stop=should_stop)
        if not partial.is_file() or partial.stat().st_size <= 0:
            raise RuntimeError(f"Downloaded model is empty: {url}")
        partial.replace(dest)
    finally:
        if partial.exists():
            partial.unlink(missing_ok=True)
    return dest


class GestureDetector:
    """MediaPipe Hands + Face Landmarker wrapper.

    Graphs are created on the first ``warmup`` or ``process`` call. ``close`` releases them.
    MediaPipe 1.2 ships the Tasks API, so the float16 hand and face landmarker
    models are downloaded once into ``~/.cache/shunkan-ido``.
    """

    def __init__(self, should_stop: Callable[[], bool] | None = None) -> None:
        self._should_stop = should_stop
        self._hands = None
        self._face = None
        self._timestamp_ms = 0

    def _ensure_loaded(self) -> None:
        if self._hands is not None and self._face is not None:
            return
        if self._should_stop is not None and self._should_stop():
            raise RuntimeError("download cancelled")
        import mediapipe as mp
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import (
            FaceLandmarker,
            FaceLandmarkerOptions,
            HandLandmarker,
            HandLandmarkerOptions,
        )
        from mediapipe.tasks.python.vision.core.vision_task_running_mode import (
            VisionTaskRunningMode,
        )

        stop = self._should_stop
        hand_path = _cached_model(_HAND_MODEL_URL, "hand_landmarker.task", should_stop=stop)
        if stop is not None and stop():
            raise RuntimeError("download cancelled")
        face_path = _cached_model(_FACE_MODEL_URL, "face_landmarker.task", should_stop=stop)
        self._mp = mp
        hands = None
        face = None
        try:
            hands = HandLandmarker.create_from_options(
                HandLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(hand_path)),
                    running_mode=VisionTaskRunningMode.VIDEO,
                    num_hands=2,
                )
            )
            face = FaceLandmarker.create_from_options(
                FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(face_path)),
                    running_mode=VisionTaskRunningMode.VIDEO,
                    num_faces=1,
                )
            )
        except Exception:
            if hands is not None:
                hands.close()
            if face is not None:
                face.close()
            raise
        self._hands = hands
        self._face = face

    def _next_timestamp_ms(self) -> int:
        now = int(time.monotonic() * 1000)
        if now <= self._timestamp_ms:
            now = self._timestamp_ms + 1
        self._timestamp_ms = now
        return now

    def warmup(self, width: int = 1280, height: int = 720) -> None:
        """Load the landmarkers and run one inference before the capture loop.

        The first video-mode call compiles the graphs. Doing that here, on a
        black frame, keeps that cost out of the first live ``dt``.
        """
        import numpy as np

        if width <= 0 or height <= 0:
            width, height = 1280, 720
        self.process(np.zeros((height, width, 3), dtype=np.uint8))

    def process(self, frame_bgr) -> FrameGestureResult:
        """Detect Instant Transmission and pack every hand from one pass.

        Hands and face are each landmarked once, with the same timestamp.
        ``instant_transmission`` uses the existing pose check. Hands are still
        returned when the pose does not match or the face is missing.
        """
        import cv2

        self._ensure_loaded()
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        if not rgb.flags["C_CONTIGUOUS"]:
            rgb = rgb.copy()
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = self._next_timestamp_ms()
        hand_result = self._hands.detect_for_video(mp_image, timestamp_ms)
        face_result = self._face.detect_for_video(mp_image, timestamp_ms)
        height, width = frame_bgr.shape[:2]
        raw_hands = hand_result.hand_landmarks or ()
        hands = tuple(
            HandSample(
                hand_id=index,
                landmarks=landmarks,
                width=width,
                height=height,
            )
            for index, landmarks in enumerate(raw_hands)
        )
        raw_faces = face_result.face_landmarks or ()
        instant = False
        if hands and raw_faces:
            face = raw_faces[0]
            image_size = (width, height)
            instant = any(
                is_instant_transmission(sample.landmarks, face, image_size)
                for sample in hands
            )
        return FrameGestureResult(instant_transmission=instant, hands=hands)

    def close(self) -> None:
        if self._hands is not None:
            self._hands.close()
            self._hands = None
        if self._face is not None:
            self._face.close()
            self._face = None
