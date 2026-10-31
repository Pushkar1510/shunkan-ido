"""OBS / virtual-camera detection and one-time setup helpers.

On Windows and macOS, meeting apps need OBS Virtual Camera. After a one-time
prime (Start Virtual Camera once), ``pyvirtualcam`` can feed that device without
keeping the OBS UI open every call. Linux uses ``v4l2loopback`` instead.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

_OBS_DOWNLOAD = "https://obsproject.com/"
_PRIME_WAIT_S = 4.0


@dataclass(frozen=True)
class ObsStatus:
    platform: str
    installed: bool
    path: Path | None
    notes: str = ""


def _macos_obs_candidates() -> list[Path]:
    home = Path.home()
    return [
        Path("/Applications/OBS.app"),
        home / "Applications" / "OBS.app",
    ]


def _windows_obs_candidates() -> list[Path]:
    roots: list[Path] = []
    for key in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        value = os.environ.get(key)
        if value:
            roots.append(Path(value))
    paths: list[Path] = []
    for root in roots:
        paths.append(root / "obs-studio" / "bin" / "64bit" / "obs64.exe")
        paths.append(root / "Programs" / "obs-studio" / "bin" / "64bit" / "obs64.exe")
    return paths


def detect_obs() -> ObsStatus:
    """Return whether OBS appears installed on this machine."""
    platform = sys.platform
    if platform == "darwin":
        for path in _macos_obs_candidates():
            if path.is_dir():
                return ObsStatus(platform=platform, installed=True, path=path)
        return ObsStatus(platform=platform, installed=False, path=None)
    if platform == "win32":
        for path in _windows_obs_candidates():
            if path.is_file():
                return ObsStatus(platform=platform, installed=True, path=path)
        return ObsStatus(platform=platform, installed=False, path=None)
    if platform.startswith("linux"):
        return ObsStatus(
            platform="linux",
            installed=False,
            path=None,
            notes=(
                "Linux uses v4l2loopback (not OBS). "
                "Install/load the module, then run with --virtual-camera."
            ),
        )
    return ObsStatus(platform=platform, installed=False, path=None)


def format_setup_guidance(status: ObsStatus, *, open_failed: bool = False) -> str:
    """Human-readable one-time setup steps for Zoom / Teams / Meet."""
    lines: list[str] = []
    if status.platform == "linux" or status.notes:
        if status.notes:
            lines.append(status.notes)
        lines.append(
            "See README (Linux / v4l2loopback). Meeting apps should pick the "
            "Video Loopback device after shunkan-ido --virtual-camera is running."
        )
        return "\n".join(lines)

    if not status.installed:
        lines.append("Virtual camera needs a one-time OBS Studio install.")
        if status.platform == "darwin":
            lines.append("  brew install --cask obs")
            lines.append(f"  or download from {_OBS_DOWNLOAD}")
        else:
            lines.append(f"  Download OBS from {_OBS_DOWNLOAD}")
        lines.append("Then run:  shunkan-ido --setup-virtual-camera")
        lines.append("After that, daily use is just:  shunkan-ido --virtual-camera")
        return "\n".join(lines)

    if open_failed:
        lines.append(
            "Could not open the virtual camera. Complete this one-time OBS prime, "
            "then retry (OBS does not need to stay open afterward):"
        )
    else:
        lines.append("One-time virtual camera setup (OBS can close afterward):")
    lines.append("  1. Run:  shunkan-ido --setup-virtual-camera")
    lines.append(
        "     (or in OBS: Start Virtual Camera once, then Stop, then quit OBS)"
    )
    if status.platform == "darwin":
        lines.append(
            "  2. If macOS blocked a camera extension, allow OBS under "
            "System Settings → Privacy & Security / Login Items & Extensions."
        )
    lines.append(
        "  3. In Zoom / Teams / Meet, choose **OBS Virtual Camera** as your camera."
    )
    lines.append("Daily:  shunkan-ido --virtual-camera   (preview + meeting feed)")
    return "\n".join(lines)


def prime_obs_virtual_camera(
    status: ObsStatus | None = None,
    *,
    wait_s: float = _PRIME_WAIT_S,
) -> bool:
    """Launch OBS with ``--startvirtualcam`` so the device is registered once.

    Returns True if the launch command succeeded. Does not guarantee Zoom sees
    the device yet (macOS may still need Camera Extension approval).
    """
    status = status if status is not None else detect_obs()
    if not status.installed or status.path is None:
        _log.warning("Cannot prime virtual camera: OBS is not installed")
        return False

    try:
        if status.platform == "darwin":
            cmd = [
                "open",
                "-a",
                str(status.path),
                "--args",
                "--startvirtualcam",
                "--minimize-to-tray",
            ]
            completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
        elif status.platform == "win32":
            cmd = [
                str(status.path),
                "--startvirtualcam",
                "--minimize-to-tray",
            ]
            completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
        else:
            _log.warning("OBS priming is not used on %s", status.platform)
            return False
    except OSError as exc:
        _log.warning("Failed to launch OBS for virtual-camera prime: %s", exc)
        return False

    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        _log.warning(
            "OBS prime launch failed (exit %s)%s",
            completed.returncode,
            f": {err}" if err else "",
        )
        return False

    if wait_s > 0:
        time.sleep(wait_s)
    _log.info(
        "OBS Virtual Camera prime launched. You can quit OBS after confirming "
        "the virtual camera works; it is not needed on every call."
    )
    return True
