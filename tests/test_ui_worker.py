"""Launcher camera worker helpers."""

from pathlib import Path

from instant_transmission.config import AppConfig
from instant_transmission.ui.worker import cam_argv


def test_cam_argv_virtual_camera_defaults() -> None:
    cfg = AppConfig(virtual_camera=True)
    argv = cam_argv(cfg)
    assert "--virtual-camera" in argv
    assert "--no-sfx" not in argv
    assert argv[argv.index("--camera") + 1] == "0"


def test_cam_argv_respects_sfx_and_backend() -> None:
    cfg = AppConfig(
        virtual_camera=True,
        sfx_enabled=False,
        virtual_backend="v4l2loopback",
        sfx_path=Path("/tmp/sfx.mp3"),
    )
    argv = cam_argv(cfg)
    assert "--no-sfx" in argv
    assert argv[argv.index("--virtual-backend") + 1] == "v4l2loopback"
    assert argv[argv.index("--sfx") + 1] == "/tmp/sfx.mp3"
