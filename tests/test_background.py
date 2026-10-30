import numpy as np
from instant_transmission.background import BackgroundCalibrator


def test_not_ready_until_duration():
    cal = BackgroundCalibrator(duration_seconds=1.0)
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    assert cal.update(frame, dt=0.4) is False
    assert cal.background is None
    assert cal.update(frame, dt=0.7) is True
    assert cal.background is not None
    assert cal.background.shape == frame.shape


def test_averages_frames():
    cal = BackgroundCalibrator(duration_seconds=0.2)
    a = np.zeros((2, 2, 3), dtype=np.uint8)
    b = np.full((2, 2, 3), 100, dtype=np.uint8)
    cal.update(a, dt=0.1)
    cal.update(b, dt=0.1)
    assert cal.background is not None
    # mean of 0 and 100 ~= 50
    assert int(cal.background.mean()) == 50
