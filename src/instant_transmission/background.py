from __future__ import annotations

import numpy as np


class BackgroundCalibrator:
    def __init__(self, duration_seconds: float) -> None:
        self.duration_seconds = max(duration_seconds, 1e-3)
        self._elapsed = 0.0
        self._sum: np.ndarray | None = None
        self._count = 0
        self.background: np.ndarray | None = None

    @property
    def progress(self) -> float:
        return min(1.0, self._elapsed / self.duration_seconds)

    def reset(self) -> None:
        self._elapsed = 0.0
        self._sum = None
        self._count = 0
        self.background = None

    def update(self, frame: np.ndarray, dt: float) -> bool:
        if self.background is not None:
            return True
        f = frame.astype(np.float64)
        if self._sum is None:
            self._sum = np.zeros_like(f)
        self._sum += f
        self._count += 1
        self._elapsed += dt
        if self._elapsed < self.duration_seconds:
            return False
        assert self._sum is not None and self._count > 0
        self.background = (self._sum / self._count).clip(0, 255).astype(np.uint8)
        return True
