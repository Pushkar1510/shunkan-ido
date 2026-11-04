from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

ORB_RADIUS_PX = 48
ORB_DURATION_DEFAULT = 1.25
EASE_IN_FRAC = 0.15

# Warm BGR: deep red → orange → yellow core
_COLOR_OUTER = np.array([0, 0, 180], dtype=np.float64)
_COLOR_MID = np.array([0, 100, 255], dtype=np.float64)
_COLOR_CORE = np.array([0, 220, 255], dtype=np.float64)

_GLOW_LAYERS: tuple[tuple[float, np.ndarray, float], ...] = (
    (1.0, _COLOR_OUTER, 0.18),
    (0.65, _COLOR_MID, 0.38),
    (0.32, _COLOR_CORE, 0.62),
)


@dataclass
class PhoenixOrb:
    x: float
    y: float
    born_at: float
    duration: float = ORB_DURATION_DEFAULT


def _life_alpha(now: float, born_at: float, duration: float) -> float:
    """Ease-in, hold, ease-out envelope in [0, 1]."""
    if duration <= 0.0:
        return 0.0
    t = (now - born_at) / duration
    if t <= 0.0 or t >= 1.0:
        return 0.0
    ease = EASE_IN_FRAC
    if t < ease:
        u = t / ease
        return u * u
    if t > 1.0 - ease:
        u = (1.0 - t) / ease
        return u * u
    return 1.0


def _flicker(now: float, born_at: float) -> float:
    age = now - born_at
    sine = 0.85 + 0.15 * math.sin(age * 12.0)
    noise = 0.9 + 0.1 * math.sin(age * 37.0 + 1.7)
    return sine * noise


def _purge_expired(orbs: list[PhoenixOrb], now: float) -> None:
    i = 0
    while i < len(orbs):
        orb = orbs[i]
        if now >= orb.born_at + orb.duration:
            orbs.pop(i)
        else:
            i += 1


def draw_orbs(frame_bgr: np.ndarray, orbs: list[PhoenixOrb], now: float) -> np.ndarray:
    """Return frame with active orbs; drop expired from ``orbs`` in-place."""
    _purge_expired(orbs, now)
    if not orbs:
        return frame_bgr.copy()

    h, w = frame_bgr.shape[:2]
    base = frame_bgr.astype(np.float64)
    glow = np.zeros_like(base)

    for orb in orbs:
        alpha = _life_alpha(now, orb.born_at, orb.duration)
        if alpha <= 0.0:
            continue
        flick = _flicker(now, orb.born_at)
        radius = max(4, int(ORB_RADIUS_PX * (0.75 + 0.25 * alpha) * flick))
        cx = int(round(orb.x))
        cy = int(round(orb.y))
        strength = alpha * flick

        for scale, color, weight in _GLOW_LAYERS:
            r = max(1, int(radius * scale))
            layer = np.zeros((h, w, 3), dtype=np.float64)
            cv2.circle(layer, (cx, cy), r, color.tolist(), -1, lineType=cv2.LINE_AA)
            glow += layer * (weight * strength)

    out = base + glow
    return np.clip(out, 0, 255).astype(np.uint8)
