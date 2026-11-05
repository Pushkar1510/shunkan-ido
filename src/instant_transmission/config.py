from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _default_sfx_path() -> Path:
    """Prefer ``.deb`` / env assets, then source-tree ``assets/``."""
    name = "instant_transmission.mp3"
    env = os.environ.get("SHUNKAN_IDO_ASSETS")
    candidates = []
    if env:
        candidates.append(Path(env) / name)
    candidates.append(Path("/opt/shunkan-ido/assets") / name)
    candidates.append(_ROOT / "assets" / name)
    for path in candidates:
        if path.is_file():
            return path
    return candidates[-1]


_DEFAULT_SFX = _default_sfx_path()


@dataclass(frozen=True)
class AppConfig:
    camera: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    virtual_camera: bool = False
    virtual_backend: str | None = None
    setup_virtual_camera: bool = False
    sfx_path: Path = _DEFAULT_SFX
    sfx_enabled: bool = True
    calibration_seconds: float = 4.0
    cooldown_seconds: float = 0.8
    teleport_seconds: float = 0.7


def parse_args(argv: list[str] | None = None) -> AppConfig:
    p = argparse.ArgumentParser(prog="shunkan-ido", description="Instant Transmission webcam cam")
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--virtual-camera", action="store_true")
    p.add_argument("--virtual-backend", default=None)
    p.add_argument(
        "--setup-virtual-camera",
        action="store_true",
        help="One-time virtual camera setup (Ubuntu v4l2loopback / Windows OBS), then exit",
    )
    p.add_argument("--sfx", type=Path, default=_DEFAULT_SFX)
    p.add_argument("--no-sfx", action="store_true")
    p.add_argument("--calibration-seconds", type=float, default=4.0)
    args = p.parse_args(argv)
    return AppConfig(
        camera=args.camera,
        width=args.width,
        height=args.height,
        fps=args.fps,
        virtual_camera=args.virtual_camera,
        virtual_backend=args.virtual_backend,
        setup_virtual_camera=args.setup_virtual_camera,
        sfx_path=args.sfx,
        sfx_enabled=not args.no_sfx,
        calibration_seconds=args.calibration_seconds,
    )
