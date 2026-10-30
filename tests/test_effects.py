import numpy as np
from instant_transmission.effects import apply_speed_lines, compose_teleport, crossfade


def test_crossfade_endpoints():
    a = np.zeros((8, 8, 3), dtype=np.uint8)
    b = np.full((8, 8, 3), 255, dtype=np.uint8)
    assert crossfade(a, b, 0.0).mean() == 0
    assert crossfade(a, b, 1.0).mean() == 255


def test_speed_lines_preserves_shape():
    frame = np.full((32, 32, 3), 40, dtype=np.uint8)
    out = apply_speed_lines(frame, mask=None, intensity=1.0)
    assert out.shape == frame.shape
    assert out.dtype == np.uint8


def test_compose_teleport_ends_on_background_when_going_out():
    live = np.zeros((16, 16, 3), dtype=np.uint8)
    bg = np.full((16, 16, 3), 200, dtype=np.uint8)
    out = compose_teleport(live, bg, mask=None, progress=1.0, going_out=True)
    assert abs(int(out.mean()) - 200) <= 1
