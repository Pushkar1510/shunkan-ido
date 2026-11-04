"""Procedural phoenix palm orb VFX."""

import numpy as np
import pytest

from instant_transmission.phoenix_fx import PhoenixOrb, draw_orbs


def _blank(h: int = 120, w: int = 160) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_draw_orbs_preserves_shape_and_dtype():
    frame = _blank()
    orbs = [PhoenixOrb(x=80.0, y=60.0, born_at=0.0, duration=1.25)]
    out = draw_orbs(frame, orbs, now=0.5)
    assert out.shape == frame.shape
    assert out.dtype == np.uint8


def test_expired_orb_removed_and_frame_unchanged():
    frame = _blank()
    original = frame.copy()
    orbs = [PhoenixOrb(x=80.0, y=60.0, born_at=10.0, duration=1.25)]
    out = draw_orbs(frame, orbs, now=10.0 + 1.25)
    assert orbs == []
    np.testing.assert_array_equal(out, original)


def test_mid_life_orb_modifies_pixels_near_center():
    frame = _blank()
    cx, cy = 80.0, 60.0
    born_at = 100.0
    duration = 1.25
    orbs = [PhoenixOrb(x=cx, y=cy, born_at=born_at, duration=duration)]
    mid = born_at + duration * 0.5
    out = draw_orbs(frame, orbs, now=mid)
    ix, iy = int(cx), int(cy)
    assert out[iy, ix].sum() > 0
    assert not np.array_equal(out, frame)


def test_empty_orb_list_returns_copy_unchanged():
    frame = _blank()
    frame[10, 10] = (40, 40, 40)
    orbs: list[PhoenixOrb] = []
    out = draw_orbs(frame, orbs, now=0.0)
    assert out.shape == frame.shape
    np.testing.assert_array_equal(out, frame)
    assert orbs == []
