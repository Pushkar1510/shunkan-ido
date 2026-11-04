from pathlib import Path

from instant_transmission.config import parse_args


def test_defaults():
    cfg = parse_args([])
    assert cfg.camera == 0
    assert cfg.width == 1280
    assert cfg.height == 720
    assert cfg.fps == 30
    assert cfg.virtual_camera is False
    assert cfg.sfx_enabled is True
    assert cfg.calibration_seconds == 4.0
    assert cfg.sfx_path.name == "instant_transmission.mp3"
    assert cfg.phoenix_enabled is True
    assert cfg.phoenix_sfx_path.name == "phoenix_snap.mp3"


def test_virtual_camera_flag():
    cfg = parse_args(["--virtual-camera"])
    assert cfg.virtual_camera is True


def test_setup_virtual_camera_flag():
    cfg = parse_args(["--setup-virtual-camera"])
    assert cfg.setup_virtual_camera is True
    assert cfg.virtual_camera is False


def test_no_sfx_flag():
    cfg = parse_args(["--no-sfx"])
    assert cfg.sfx_enabled is False


def test_no_phoenix_disables_snap_orbs():
    cfg = parse_args(["--no-phoenix"])
    assert cfg.phoenix_enabled is False
    assert cfg.sfx_enabled is True


def test_phoenix_sfx_sets_snap_sound_path():
    cfg = parse_args(["--phoenix-sfx", "custom/snap.mp3"])
    assert cfg.phoenix_sfx_path == Path("custom/snap.mp3")
    assert cfg.phoenix_enabled is True
