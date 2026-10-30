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


def test_virtual_camera_flag():
    cfg = parse_args(["--virtual-camera"])
    assert cfg.virtual_camera is True


def test_no_sfx_flag():
    cfg = parse_args(["--no-sfx"])
    assert cfg.sfx_enabled is False
