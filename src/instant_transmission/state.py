# src/instant_transmission/state.py
from __future__ import annotations

from enum import Enum, auto


class AppState(Enum):
    CALIBRATING = auto()
    VISIBLE = auto()
    TELEPORTING_OUT = auto()
    VANISHED = auto()
    TELEPORTING_IN = auto()


class TeleportController:
    def __init__(self, cooldown_seconds: float, teleport_seconds: float) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.teleport_seconds = max(teleport_seconds, 1e-3)
        self.state = AppState.CALIBRATING
        self.progress = 0.0
        self._anim_elapsed = 0.0
        self._cooldown_until = 0.0

    def finish_calibration(self) -> None:
        if self.state == AppState.CALIBRATING:
            self.state = AppState.VISIBLE

    def in_cooldown(self, now: float) -> bool:
        return now < self._cooldown_until

    def on_gesture(self, now: float) -> bool:
        if self.in_cooldown(now):
            return False
        if self.state == AppState.VISIBLE:
            self.state = AppState.TELEPORTING_OUT
            self._anim_elapsed = 0.0
            self.progress = 0.0
            return True
        if self.state == AppState.VANISHED:
            self.state = AppState.TELEPORTING_IN
            self._anim_elapsed = 0.0
            self.progress = 0.0
            return True
        return False

    def update(self, now: float, dt: float) -> None:
        if self.state not in (AppState.TELEPORTING_OUT, AppState.TELEPORTING_IN):
            return
        self._anim_elapsed += dt
        self.progress = min(1.0, self._anim_elapsed / self.teleport_seconds)
        if self.progress < 1.0:
            return
        if self.state == AppState.TELEPORTING_OUT:
            self.state = AppState.VANISHED
        else:
            self.state = AppState.VISIBLE
        self.progress = 0.0
        self._cooldown_until = now + self.cooldown_seconds
