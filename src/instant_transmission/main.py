"""Instant Transmission webcam loop.

Wires capture, calibration, gesture, effects, audio, and preview into one
process. ``run`` returns a process exit code; ``main`` is the console entry.
"""

from __future__ import annotations

import logging
import signal
import time

import cv2
import numpy as np

from instant_transmission.audio import SfxPlayer
from instant_transmission.background import BackgroundCalibrator
from instant_transmission.capture import CameraCapture
from instant_transmission.config import AppConfig, parse_args
from instant_transmission.effects import compose_teleport
from instant_transmission.gesture import GestureDetector
from instant_transmission.output import FrameOutput
from instant_transmission.state import AppState, TeleportController
from instant_transmission.virtual_cam import (
    detect_obs,
    format_setup_guidance,
    prime_obs_virtual_camera,
)

_log = logging.getLogger(__name__)

_QUIT_KEYS = frozenset({ord("q"), ord("Q"), 27})
# A hitch shorter than this still counts in full. Longer stalls (first
# MediaPipe call, a blocked camera) cannot skip calibration or the teleport.
_MIN_DT_CAP_S = 0.1
_stop_requested = False


def _request_stop(_signum: int, _frame: object) -> None:
    """Ask the loop to exit. OpenCV's Qt window can ignore a default SIGINT."""
    global _stop_requested
    _stop_requested = True


def _arm_stop_signals() -> None:
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)


