"""Finger snap detection from hand landmark sequences."""

from types import SimpleNamespace

import pytest

from instant_transmission.gesture import HandSample
from instant_transmission.snap_gesture import SnapDetector, SnapEvent


def _lm(x: float, y: float, z: float = 0.0):
    return SimpleNamespace(x=x, y=y, z=z)


def _hand_with_tip_distance(tip_dist: float) -> list:
    """Landmarks with thumb–middle tip distance ``tip_dist`` in normalized xy."""
    pts = [_lm(0.0, 0.0) for _ in range(21)]
    pts[0] = _lm(0.40, 0.60)
    pts[4] = _lm(0.50, 0.50)
    pts[5] = _lm(0.46, 0.50)
    pts[12] = _lm(0.50 + tip_dist, 0.50)
    pts[17] = _lm(0.58, 0.52)
    return pts


def _sample(hand_id: int, tip_dist: float, *, width: int = 1280, height: int = 720) -> HandSample:
    return HandSample(
        hand_id=hand_id,
        landmarks=_hand_with_tip_distance(tip_dist),
        width=width,
        height=height,
    )


def test_close_then_open_emits_one_snap_event():
    detector = SnapDetector()
    t0 = 100.0
    assert detector.update([_sample(0, 0.20)], t0) == []
    assert detector.update([_sample(0, 0.03)], t0 + 0.02) == []
    events = detector.update([_sample(0, 0.12)], t0 + 0.05)
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, SnapEvent)
    assert event.hand_id == 0
    palm = _sample(0, 0.12).palm_xy()
    assert event.palm_xy == pytest.approx(palm)
    assert detector.update([_sample(0, 0.12)], t0 + 0.06) == []


def test_slow_pinch_does_not_emit():
    detector = SnapDetector(max_snap_window_s=0.15)
    t0 = 200.0
    detector.update([_sample(1, 0.20)], t0)
    detector.update([_sample(1, 0.03)], t0 + 0.01)
    events = detector.update([_sample(1, 0.12)], t0 + 0.20)
    assert events == []


def test_cooldown_suppresses_second_snap():
    detector = SnapDetector(cooldown_seconds=0.5)
    t0 = 300.0

    def snap_at(t: float) -> list[SnapEvent]:
        detector.update([_sample(0, 0.20)], t)
        detector.update([_sample(0, 0.03)], t + 0.01)
        return detector.update([_sample(0, 0.12)], t + 0.03)

    assert len(snap_at(t0)) == 1
    assert snap_at(t0 + 0.10) == []
    events = snap_at(t0 + 0.55)
    assert len(events) == 1


def test_empty_hands_returns_empty_list():
    detector = SnapDetector()
    assert detector.update([], 0.0) == []
