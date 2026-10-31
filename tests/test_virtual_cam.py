"""Tests for OBS detection and virtual-camera setup guidance."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from instant_transmission.virtual_cam import (
    ObsStatus,
    detect_obs,
    format_setup_guidance,
    prime_obs_virtual_camera,
)


def test_detect_obs_macos_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = tmp_path / "OBS.app"
    app.mkdir()
    monkeypatch.setattr("instant_transmission.virtual_cam.sys.platform", "darwin")
    monkeypatch.setattr(
        "instant_transmission.virtual_cam._macos_obs_candidates",
        lambda: [app],
    )
    status = detect_obs()
    assert status.platform == "darwin"
    assert status.installed is True
    assert status.path == app


def test_detect_obs_macos_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "OBS.app"
    monkeypatch.setattr("instant_transmission.virtual_cam.sys.platform", "darwin")
    monkeypatch.setattr(
        "instant_transmission.virtual_cam._macos_obs_candidates",
        lambda: [missing],
    )
    status = detect_obs()
    assert status.installed is False
    assert status.path is None


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


def test_guidance_when_obs_missing_macos() -> None:
    status = ObsStatus(
        platform="darwin",
        installed=False,
        path=None,
        notes="",
    )
    text = format_setup_guidance(status, open_failed=True)
    assert "OBS" in text
    assert "brew install --cask obs" in text
    assert "one-time" in text.lower() or "once" in text.lower()


def test_guidance_when_obs_installed_but_open_failed() -> None:
    status = ObsStatus(
        platform="darwin",
        installed=True,
        path=Path("/Applications/OBS.app"),
        notes="",
    )
    text = format_setup_guidance(status, open_failed=True)
    assert "Start Virtual Camera" in text or "setup-virtual-camera" in text
    assert "OBS Virtual Camera" in text


def test_prime_obs_virtual_camera_macos(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = tmp_path / "OBS.app"
    app.mkdir()
    status = ObsStatus(platform="darwin", installed=True, path=app, notes="")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        calls.append(cmd)
        result = MagicMock()
        result.returncode = 0
        return result

    monkeypatch.setattr("instant_transmission.virtual_cam.subprocess.run", fake_run)
    monkeypatch.setattr("instant_transmission.virtual_cam.time.sleep", lambda _s: None)
    assert prime_obs_virtual_camera(status) is True
    assert calls
    assert calls[0][0] == "open"
    assert "--startvirtualcam" in calls[0]


def test_prime_obs_virtual_camera_refuses_without_obs() -> None:
    status = ObsStatus(platform="darwin", installed=False, path=None, notes="")
    assert prime_obs_virtual_camera(status) is False
