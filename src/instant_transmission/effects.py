from __future__ import annotations

import cv2
import numpy as np

_LINE_PHASE = 0.4
_NUM_LINES = 24


def crossfade(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    t = float(np.clip(t, 0.0, 1.0))
    blended = (1.0 - t) * a.astype(np.float64) + t * b.astype(np.float64)
    return np.clip(blended, 0, 255).astype(np.uint8)


def apply_speed_lines(
    frame: np.ndarray,
    mask: np.ndarray | None,
    intensity: float,
) -> np.ndarray:
    intensity = float(np.clip(intensity, 0.0, 1.0))
    if intensity <= 0.0:
        return frame.copy()

    out = frame.copy()
    h, w = out.shape[:2]
    rng = np.random.default_rng(int(intensity * 1_000_000) % (2**32))

    region = np.ones((h, w), dtype=bool) if mask is None else mask > 0
    ys, xs = np.where(region)
    if ys.size == 0:
        return out

    overlay = out.copy()
    white = (255, 255, 255)
    cyan = (255, 255, 0)  # BGR

    for _ in range(_NUM_LINES):
        idx = int(rng.integers(0, ys.size))
        x = int(xs[idx])
        y0 = int(rng.integers(0, max(h // 4, 1)))
        y1 = int(rng.integers(min(3 * h // 4, h - 1), h))
        color = white if rng.random() > 0.35 else cyan
        thickness = int(rng.integers(1, 3))
        cv2.line(overlay, (x, y0), (x, y1), color, thickness, lineType=cv2.LINE_AA)

    alpha = intensity * 0.85
    out = cv2.addWeighted(overlay, alpha, out, 1.0 - alpha, 0)
    return out.astype(np.uint8)


def compose_teleport(
    live: np.ndarray,
    background: np.ndarray,
    mask: np.ndarray | None,
    progress: float,
    going_out: bool,
) -> np.ndarray:
    progress = float(np.clip(progress, 0.0, 1.0))

    if progress <= _LINE_PHASE:
        line_intensity = progress / _LINE_PHASE
        base = live if going_out else background
        return apply_speed_lines(base, mask, line_intensity)

    fade_t = (progress - _LINE_PHASE) / (1.0 - _LINE_PHASE)
    if going_out:
        return crossfade(live, background, fade_t)
    return crossfade(background, live, fade_t)
