from instant_transmission.main import _clamp_dt


def test_clamp_dt_keeps_a_normal_frame():
    assert _clamp_dt(0.02, 30) == 0.02


def test_clamp_dt_caps_a_stall_at_least_one_tenth():
    assert _clamp_dt(3.0, 30) == 0.1


def test_clamp_dt_allows_a_slow_frame_rate():
    assert _clamp_dt(2.0, 5) == 0.2


def test_clamp_dt_drops_a_negative_gap():
    assert _clamp_dt(-1.0, 30) == 0.0
