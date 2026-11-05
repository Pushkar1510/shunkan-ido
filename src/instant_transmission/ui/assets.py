"""Resolve brand art shipped under ``assets/``.

Looks in (first hit wins):

1. ``SHUNKAN_IDO_ASSETS`` if set
2. ``/opt/shunkan-ido/assets`` (``.deb`` install)
3. Repo / source checkout ``assets/`` next to the project root
"""

from __future__ import annotations

import os
from pathlib import Path

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


def _repo_assets_dir() -> Path:
    # ui/assets.py → parents[3] == repo root when running from ``src/`` layout
    return Path(__file__).resolve().parents[3] / "assets"


def _candidate_dirs() -> list[Path]:
    dirs: list[Path] = []
    env = os.environ.get("SHUNKAN_IDO_ASSETS")
    if env:
        dirs.append(Path(env))
    dirs.append(Path("/opt/shunkan-ido/assets"))
    dirs.append(_repo_assets_dir())
    # Deduplicate while preserving order
    seen: set[Path] = set()
    out: list[Path] = []
    for path in dirs:
        resolved = path.resolve() if path.exists() else path
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(path)
    return out


def assets_dir() -> Path:
    for path in _candidate_dirs():
        if path.is_dir():
            return path
    return _repo_assets_dir()


def _first_existing(names: tuple[str, ...]) -> Path | None:
    for directory in _candidate_dirs():
        for name in names:
            path = directory / name
            if path.is_file():
                return path
    return None


def background_path() -> Path | None:
    return _first_existing(BACKGROUND_CANDIDATES)


def logo_path() -> Path | None:
    return _first_existing(LOGO_CANDIDATES)


def icon_path() -> Path | None:
    return _first_existing(ICON_CANDIDATES)
