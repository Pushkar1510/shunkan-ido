"""Tests for virtual-camera detection and setup guidance (Ubuntu / Windows)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from instant_transmission.virtual_cam import (
    LOOPBACK_LABEL,
    ObsStatus,
    detect_linux_loopback,
    detect_obs,
    format_linux_setup_guidance,
    format_setup_guidance,
    format_windows_setup_guidance,
    preferred_backend,
    prime_obs_virtual_camera,
    run_platform_setup,
    setup_linux_virtual_camera,
)


def test_preferred_backend_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    assert preferred_backend("linux") == "v4l2loopback"


def test_preferred_backend_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    assert preferred_backend("win32") == "obs"


def test_detect_obs_windows_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    exe = tmp_path / "obs64.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr("instant_transmission.virtual_cam.sys.platform", "win32")
    monkeypatch.setattr(
        "instant_transmission.virtual_cam._windows_obs_candidates",
        lambda: [exe],
    )
    status = detect_obs()
    assert status.platform == "win32"
    assert status.installed is True
    assert status.path == exe


def test_detect_obs_linux_skips_obs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("instant_transmission.virtual_cam.sys.platform", "linux")
    status = detect_obs()
    assert status.platform == "linux"
    assert status.installed is False
    assert "v4l2loopback" in status.notes.lower()


def test_macos_guidance_unsupported() -> None:
    text = format_setup_guidance(platform="darwin")
    assert "not supported" in text.lower()
    assert "Ubuntu" in text or "Windows" in text


def test_linux_setup_guidance_mentions_label() -> None:
    text = format_linux_setup_guidance()
    assert LOOPBACK_LABEL in text
    assert "v4l2loopback" in text
    assert "packaging/ubuntu/setup-virtual-camera.sh" in text


def test_windows_guidance_when_obs_missing() -> None:
    status = ObsStatus(platform="win32", installed=False, path=None)
    text = format_windows_setup_guidance(status, open_failed=True)
    assert "OBS" in text
    assert "setup-virtual-camera" in text
    assert "winget" in text or "packaging/windows" in text


def test_detect_linux_loopback_prefers_labeled_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("instant_transmission.virtual_cam.sys.platform", "linux")
    labeled = Path("/dev/video10")
    other = Path("/dev/video2")

    monkeypatch.setattr(
        "instant_transmission.virtual_cam._sysfs_loopback_devices",
        lambda: [other, labeled],
    )
    monkeypatch.setattr(
        "instant_transmission.virtual_cam._device_card_name",
        lambda device: LOOPBACK_LABEL if device == labeled else "Loopback",
    )

    # Pretend the module is loaded without touching real /proc.
    class _Modules:
        def is_file(self) -> bool:
            return True

        def read_text(self, *a: object, **k: object) -> str:
            return "v4l2loopback 1 0 - Live 0x0\n"

    real_path = Path

    def path_ctor(value: object = "", *_a: object, **_k: object) -> object:
        if str(value) == "/proc/modules":
            return _Modules()
        return real_path(value)

    monkeypatch.setattr("instant_transmission.virtual_cam.Path", path_ctor)
    status = detect_linux_loopback()
    assert status.module_loaded is True
    assert status.device == labeled


def test_setup_linux_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("instant_transmission.virtual_cam.sys.platform", "linux")
    monkeypatch.setattr(
        "instant_transmission.virtual_cam.detect_linux_loopback",
        lambda: MagicMock(device=None, notes="not loaded"),
    )
    result = setup_linux_virtual_camera(dry_run=True)
    assert result.ok is False
    assert "v4l2loopback" in result.message


def test_setup_linux_already_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("instant_transmission.virtual_cam.sys.platform", "linux")
    device = Path("/dev/video10")
    monkeypatch.setattr(
        "instant_transmission.virtual_cam.detect_linux_loopback",
        lambda: MagicMock(
            device=device,
            module_loaded=True,
            notes="",
        ),
    )
    monkeypatch.setattr(
        "instant_transmission.virtual_cam._device_card_name",
        lambda _d: LOOPBACK_LABEL,
    )
    monkeypatch.setattr(
        "instant_transmission.virtual_cam.linux_loopback_producer_ready",
        lambda _d=None: True,
    )
    result = setup_linux_virtual_camera()
    assert result.ok is True
    assert result.device == device


def test_setup_linux_reloads_when_not_output_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("instant_transmission.virtual_cam.sys.platform", "linux")
    device = Path("/dev/video10")
    calls: list[list[str]] = []

    def fake_detect() -> MagicMock:
        return MagicMock(device=device, module_loaded=True, notes="")

    monkeypatch.setattr(
        "instant_transmission.virtual_cam.detect_linux_loopback",
        fake_detect,
    )
    monkeypatch.setattr(
        "instant_transmission.virtual_cam._device_card_name",
        lambda _d: LOOPBACK_LABEL,
    )
    # First check fails (stuck caps); after reload, ready.
    ready_states = iter([False, True])
    monkeypatch.setattr(
        "instant_transmission.virtual_cam.linux_loopback_producer_ready",
        lambda _d=None: next(ready_states, True),
    )
    monkeypatch.setattr(
        "instant_transmission.virtual_cam._elevated_linux_reload_cmd",
        lambda: ["pkexec", "bash", "-c", "modprobe -r v4l2loopback; modprobe v4l2loopback"],
    )

    def fake_run(cmd: list[str], **_kwargs: object) -> MagicMock:
        calls.append(cmd)
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = ""
        return result

    monkeypatch.setattr("instant_transmission.virtual_cam.subprocess.run", fake_run)
    monkeypatch.setattr("instant_transmission.virtual_cam.time.sleep", lambda _s: None)
    result = setup_linux_virtual_camera()
    assert result.ok is True
    assert calls and "pkexec" in calls[0][0]
    assert any("modprobe -r" in part for part in calls[0])


def test_prime_obs_refuses_non_windows() -> None:
    status = ObsStatus(platform="linux", installed=False, path=None)
    assert prime_obs_virtual_camera(status) is False


def test_prime_obs_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    exe = tmp_path / "obs64.exe"
    exe.write_bytes(b"")
    status = ObsStatus(platform="win32", installed=True, path=exe)
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        calls.append(cmd)
        result = MagicMock()
        result.returncode = 0
        return result

    monkeypatch.setattr("instant_transmission.virtual_cam.subprocess.run", fake_run)
    monkeypatch.setattr("instant_transmission.virtual_cam.time.sleep", lambda _s: None)
    assert prime_obs_virtual_camera(status) is True
    assert calls[0][0] == str(exe)
    assert "--startvirtualcam" in calls[0]


def test_run_platform_setup_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("instant_transmission.virtual_cam.sys.platform", "darwin")
    result = run_platform_setup()
    assert result.ok is False
    assert "not supported" in result.message.lower()