def _overlay_calibration(frame: np.ndarray, progress: float) -> np.ndarray:
    """Tell the user to leave the shot and show how much calibration remains.

    Hershey fonts used by ``cv2.putText`` are ASCII-only, so the ellipsis is
    three dots rather than a single Unicode character.
    """
    display = frame.copy()
    progress = float(np.clip(progress, 0.0, 1.0))
    label = f"Step out of frame... {round(progress * 100):.0f}%"
    origin = (40, 72)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(display, label, origin, font, 1.0, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(display, label, origin, font, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

    height, width = display.shape[:2]
    bar_w = min(480, max(width - 80, 1))
    bar_h = 16
    x, y = 40, 96
    y2 = min(y + bar_h, height - 1)
    x2 = min(x + bar_w, width - 1)
    cv2.rectangle(display, (x, y), (x2, y2), (0, 0, 0), thickness=-1)
    fill = int(bar_w * progress)
    if fill > 0:
        cv2.rectangle(
            display,
            (x, y),
            (min(x + fill, width - 1), y2),
            (255, 255, 255),
            thickness=-1,
        )
    return display


def _aligned(background: np.ndarray, frame: np.ndarray) -> np.ndarray:
    if background.shape == frame.shape:
        return background
    height, width = frame.shape[:2]
    return cv2.resize(background, (width, height))


def _display_frame(
    frame: np.ndarray,
    controller: TeleportController,
    calibrator: BackgroundCalibrator,
) -> np.ndarray:
    state = controller.state
    if state == AppState.CALIBRATING:
        return _overlay_calibration(frame, calibrator.progress)
    if state == AppState.VISIBLE:
        return frame

    background = calibrator.background
    if background is None:
        return frame
    background = _aligned(background, frame)
    if state == AppState.VANISHED:
        return background

    going_out = state == AppState.TELEPORTING_OUT
    return compose_teleport(
        frame,
        background,
        mask=None,
        progress=controller.progress,
        going_out=going_out,
    )


def _clamp_dt(elapsed: float, fps: int) -> float:
    """Limit one frame's timestep to about ``1/fps``, and at least 0.1s.

    Normal frame intervals pass through. A multi-second gap becomes a single
    short step so the teleport animation and calibration cannot jump to done.
    """
    if elapsed <= 0.0:
        return 0.0
    frame = 1.0 / max(int(fps), 1)
    return min(elapsed, max(frame, _MIN_DT_CAP_S))


def _loop(
    capture: CameraCapture,
    output: FrameOutput,
    gesture: GestureDetector,
    sfx: SfxPlayer,
    calibrator: BackgroundCalibrator,
    controller: TeleportController,
    fps: int,
) -> None:
    # Clock starts after model warmup, so the first live frame does not
    # include graph compilation. ``_clamp_dt`` covers any later stall.
    previous = time.perf_counter()
    while True:
        if _stop_requested:
            return
        frame = cv2.flip(capture.read(), 1)
        now = time.perf_counter()
        dt = _clamp_dt(now - previous, fps)
        previous = now

        state = controller.state
        if state == AppState.CALIBRATING:
            if calibrator.update(frame, dt):
                controller.finish_calibration()
        elif state in (AppState.VISIBLE, AppState.VANISHED):
            if gesture.process(frame) and controller.on_gesture(now):
                sfx.play()

        # Draw the current teleport frame before update(). A completing
        # update leaves TELEPORTING_* and clears progress in the same call,
        # so the in-progress frame would be skipped if update ran first.
        display = _display_frame(frame, controller, calibrator)
        controller.update(now, dt)
        output.send(display)

        # Qt's waitKey can replace the SIGINT handler, so put ours back
        # every frame. A tap that lands inside waitKey is caught on the
        # next frame via _stop_requested.
        _arm_stop_signals()
        key = cv2.waitKey(1) & 0xFF
        _arm_stop_signals()
        if key in _QUIT_KEYS or _stop_requested:
            return


def _close(resource: object) -> None:
    close = getattr(resource, "close", None)
    if close is None:
        return
    try:
        close()
    except Exception:
        _log.warning("warning: failed to close %s", type(resource).__name__, exc_info=True)


def _run_setup_virtual_camera() -> int:
    """One-time OBS Virtual Camera prime; does not open the webcam preview."""
    status = detect_obs()
    if status.platform == "linux":
        _log.info("%s", format_setup_guidance(status, open_failed=False))
        return 0
    if not status.installed:
        _log.error("%s", format_setup_guidance(status, open_failed=False))
        return 1
    _log.info("Priming OBS Virtual Camera (one-time)…")
    if not prime_obs_virtual_camera(status):
        _log.error("%s", format_setup_guidance(status, open_failed=True))
        return 1
    _log.info(
        "Prime launched. In OBS you can Stop Virtual Camera and quit when ready.\n"
        "Then run:  shunkan-ido --virtual-camera\n"
        "In Zoom/Teams/Meet select: OBS Virtual Camera"
    )
    return 0


def run(config: AppConfig) -> int:
    """Run the preview loop. Returns 0 on quit, 1 if capture or the loop fails."""
    if config.setup_virtual_camera:
        return _run_setup_virtual_camera()

    global _stop_requested
    _stop_requested = False
    _arm_stop_signals()
    capture: CameraCapture | None = None
    output: FrameOutput | None = None
    gesture: GestureDetector | None = None
    sfx: SfxPlayer | None = None
    try:
        capture = CameraCapture(config.camera, config.width, config.height, config.fps)
        output = FrameOutput(
            width=config.width,
            height=config.height,
            fps=config.fps,
            show_preview=True,
            virtual_camera=config.virtual_camera,
            virtual_backend=config.virtual_backend,
        )
        gesture = GestureDetector(should_stop=lambda: _stop_requested)
        _log.info("Loading models…")
        gesture.warmup(config.width, config.height)
        if _stop_requested:
            _log.info("Interrupted during model load")
            return 0
        sfx = SfxPlayer(config.sfx_path, config.sfx_enabled)
        calibrator = BackgroundCalibrator(config.calibration_seconds)
        controller = TeleportController(config.cooldown_seconds, config.teleport_seconds)
        _loop(capture, output, gesture, sfx, calibrator, controller, config.fps)
        return 0
    except KeyboardInterrupt:
        _log.info("Interrupted")
        return 0
    except RuntimeError as exc:
        if str(exc) == "download cancelled":
            _log.info("Interrupted during model load")
            return 0
        _log.error("%s", exc)
        return 1
    except Exception:
        _log.exception("Instant Transmission stopped")
        return 1
    finally:
        _close(gesture)
        _close(sfx)
        _close(output)
        _close(capture)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
