"""Hand samples returned alongside Instant Transmission detection."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

from instant_transmission.gesture import (
    FrameGestureResult,
    GestureDetector,
    HandSample,
    is_instant_transmission,
)


def _lm(x: float, y: float, z: float = 0.0):
    return SimpleNamespace(x=x, y=y, z=z)


def _landmarks() -> list:
    pts = [_lm(0.0, 0.0) for _ in range(21)]
    pts[0] = _lm(0.40, 0.60)  # wrist
    pts[4] = _lm(0.50, 0.40)  # thumb tip
    pts[5] = _lm(0.46, 0.50)  # index MCP
    pts[12] = _lm(0.55, 0.30)  # middle tip
    pts[17] = _lm(0.58, 0.52)  # pinky MCP
    return pts


def _hand(
    wrist=(0.5, 0.55),
    index_pip=(0.48, 0.40),
    index_tip=(0.50, 0.26),
    middle_pip=(0.52, 0.40),
    middle_tip=(0.52, 0.26),
    ring_pip=(0.54, 0.42),
    ring_tip=(0.54, 0.48),
    pinky_pip=(0.56, 0.43),
    pinky_tip=(0.56, 0.49),
):
    pts = [_lm(*wrist) for _ in range(21)]
    pts[0] = _lm(*wrist)
    pts[4] = _lm(wrist[0] - 0.02, wrist[1] - 0.02)
    pts[5] = _lm(0.47, 0.48)
    pts[6] = _lm(*index_pip)
    pts[8] = _lm(*index_tip)
    pts[10] = _lm(*middle_pip)
    pts[12] = _lm(*middle_tip)
    pts[14] = _lm(*ring_pip)
    pts[16] = _lm(*ring_tip)
    pts[17] = _lm(0.57, 0.49)
    pts[18] = _lm(*pinky_pip)
    pts[20] = _lm(*pinky_tip)
    return pts


def _face_forehead():
    pts = [_lm(0.5, 0.5) for _ in range(468)]
    pts[10] = _lm(0.5, 0.25)
    return pts


def test_palm_xy_averages_wrist_index_mcp_and_pinky_mcp_in_pixels():
    width, height = 1280, 720
    landmarks = _landmarks()
    sample = HandSample(hand_id=1, landmarks=landmarks, width=width, height=height)
    xs = [landmarks[index].x * width for index in (0, 5, 17)]
    ys = [landmarks[index].y * height for index in (0, 5, 17)]
    palm_x, palm_y = sample.palm_xy()
    assert palm_x == pytest.approx(sum(xs) / 3)
    assert palm_y == pytest.approx(sum(ys) / 3)


def test_tip_distance_thumb_middle_uses_normalized_xy():
    landmarks = _landmarks()
    sample = HandSample(hand_id=0, landmarks=landmarks, width=640, height=480)
    expected = math.hypot(0.50 - 0.55, 0.40 - 0.30)
    assert sample.tip_distance_thumb_middle() == expected
    assert 0.0 <= expected <= math.hypot(1.0, 1.0)


def test_frame_gesture_result_keeps_flag_and_hand_tuple():
    sample = HandSample(hand_id=0, landmarks=_landmarks(), width=100, height=80)
    result = FrameGestureResult(instant_transmission=True, hands=(sample,))
    assert result.instant_transmission is True
    assert result.hands == (sample,)
    assert result.hands[0].hand_id == 0


class _FakeImage:
    def __init__(self, image_format, data):
        self.image_format = image_format
        self.data = data


class _FakeMp:
    Image = _FakeImage

    class ImageFormat:
        SRGB = "srgb"


def _detector_with_fakes(hands, faces, calls: list):
    class _Hands:
        def detect_for_video(self, image, timestamp_ms):
            calls.append(("hands", timestamp_ms))
            return SimpleNamespace(hand_landmarks=hands)

    class _Face:
        def detect_for_video(self, image, timestamp_ms):
            calls.append(("face", timestamp_ms))
            return SimpleNamespace(face_landmarks=faces)

    detector = GestureDetector()
    detector._hands = _Hands()
    detector._face = _Face()
    detector._mp = _FakeMp
    return detector


def test_process_packs_hands_from_one_mediapipe_pass():
    hand = _hand()
    face = _face_forehead()
    calls: list = []
    detector = _detector_with_fakes([hand], [face], calls)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    result = detector.process(frame)

    assert [name for name, _ts in calls] == ["hands", "face"]
    assert calls[0][1] == calls[1][1]
    assert isinstance(result, FrameGestureResult)
    assert result.instant_transmission is is_instant_transmission(hand, face, (1280, 720))
    assert result.instant_transmission is True
    assert len(result.hands) == 1
    assert result.hands[0].hand_id == 0
    assert result.hands[0].landmarks is hand
    assert result.hands[0].width == 1280
    assert result.hands[0].height == 720


def test_process_returns_hands_when_face_is_missing():
    left = _landmarks()
    right = _landmarks()
    calls: list = []
    detector = _detector_with_fakes([left, right], [], calls)
    frame = np.zeros((360, 640, 3), dtype=np.uint8)

    result = detector.process(frame)

    assert [name for name, _ts in calls] == ["hands", "face"]
    assert result.instant_transmission is False
    assert [sample.hand_id for sample in result.hands] == [0, 1]
    assert result.hands[0].landmarks is left
    assert result.hands[1].landmarks is right
    assert result.hands[0].width == 640
    assert result.hands[0].height == 360


def test_process_keeps_hands_when_pose_is_not_instant_transmission():
    hand = _hand(index_tip=(0.2, 0.8), middle_tip=(0.22, 0.8))
    face = _face_forehead()
    calls: list = []
    detector = _detector_with_fakes([hand], [face], calls)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    result = detector.process(frame)

    assert is_instant_transmission(hand, face, (1280, 720)) is False
    assert result.instant_transmission is False
    assert result.hands[0].landmarks is hand
    assert result.hands[0].hand_id == 0


def test_process_empty_hands_is_not_instant_transmission():
    calls: list = []
    detector = _detector_with_fakes([], [], calls)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    result = detector.process(frame)

    assert result == FrameGestureResult(instant_transmission=False, hands=())
