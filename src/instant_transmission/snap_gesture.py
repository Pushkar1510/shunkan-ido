"""Detect finger snap from thumb–middle tip distance over time."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from instant_transmission.gesture import HandSample


@dataclass(frozen=True)
class SnapEvent:
    palm_xy: tuple[float, float]
    hand_id: int


@dataclass
class _HandSnapState:
    pinched: bool = False
    pinched_at: float = 0.0


class SnapDetector:
    """Emit ``SnapEvent`` when a hand pinches then releases quickly."""

    def __init__(
        self,
        *,
        cooldown_seconds: float = 0.5,
        pinch_threshold: float = 0.05,
        release_threshold: float = 0.10,
        max_snap_window_s: float = 0.15,
    ) -> None:
        self._cooldown_seconds = cooldown_seconds
        self._pinch_threshold = pinch_threshold
        self._release_threshold = release_threshold
        self._max_snap_window_s = max_snap_window_s
        self._hand_state: dict[int, _HandSnapState] = {}
        self._cooldown_until = float("-inf")

    def update(self, hands: Sequence[HandSample], now: float) -> list[SnapEvent]:
        events: list[SnapEvent] = []
        seen: set[int] = set()
        for hand in hands:
            seen.add(hand.hand_id)
            state = self._hand_state.setdefault(hand.hand_id, _HandSnapState())
            distance = hand.tip_distance_thumb_middle()
            if not state.pinched:
                if distance < self._pinch_threshold:
                    state.pinched = True
                    state.pinched_at = now
                continue
            elapsed = now - state.pinched_at
            if elapsed > self._max_snap_window_s:
                state.pinched = False
                if distance < self._pinch_threshold:
                    state.pinched = True
                    state.pinched_at = now
                continue
            if distance <= self._release_threshold:
                continue
            state.pinched = False
            if now < self._cooldown_until:
                continue
            events.append(SnapEvent(palm_xy=hand.palm_xy(), hand_id=hand.hand_id))
            self._cooldown_until = now + self._cooldown_seconds
        for hand_id in list(self._hand_state):
            if hand_id not in seen:
                del self._hand_state[hand_id]
        return events
