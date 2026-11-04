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
from instant_transmission.phoenix_fx import PhoenixOrb, draw_orbs
from instant_transmission.snap_gesture import SnapDetector
from instant_transmission.state import AppState, TeleportController
from instant_transmission.virtual_cam import run_platform_setup

_log = logging.getLogger(__name__)

_QUIT_KEYS = frozenset({ord("q"), ord("Q"), 27})
_START_CALIBRATION_KEYS = frozenset({ord(" "), 13})  # Space, Enter
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


def _draw_banner(display: np.ndarray, lines: list[str], *, y0: int = 72) -> None:
    """Draw outlined ASCII text lines (Hershey fonts are ASCII-only)."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    y = y0
    for line in lines:
        origin = (40, y)
        cv2.putText(display, line, origin, font, 1.0, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(display, line, origin, font, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        y += 40


def _overlay_waiting(frame: np.ndarray) -> np.ndarray:
    """Ask the user to leave the shot before empty-room capture starts."""
    display = frame.copy()
    _draw_banner(
        display,
        [
            "Step out of the frame",
            "Press SPACE (or Enter) when ready",
        ],
    )
    return display


def _overlay_calibration(frame: np.ndarray, progress: float) -> np.ndarray:
    """Tell the user to stay out of the shot and show calibration progress."""
    display = frame.copy()
    progress = float(np.clip(progress, 0.0, 1.0))
    _draw_banner(display, [f"Capturing empty room... {round(progress * 100):.0f}%"])

    height, width = display.shape[:2]
    bar_w = min(480, max(width - 80, 1))
    bar_h = 16
    x, y = 40, 120
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
    if state == AppState.WAITING:
        return _overlay_waiting(frame)
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


def _drop_expired_orbs(orbs: list[PhoenixOrb], now: float) -> None:
    """Remove orbs whose life has ended. ``draw_orbs`` does this only when called."""
    orbs[:] = [orb for orb in orbs if now < orb.born_at + orb.duration]


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
    phoenix_sfx: SfxPlayer | None = None,
    *,
    phoenix_enabled: bool = True,
) -> None:
    # Clock starts after model warmup, so the first live frame does not
    # include graph compilation. ``_clamp_dt`` covers any later stall.
    previous = time.perf_counter()
    orbs: list[PhoenixOrb] = []
    snap = SnapDetector()
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
            result = gesture.process(frame)
            if result.instant_transmission and controller.on_gesture(now):
                sfx.play()
            elif (
                phoenix_enabled
                and state == AppState.VISIBLE
                and not result.instant_transmission
            ):
                for event in snap.update(result.hands, now):
                    x, y = event.palm_xy
                    orbs.append(PhoenixOrb(x=x, y=y, born_at=now))
                    if phoenix_sfx is not None:
                        phoenix_sfx.play()

        # Draw the current teleport frame before update(). A completing
        # update leaves TELEPORTING_* and clears progress in the same call,
        # so the in-progress frame would be skipped if update ran first.
        display = _display_frame(frame, controller, calibrator)
        _drop_expired_orbs(orbs, now)
        if phoenix_enabled and controller.state == AppState.VISIBLE:
            display = draw_orbs(display, orbs, now)
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
        if key in _START_CALIBRATION_KEYS and controller.state == AppState.WAITING:
            controller.start_calibration()


def _close(resource: object) -> None:
    close = getattr(resource, "close", None)
    if close is None:
        return
    try:
        close()
    except Exception:
        _log.warning("warning: failed to close %s", type(resource).__name__, exc_info=True)


def _run_setup_virtual_camera() -> int:
    """One-time virtual camera setup (Linux loopback or Windows OBS prime)."""
    result = run_platform_setup()
    if result.ok:
        _log.info("%s", result.message)
        return 0
    _log.error("%s", result.message)
    return 1


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
    phoenix_sfx: SfxPlayer | None = None
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
        phoenix_sfx = SfxPlayer(config.phoenix_sfx_path, config.phoenix_enabled)
        calibrator = BackgroundCalibrator(config.calibration_seconds)
        controller = TeleportController(config.cooldown_seconds, config.teleport_seconds)
        _loop(
            capture,
            output,
            gesture,
            sfx,
            calibrator,
            controller,
            config.fps,
            phoenix_sfx,
            phoenix_enabled=config.phoenix_enabled,
        )
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
        _close(phoenix_sfx)
        _close(sfx)
        _close(output)
        _close(capture)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
