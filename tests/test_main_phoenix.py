"""Phoenix snap wiring inside the preview loop."""

import signal
from types import SimpleNamespace

import numpy as np

import instant_transmission.main as main_mod
from instant_transmission.gesture import FrameGestureResult, HandSample
from instant_transmission.main import _loop
from instant_transmission.state import AppState, TeleportController

WIDTH = 160
HEIGHT = 120


def _lm(x: float, y: float):
    return SimpleNamespace(x=x, y=y, z=0.0)


def _sample(tip_dist: float) -> HandSample:
    pts = [_lm(0.0, 0.0) for _ in range(21)]
    pts[0] = _lm(0.40, 0.60)
    pts[4] = _lm(0.50, 0.50)
    pts[5] = _lm(0.46, 0.50)
    pts[12] = _lm(0.50 + tip_dist, 0.50)
    pts[17] = _lm(0.58, 0.52)
    return HandSample(hand_id=0, landmarks=pts, width=WIDTH, height=HEIGHT)


def _result(instant_transmission: bool, tip_dist: float | None) -> FrameGestureResult:
    hands = () if tip_dist is None else (_sample(tip_dist),)
    return FrameGestureResult(instant_transmission, hands)


class _Capture:
    def read(self) -> np.ndarray:
        return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)


class _Output:
    def __init__(self) -> None:
        self.frames: list[np.ndarray] = []

    def send(self, frame: np.ndarray) -> None:
        self.frames.append(frame.copy())


class _Gesture:
    def __init__(self, results: list[FrameGestureResult]) -> None:
        self._results = results
        self.calls = 0

    def process(self, _frame: np.ndarray) -> FrameGestureResult:
        result = self._results[self.calls]
        self.calls += 1
        return result


class _Sfx:
    def __init__(self) -> None:
        self.plays = 0

    def play(self) -> None:
        self.plays += 1


class _Calibrator:
    background = None
    progress = 0.0

    def update(self, _frame: np.ndarray, _dt: float) -> bool:
        return False


def _visible_controller() -> TeleportController:
    controller = TeleportController(cooldown_seconds=0.8, teleport_seconds=10.0)
    controller.start_calibration()
    controller.finish_calibration()
    assert controller.state == AppState.VISIBLE
    return controller


def _run(monkeypatch, results: list[FrameGestureResult], controller: TeleportController, *, phoenix_enabled: bool = True):
    times = iter([100.0, 100.0, 100.02, 100.05, 100.20])
    keys = iter([0, 0, 0, ord("q")])
    monkeypatch.setattr(main_mod.time, "perf_counter", lambda: next(times))
    monkeypatch.setattr(main_mod.cv2, "waitKey", lambda _delay: next(keys))
    main_mod._stop_requested = False
    previous_int = signal.getsignal(signal.SIGINT)
    previous_term = signal.getsignal(signal.SIGTERM)
    gesture = _Gesture(results)
    it_sfx = _Sfx()
    phoenix_sfx = _Sfx()
    output = _Output()
    try:
        _loop(
            _Capture(),
            output,
            gesture,
            it_sfx,
            _Calibrator(),
            controller,
            30,
            phoenix_sfx,
            phoenix_enabled=phoenix_enabled,
        )
    finally:
        signal.signal(signal.SIGINT, previous_int)
        signal.signal(signal.SIGTERM, previous_term)
        main_mod._stop_requested = False
    return gesture, it_sfx, phoenix_sfx, output


def _snap_script(instant_transmission_on_release: bool = False) -> list[FrameGestureResult]:
    return [
        _result(False, 0.20),
        _result(False, 0.03),
        _result(instant_transmission_on_release, 0.12),
        _result(False, None),
    ]


def test_visible_snap_spawns_orb_and_plays_phoenix_sfx(monkeypatch):
    gesture, it_sfx, phoenix_sfx, output = _run(
        monkeypatch, _snap_script(), _visible_controller()
    )
    palm = _sample(0.12).palm_xy()
    cx, cy = int(round(palm[0])), int(round(palm[1]))
    assert gesture.calls == 4
    assert it_sfx.plays == 0
    assert phoenix_sfx.plays == 1
    assert output.frames[2][cy, cx].sum() > 0
    assert output.frames[3][cy, cx].sum() > 0


def test_instant_transmission_blocks_snap_on_that_frame(monkeypatch):
    controller = _visible_controller()
    _gesture, it_sfx, phoenix_sfx, output = _run(
        monkeypatch,
        _snap_script(instant_transmission_on_release=True),
        controller,
    )
    assert it_sfx.plays == 1
    assert phoenix_sfx.plays == 0
    assert controller.state == AppState.TELEPORTING_OUT
    assert output.frames[-1].max() == 0


def test_cooldown_instant_transmission_does_not_snap(monkeypatch):
    controller = _visible_controller()
    controller._cooldown_until = 10_000.0
    results = [
        _result(True, 0.20),
        _result(True, 0.03),
        _result(True, 0.12),
        _result(True, None),
    ]
    gesture, it_sfx, phoenix_sfx, output = _run(monkeypatch, results, controller)
    assert gesture.calls == 4
    assert it_sfx.plays == 0
    assert phoenix_sfx.plays == 0
    assert controller.state == AppState.VISIBLE
    assert output.frames[-1].max() == 0


def test_vanished_does_not_evaluate_snap(monkeypatch):
    controller = _visible_controller()
    controller.state = AppState.VANISHED
    gesture, it_sfx, phoenix_sfx, output = _run(monkeypatch, _snap_script(), controller)
    assert gesture.calls == 4
    assert it_sfx.plays == 0
    assert phoenix_sfx.plays == 0
    assert output.frames[-1].max() == 0


def test_calibrating_and_teleporting_skip_snap(monkeypatch):
    for state in (AppState.CALIBRATING, AppState.TELEPORTING_OUT, AppState.TELEPORTING_IN):
        controller = TeleportController(cooldown_seconds=0.8, teleport_seconds=10.0)
        controller.state = state
        gesture, it_sfx, phoenix_sfx, _output = _run(monkeypatch, _snap_script(), controller)
        assert gesture.calls == 0
        assert it_sfx.plays == 0
        assert phoenix_sfx.plays == 0


def test_no_phoenix_skips_orb_and_sfx(monkeypatch):
    _gesture, it_sfx, phoenix_sfx, output = _run(
        monkeypatch,
        _snap_script(),
        _visible_controller(),
        phoenix_enabled=False,
    )
    assert it_sfx.plays == 0
    assert phoenix_sfx.plays == 0
    assert output.frames[-1].max() == 0
