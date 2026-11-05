"""Resolve brand art shipped under ``assets/``."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_ASSETS = _ROOT / "assets"

BACKGROUND_CANDIDATES = (
    "Shunkan_ido_bg.jpg",
    "launcher_bg.png",
    "launcher_bg.jpg",
)
LOGO_CANDIDATES = (
    "shunkan_ido_logo.png",
    "logo.png",
)
ICON_CANDIDATES = (
    "shunkan_ido_icon.png",
    "icon.png",
)


def assets_dir() -> Path:
    return _ASSETS


def _first_existing(names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = _ASSETS / name
        if path.is_file():
            return path
    return None


def background_path() -> Path | None:
    return _first_existing(BACKGROUND_CANDIDATES)


def logo_path() -> Path | None:
    return _first_existing(LOGO_CANDIDATES)


def icon_path() -> Path | None:
    return _first_existing(ICON_CANDIDATES)
