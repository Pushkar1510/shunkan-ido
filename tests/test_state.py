# tests/test_state.py
from instant_transmission.state import AppState, TeleportController


def test_starts_calibrating():
    c = TeleportController(cooldown_seconds=0.8, teleport_seconds=0.5)
    assert c.state == AppState.CALIBRATING


def test_calibration_then_gesture_teleports_out():
    c = TeleportController(cooldown_seconds=0.8, teleport_seconds=0.5)
    c.finish_calibration()
    assert c.state == AppState.VISIBLE
    started = c.on_gesture(now=1.0)
    assert started is True
    assert c.state == AppState.TELEPORTING_OUT


def test_teleport_out_completes_to_vanished():
    c = TeleportController(cooldown_seconds=0.8, teleport_seconds=0.5)
    c.finish_calibration()
    c.on_gesture(now=0.0)
    c.update(now=0.6, dt=0.6)
    assert c.state == AppState.VANISHED


def test_gesture_during_cooldown_ignored():
    c = TeleportController(cooldown_seconds=1.0, teleport_seconds=0.2)
    c.finish_calibration()
    assert c.on_gesture(now=0.0) is True
    c.update(now=0.3, dt=0.3)  # -> VANISHED, cooldown starts
    assert c.state == AppState.VANISHED
    assert c.on_gesture(now=0.5) is False  # still cooling down


def test_reappear_cycle():
    c = TeleportController(cooldown_seconds=0.1, teleport_seconds=0.2)
    c.finish_calibration()
    c.on_gesture(now=0.0)
    c.update(now=0.25, dt=0.25)
    assert c.state == AppState.VANISHED
    c.update(now=0.4, dt=0.15)  # past cooldown
    assert c.on_gesture(now=0.4) is True
    assert c.state == AppState.TELEPORTING_IN
    c.update(now=0.7, dt=0.3)
    assert c.state == AppState.VISIBLE
