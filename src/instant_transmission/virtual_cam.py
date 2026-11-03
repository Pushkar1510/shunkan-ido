"""Virtual-camera detection and setup for Ubuntu and Windows.

macOS is out of product scope. Linux uses ``v4l2loopback`` labeled
``Shunkan-Ido``. Windows uses OBS Virtual Camera via ``pyvirtualcam`` after a
one-time OBS install (setup script / winget), not a separate daily OBS workflow.
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

LOOPBACK_LABEL = "Shunkan-Ido"
_OBS_DOWNLOAD = "https://obsproject.com/"
_PRIME_WAIT_S = 4.0
_LINUX_MODPROBE = (
    f"sudo modprobe v4l2loopback devices=1 video_nr=10 "
    f"card_label={LOOPBACK_LABEL} exclusive_caps=1"
)


@dataclass(frozen=True)
class LoopbackStatus:
    """Linux v4l2loopback readiness."""

    platform: str
    module_loaded: bool
    device: Path | None
    label: str = LOOPBACK_LABEL
    notes: str = ""


@dataclass(frozen=True)
class ObsStatus:
    """Windows OBS install status (virtual cam provider for pyvirtualcam)."""

    platform: str
    installed: bool
    path: Path | None
    notes: str = ""


@dataclass(frozen=True)
class SetupResult:
    ok: bool
    message: str
    device: Path | None = None


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
    """Return whether OBS appears installed (Windows meeting virtual cam)."""
    platform = sys.platform
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
            notes="Linux uses v4l2loopback (not OBS).",
        )
    return ObsStatus(
        platform=platform,
        installed=False,
        path=None,
        notes="This build targets Ubuntu and Windows only; macOS is not supported.",
    )


def _sysfs_loopback_devices() -> list[Path]:
    """Return ``/dev/video*`` nodes backed by v4l2loopback when sysfs is present."""
    sys_class = Path("/sys/class/video4linux")
    if not sys_class.is_dir():
        return []
    found: list[Path] = []
    for entry in sorted(sys_class.iterdir()):
        name = entry.name
        if not name.startswith("video"):
            continue
        driver = entry / "device" / "driver"
        try:
            target = driver.resolve().name if driver.exists() else ""
        except OSError:
            target = ""
        if "v4l2loopback" not in target:
            # Some systems expose name via uevent
            uevent = entry / "device" / "uevent"
            text = ""
            if uevent.is_file():
                try:
                    text = uevent.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    text = ""
            if "v4l2loopback" not in text.lower():
                name_file = entry / "name"
                try:
                    card = name_file.read_text(encoding="utf-8").strip() if name_file.is_file() else ""
                except OSError:
                    card = ""
                if card != LOOPBACK_LABEL and "loopback" not in card.lower():
                    continue
        found.append(Path("/dev") / name)
    return found


def _device_card_name(device: Path) -> str:
    sys_name = Path("/sys/class/video4linux") / device.name / "name"
    try:
        if sys_name.is_file():
            return sys_name.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


def detect_linux_loopback() -> LoopbackStatus:
    """Detect whether a Shunkan-Ido (or any) v4l2loopback device is available."""
    if not sys.platform.startswith("linux"):
        return LoopbackStatus(
            platform=sys.platform,
            module_loaded=False,
            device=None,
            notes="v4l2loopback is only used on Linux.",
        )

    module_loaded = False
    try:
        modules = Path("/proc/modules")
        if modules.is_file():
            module_loaded = "v4l2loopback" in modules.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        module_loaded = False

    devices = _sysfs_loopback_devices()
    preferred: Path | None = None
    for dev in devices:
        if _device_card_name(dev) == LOOPBACK_LABEL:
            preferred = dev
            break
    if preferred is None and devices:
        preferred = devices[0]

    notes = ""
    if not module_loaded and preferred is None:
        notes = "v4l2loopback is not loaded."
    elif preferred is not None and _device_card_name(preferred) != LOOPBACK_LABEL:
        notes = (
            f"Found loopback {preferred} but label is not {LOOPBACK_LABEL!r}; "
            "prefer reloading with the setup script."
        )

    return LoopbackStatus(
        platform="linux",
        module_loaded=module_loaded or preferred is not None,
        device=preferred,
        notes=notes,
    )


def preferred_linux_device() -> str | None:
    """Device path string for pyvirtualcam, if a loopback node exists."""
    status = detect_linux_loopback()
    if status.device is None:
        return None
    return str(status.device)


def preferred_backend(platform: str | None = None) -> str | None:
    """Default pyvirtualcam backend for this OS."""
    platform = platform or sys.platform
    if platform.startswith("linux"):
        return "v4l2loopback"
    if platform == "win32":
        return "obs"
    return None


def format_linux_setup_guidance(*, open_failed: bool = False) -> str:
    status = detect_linux_loopback()
    lines: list[str] = []
    if open_failed:
        lines.append("Could not open the Linux virtual camera.")
    lines.append("Ubuntu / Debian one-time setup (no OBS):")
    lines.append("  1. Run:  bash packaging/ubuntu/setup-virtual-camera.sh")
    lines.append("     or:")
    lines.append("       sudo apt install -y v4l2loopback-dkms v4l2loopback-utils")
    lines.append(f"       {_LINUX_MODPROBE}")
    lines.append("  2. Run:  shunkan-ido --setup-virtual-camera   # verifies the device")
    lines.append("  3. Daily:  shunkan-ido --virtual-camera")
    lines.append(
        f"  4. In Meet/Zoom/Teams pick the camera named {LOOPBACK_LABEL!r} "
        "(or Video Loopback)."
    )
    if status.device is not None:
        lines.append(f"Detected loopback device: {status.device}")
    elif status.notes:
        lines.append(status.notes)
    return "\n".join(lines)


def format_windows_setup_guidance(
    status: ObsStatus | None = None,
    *,
    open_failed: bool = False,
) -> str:
    status = status if status is not None else detect_obs()
    lines: list[str] = []
    if open_failed:
        lines.append("Could not open the Windows virtual camera.")
    if not status.installed:
        lines.append("Windows one-time setup (OBS Virtual Camera provider):")
        lines.append("  1. Run:  powershell -File packaging/windows/setup-virtual-camera.ps1")
        lines.append("     or: winget install -e --id OBSProject.OBSStudio")
        lines.append(f"     or download OBS from {_OBS_DOWNLOAD}")
        lines.append("  2. Run:  shunkan-ido --setup-virtual-camera")
        lines.append("  3. Daily:  shunkan-ido --virtual-camera")
        lines.append("  4. In Meet/Zoom/Teams pick OBS Virtual Camera.")
        return "\n".join(lines)

    lines.append("OBS is installed. Complete one-time virtual camera prime:")
    lines.append("  1. Run:  shunkan-ido --setup-virtual-camera")
    lines.append("  2. Daily:  shunkan-ido --virtual-camera")
    lines.append("  3. In Meet/Zoom/Teams pick OBS Virtual Camera.")
    return "\n".join(lines)


def format_setup_guidance(
    *,
    open_failed: bool = False,
    platform: str | None = None,
) -> str:
    """Human-readable setup steps for the current (or given) platform."""
    platform = platform or sys.platform
    if platform.startswith("linux"):
        return format_linux_setup_guidance(open_failed=open_failed)
    if platform == "win32":
        return format_windows_setup_guidance(open_failed=open_failed)
    return (
        "macOS is not supported by this build.\n"
        "Use Ubuntu or Windows. See packaging/ubuntu or packaging/windows."
    )


def setup_linux_virtual_camera(*, dry_run: bool = False) -> SetupResult:
    """Try to load v4l2loopback with the Shunkan-Ido label; return status."""
    if not sys.platform.startswith("linux"):
        return SetupResult(ok=False, message="Linux setup only runs on Linux.")

    current = detect_linux_loopback()
    if current.device is not None and _device_card_name(current.device) == LOOPBACK_LABEL:
        return SetupResult(
            ok=True,
            message=f"Virtual camera ready: {current.device} ({LOOPBACK_LABEL})",
            device=current.device,
        )

    if dry_run:
        return SetupResult(
            ok=False,
            message=(
                "Would install/load v4l2loopback.\n" + format_linux_setup_guidance()
            ),
            device=None,
        )

    # Attempt modprobe (may need sudo password / fail without privileges).
    cmd = [
        "sudo",
        "modprobe",
        "v4l2loopback",
        "devices=1",
        "video_nr=10",
        f"card_label={LOOPBACK_LABEL}",
        "exclusive_caps=1",
    ]
    try:
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError as exc:
        return SetupResult(
            ok=False,
            message=f"Failed to run modprobe: {exc}\n{format_linux_setup_guidance()}",
        )

    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        return SetupResult(
            ok=False,
            message=(
                f"modprobe failed (exit {completed.returncode})"
                + (f": {err}" if err else "")
                + "\n"
                + format_linux_setup_guidance()
            ),
        )

    time.sleep(0.5)
    status = detect_linux_loopback()
    if status.device is None:
        return SetupResult(
            ok=False,
            message=(
                "modprobe succeeded but no loopback device was found.\n"
                + format_linux_setup_guidance()
            ),
        )
    return SetupResult(
        ok=True,
        message=f"Virtual camera ready: {status.device} ({_device_card_name(status.device) or LOOPBACK_LABEL})",
        device=status.device,
    )


def prime_obs_virtual_camera(
    status: ObsStatus | None = None,
    *,
    wait_s: float = _PRIME_WAIT_S,
) -> bool:
    """Launch OBS with ``--startvirtualcam`` once (Windows)."""
    status = status if status is not None else detect_obs()
    if status.platform != "win32":
        _log.warning("OBS priming is only used on Windows in this build")
        return False
    if not status.installed or status.path is None:
        _log.warning("Cannot prime virtual camera: OBS is not installed")
        return False

    try:
        cmd = [str(status.path), "--startvirtualcam", "--minimize-to-tray"]
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
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
        "OBS Virtual Camera prime launched. You can quit OBS afterward; "
        "daily use is shunkan-ido --virtual-camera."
    )
    return True


def run_platform_setup() -> SetupResult:
    """CLI entry for ``--setup-virtual-camera``."""
    if sys.platform.startswith("linux"):
        return setup_linux_virtual_camera()
    if sys.platform == "win32":
        status = detect_obs()
        if not status.installed:
            return SetupResult(ok=False, message=format_windows_setup_guidance(status))
        if not prime_obs_virtual_camera(status):
            return SetupResult(
                ok=False,
                message=format_windows_setup_guidance(status, open_failed=True),
            )
        return SetupResult(
            ok=True,
            message=(
                "OBS Virtual Camera primed.\n"
                "Daily: shunkan-ido --virtual-camera\n"
                "In Meet/Zoom/Teams select: OBS Virtual Camera"
            ),
        )
    return SetupResult(
        ok=False,
        message=format_setup_guidance(),
    )

