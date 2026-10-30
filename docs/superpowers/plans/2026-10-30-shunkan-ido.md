# Shunkan-Ido (Instant Transmission Cam) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python desktop app that detects Goku’s Instant Transmission pose and teleports the user out of / into a webcam feed (preview + optional virtual camera for Zoom/Teams/Meet).

**Architecture:** OpenCV captures frames → MediaPipe Hands + Face detect the forehead pose → a small state machine drives speed-lines + background swap → preview always, `pyvirtualcam` optional. All processing stays on-device.

**Tech Stack:** Python 3.11+, OpenCV, MediaPipe, NumPy, pygame (SFX), pyvirtualcam (optional), pytest

## Global Constraints

- Python 3.11+
- Platforms: Linux, Windows, macOS (desktop only; no iOS/Android)
- Instant Transmission mode only in v1 (no other vanish modes)
- Gesture triggers **immediately** (no hold countdown); cooldown after animation completes
- Empty-room background capture at startup
- Preview always on; virtual camera only with `--virtual-camera`
- Do **not** commit copyrighted DBZ audio; user supplies `assets/instant_transmission.mp3`
- No cloud uploads; process frames locally
- Package lives under `src/instant_transmission/`
- Repo: `https://github.com/Pushkar1510/shunkan-ido.git` (author Pushkar1510)

## File Structure

| Path | Responsibility |
|------|----------------|
| `pyproject.toml` | Package metadata, deps, pytest/cli entry |
| `requirements.txt` | Pip-friendly dependency pin list |
| `README.md` | Setup, SFX note, virtual cam per OS, usage |
| `assets/.gitkeep` | Placeholder; SFX gitignored |
| `src/instant_transmission/__init__.py` | Package version |
| `src/instant_transmission/config.py` | `AppConfig` dataclass + CLI argparse |
| `src/instant_transmission/capture.py` | Webcam open/read/release |
| `src/instant_transmission/background.py` | Empty-room calibration buffer |
| `src/instant_transmission/state.py` | Teleport state machine + cooldown |
| `src/instant_transmission/gesture.py` | Landmark geometry + Instant Transmission detect |
| `src/instant_transmission/effects.py` | Speed-lines + crossfade compositing |
| `src/instant_transmission/audio.py` | Non-blocking SFX via pygame |
| `src/instant_transmission/output.py` | Preview + optional virtual camera |
| `src/instant_transmission/main.py` | Main loop wiring |
| `tests/test_config.py` | CLI/config parsing |
| `tests/test_state.py` | State transitions + cooldown |
| `tests/test_gesture.py` | Synthetic landmark pose checks |
| `tests/test_effects.py` | Crossfade / speed-line shape checks |
| `tests/test_background.py` | Calibration completion |

---

### Task 1: Project scaffold + config CLI

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `assets/.gitkeep`
- Create: `src/instant_transmission/__init__.py`
- Create: `src/instant_transmission/config.py`
- Create: `tests/test_config.py`
- Create: `README.md` (minimal stub; expand in Task 8)
- Modify: `.gitignore` (ensure `assets/*.mp3` already ignored)

**Interfaces:**
- Produces: `AppConfig` dataclass; `parse_args(argv: list[str] | None = None) -> AppConfig`

- [ ] **Step 1: Write failing tests for config defaults and flags**

```python
# tests/test_config.py
from instant_transmission.config import parse_args


def test_defaults():
    cfg = parse_args([])
    assert cfg.camera == 0
    assert cfg.width == 1280
    assert cfg.height == 720
    assert cfg.fps == 30
    assert cfg.virtual_camera is False
    assert cfg.sfx_enabled is True
    assert cfg.calibration_seconds == 4.0
    assert cfg.sfx_path.name == "instant_transmission.mp3"


def test_virtual_camera_flag():
    cfg = parse_args(["--virtual-camera"])
    assert cfg.virtual_camera is True


def test_no_sfx_flag():
    cfg = parse_args(["--no-sfx"])
    assert cfg.sfx_enabled is False
```

- [ ] **Step 2: Run tests — expect fail (module missing)**

Run: `cd /home/pushkar/Documents/Pushkar/DBZ && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]" 2>/dev/null; pip install pytest numpy && PYTHONPATH=src pytest tests/test_config.py -v`

Expected: FAIL — `ModuleNotFoundError` or collection error for `instant_transmission.config`

- [ ] **Step 3: Create package layout and config implementation**

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "shunkan-ido"
version = "0.1.0"
description = "Instant Transmission webcam vanish for video meetings"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "opencv-python>=4.8",
  "mediapipe>=0.10",
  "numpy>=1.26",
  "pygame>=2.5",
  "pyvirtualcam>=0.12",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
shunkan-ido = "instant_transmission.main:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`requirements.txt`:

```
opencv-python>=4.8
mediapipe>=0.10
numpy>=1.26
pygame>=2.5
pyvirtualcam>=0.12
pytest>=8.0
```

`src/instant_transmission/__init__.py`:

```python
__version__ = "0.1.0"
```

`src/instant_transmission/config.py`:

```python
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SFX = _ROOT / "assets" / "instant_transmission.mp3"


@dataclass(frozen=True)
class AppConfig:
    camera: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    virtual_camera: bool = False
    virtual_backend: str | None = None
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
        sfx_path=args.sfx,
        sfx_enabled=not args.no_sfx,
        calibration_seconds=args.calibration_seconds,
    )
```

Minimal `README.md`:

```markdown
# shunkan-ido

Instant Transmission webcam vanish for Zoom / Teams / Meet.

See `docs/superpowers/specs/2026-10-30-instant-transmission-cam-design.md`.
```

`assets/.gitkeep`: empty file.

- [ ] **Step 4: Install editable package and run tests**

Run: `source .venv/bin/activate && pip install -e ".[dev]" && pytest tests/test_config.py -v`

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml requirements.txt README.md assets/.gitkeep \
  src/instant_transmission/__init__.py src/instant_transmission/config.py \
  tests/test_config.py .gitignore docs/
git commit -m "$(cat <<'EOF'
chore: scaffold shunkan-ido package and CLI config

EOF
)"
```

(Only commit if local `user.name` / `user.email` are set to Pushkar1510 / personal email.)

---

### Task 2: Teleport state machine

**Files:**
- Create: `src/instant_transmission/state.py`
- Create: `tests/test_state.py`

**Interfaces:**
- Consumes: `cooldown_seconds: float`, `teleport_seconds: float`
- Produces:
  - `class AppState(Enum)`
  - `class TeleportController` with:
    - `state: AppState`
    - `progress: float`  # 0..1 during teleport animations
    - `finish_calibration() -> None`
    - `on_gesture(now: float) -> bool`  # True if teleport started
    - `update(now: float, dt: float) -> None`
    - `in_cooldown(now: float) -> bool`

- [ ] **Step 1: Write failing state tests**

```python
# tests/test_state.py
from instant_transmission.state import AppState, TeleportController


def test_starts_calibrating():
    c = TeleportController(cooldown_seconds=0.8, teleport_seconds=0.5)
    assert c.state == AppState.CALIBRATING


def test_calibration_then_gesture_teleports_out():
    c = TeleportController(cooldown_seconds=0.8, teleport_seconds=0.5)
    c.finish_calibration()
    assert c.state == AppState.VISIBLE
    started = c.on_gesture(now=1.0)
    assert started is True
    assert c.state == AppState.TELEPORTING_OUT


def test_teleport_out_completes_to_vanished():
    c = TeleportController(cooldown_seconds=0.8, teleport_seconds=0.5)
    c.finish_calibration()
    c.on_gesture(now=0.0)
    c.update(now=0.6, dt=0.6)
    assert c.state == AppState.VANISHED


def test_gesture_during_cooldown_ignored():
    c = TeleportController(cooldown_seconds=1.0, teleport_seconds=0.2)
    c.finish_calibration()
    assert c.on_gesture(now=0.0) is True
    c.update(now=0.3, dt=0.3)  # -> VANISHED, cooldown starts
    assert c.state == AppState.VANISHED
    assert c.on_gesture(now=0.5) is False  # still cooling down


def test_reappear_cycle():
    c = TeleportController(cooldown_seconds=0.1, teleport_seconds=0.2)
    c.finish_calibration()
    c.on_gesture(now=0.0)
    c.update(now=0.25, dt=0.25)
    assert c.state == AppState.VANISHED
    c.update(now=0.4, dt=0.15)  # past cooldown
    assert c.on_gesture(now=0.4) is True
    assert c.state == AppState.TELEPORTING_IN
    c.update(now=0.7, dt=0.3)
    assert c.state == AppState.VISIBLE
```

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/test_state.py -v`  
Expected: FAIL — import error

- [ ] **Step 3: Implement state machine**

```python
# src/instant_transmission/state.py
from __future__ import annotations

from enum import Enum, auto


class AppState(Enum):
    CALIBRATING = auto()
    VISIBLE = auto()
    TELEPORTING_OUT = auto()
    VANISHED = auto()
    TELEPORTING_IN = auto()


class TeleportController:
    def __init__(self, cooldown_seconds: float, teleport_seconds: float) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.teleport_seconds = max(teleport_seconds, 1e-3)
        self.state = AppState.CALIBRATING
        self.progress = 0.0
        self._anim_elapsed = 0.0
        self._cooldown_until = 0.0

    def finish_calibration(self) -> None:
        if self.state == AppState.CALIBRATING:
            self.state = AppState.VISIBLE

    def in_cooldown(self, now: float) -> bool:
        return now < self._cooldown_until

    def on_gesture(self, now: float) -> bool:
        if self.in_cooldown(now):
            return False
        if self.state == AppState.VISIBLE:
            self.state = AppState.TELEPORTING_OUT
            self._anim_elapsed = 0.0
            self.progress = 0.0
            return True
        if self.state == AppState.VANISHED:
            self.state = AppState.TELEPORTING_IN
            self._anim_elapsed = 0.0
            self.progress = 0.0
            return True
        return False

    def update(self, now: float, dt: float) -> None:
        if self.state not in (AppState.TELEPORTING_OUT, AppState.TELEPORTING_IN):
            return
        self._anim_elapsed += dt
        self.progress = min(1.0, self._anim_elapsed / self.teleport_seconds)
        if self.progress < 1.0:
            return
        if self.state == AppState.TELEPORTING_OUT:
            self.state = AppState.VANISHED
        else:
            self.state = AppState.VISIBLE
        self.progress = 0.0
        self._cooldown_until = now + self.cooldown_seconds
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_state.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/instant_transmission/state.py tests/test_state.py
git commit -m "$(cat <<'EOF'
feat: add teleport state machine with cooldown

EOF
)"
```

---

### Task 3: Background calibration

**Files:**
- Create: `src/instant_transmission/background.py`
- Create: `tests/test_background.py`

**Interfaces:**
- Produces:
  - `class BackgroundCalibrator`:
    - `__init__(self, duration_seconds: float)`
    - `reset() -> None`
    - `update(frame: np.ndarray, dt: float) -> bool`  # True when done
    - `background: np.ndarray | None`
    - `progress: float`  # 0..1

- [ ] **Step 1: Write failing tests**

```python
# tests/test_background.py
import numpy as np
from instant_transmission.background import BackgroundCalibrator


def test_not_ready_until_duration():
    cal = BackgroundCalibrator(duration_seconds=1.0)
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    assert cal.update(frame, dt=0.4) is False
    assert cal.background is None
    assert cal.update(frame, dt=0.7) is True
    assert cal.background is not None
    assert cal.background.shape == frame.shape


def test_averages_frames():
    cal = BackgroundCalibrator(duration_seconds=0.2)
    a = np.zeros((2, 2, 3), dtype=np.uint8)
    b = np.full((2, 2, 3), 100, dtype=np.uint8)
    cal.update(a, dt=0.1)
    cal.update(b, dt=0.1)
    assert cal.background is not None
    # mean of 0 and 100 ~= 50
    assert int(cal.background.mean()) == 50
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/test_background.py -v`

- [ ] **Step 3: Implement calibrator**

```python
# src/instant_transmission/background.py
from __future__ import annotations

import numpy as np


class BackgroundCalibrator:
    def __init__(self, duration_seconds: float) -> None:
        self.duration_seconds = max(duration_seconds, 1e-3)
        self._elapsed = 0.0
        self._sum: np.ndarray | None = None
        self._count = 0
        self.background: np.ndarray | None = None

    @property
    def progress(self) -> float:
        return min(1.0, self._elapsed / self.duration_seconds)

    def reset(self) -> None:
        self._elapsed = 0.0
        self._sum = None
        self._count = 0
        self.background = None

    def update(self, frame: np.ndarray, dt: float) -> bool:
        if self.background is not None:
            return True
        f = frame.astype(np.float64)
        if self._sum is None:
            self._sum = np.zeros_like(f)
        self._sum += f
        self._count += 1
        self._elapsed += dt
        if self._elapsed < self.duration_seconds:
            return False
        assert self._sum is not None and self._count > 0
        self.background = (self._sum / self._count).clip(0, 255).astype(np.uint8)
        return True
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/test_background.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/instant_transmission/background.py tests/test_background.py
git commit -m "$(cat <<'EOF'
feat: add empty-room background calibrator

EOF
)"
```

---

### Task 4: Instant Transmission gesture geometry

**Files:**
- Create: `src/instant_transmission/gesture.py`
- Create: `tests/test_gesture.py`

**Interfaces:**
- Produces:
  - `is_instant_transmission(hand_landmarks, face_landmarks, image_size: tuple[int,int]) -> bool`
  - `class GestureDetector` wrapping MediaPipe Hands + Face Mesh:
    - `process(frame_bgr: np.ndarray) -> bool`  # True if pose detected this frame
    - `close() -> None`
- Geometry rules (normalized image coords):
  - Index + middle extended (tip farther from wrist than pip along finger axis)
  - Ring + pinky folded (tip closer to wrist than pip)
  - Index tip and middle tip within forehead radius of face forehead landmark
  - Index/middle tips close to each other (together)

- [ ] **Step 1: Write failing geometry unit tests with fake landmarks**

Use simple namespace objects with `.x`, `.y`, `.z` attributes. Forehead landmark ≈ `(0.5, 0.25)`. Tips of index/middle near forehead; ring/pinky tips near palm.

```python
# tests/test_gesture.py
from types import SimpleNamespace
from instant_transmission.gesture import is_instant_transmission


def _lm(x: float, y: float, z: float = 0.0):
    return SimpleNamespace(x=x, y=y, z=z)


def _hand(
    wrist=(0.5, 0.55),
    index_pip=(0.48, 0.40),
    index_tip=(0.50, 0.26),
    middle_pip=(0.52, 0.40),
    middle_tip=(0.52, 0.26),
    ring_pip=(0.54, 0.42),
    ring_tip=(0.54, 0.48),
    pinky_pip=(0.56, 0.43),
    pinky_tip=(0.56, 0.49),
):
    # MediaPipe hand indices used by implementation must match these slots.
    pts = [None] * 21
    pts[0] = _lm(*wrist)
    pts[6] = _lm(*index_pip)
    pts[8] = _lm(*index_tip)
    pts[10] = _lm(*middle_pip)
    pts[12] = _lm(*middle_tip)
    pts[14] = _lm(*ring_pip)
    pts[16] = _lm(*ring_tip)
    pts[18] = _lm(*pinky_pip)
    pts[20] = _lm(*pinky_tip)
    # Fill unused with wrist so attribute access is safe if probed
    for i, p in enumerate(pts):
        if p is None:
            pts[i] = _lm(*wrist)
    return pts


def _face_forehead():
    # Implementation should treat landmark 10 (MediaPipe Face Mesh) as forehead approx
    pts = [_lm(0.5, 0.5) for _ in range(468)]
    pts[10] = _lm(0.5, 0.25)
    return pts


def test_valid_instant_transmission_pose():
    assert is_instant_transmission(_hand(), _face_forehead(), (1280, 720)) is True


def test_rejects_when_fingers_far_from_forehead():
    hand = _hand(index_tip=(0.2, 0.8), middle_tip=(0.22, 0.8))
    assert is_instant_transmission(hand, _face_forehead(), (1280, 720)) is False


def test_rejects_open_palm():
    hand = _hand(
        ring_pip=(0.54, 0.40),
        ring_tip=(0.54, 0.26),
        pinky_pip=(0.56, 0.41),
        pinky_tip=(0.56, 0.27),
    )
    assert is_instant_transmission(hand, _face_forehead(), (1280, 720)) is False
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/test_gesture.py -v`

- [ ] **Step 3: Implement pure geometry + MediaPipe wrapper**

Implement `is_instant_transmission` with clear thresholds as module-level constants (`FOREHEAD_RADIUS`, `FINGER_TOGETHER_DIST`, etc.).

`GestureDetector.process`:
1. Run Face Mesh + Hands on BGR→RGB frame
2. If both present, call `is_instant_transmission`
3. Return bool

Keep MediaPipe init lazy; `close()` releases resources.

Tune thresholds so the three unit tests pass; document constants at top of `gesture.py`.

- [ ] **Step 4: Run unit tests — expect pass**

Run: `pytest tests/test_gesture.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/instant_transmission/gesture.py tests/test_gesture.py
git commit -m "$(cat <<'EOF'
feat: detect Instant Transmission pose from landmarks

EOF
)"
```

---

### Task 5: Visual effects (speed-lines + crossfade)

**Files:**
- Create: `src/instant_transmission/effects.py`
- Create: `tests/test_effects.py`

**Interfaces:**
- Produces:
  - `crossfade(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray`  # t in [0,1]
  - `apply_speed_lines(frame: np.ndarray, mask: np.ndarray | None, intensity: float) -> np.ndarray`
  - `compose_teleport(live, background, mask, progress, going_out: bool) -> np.ndarray`
    - First ~40% of progress: speed-lines dominate on live (or bg when coming in)
    - Remaining progress: crossfade live↔background

- [ ] **Step 1: Write failing effect tests**

```python
# tests/test_effects.py
import numpy as np
from instant_transmission.effects import crossfade, apply_speed_lines, compose_teleport


def test_crossfade_endpoints():
    a = np.zeros((8, 8, 3), dtype=np.uint8)
    b = np.full((8, 8, 3), 255, dtype=np.uint8)
    assert crossfade(a, b, 0.0).mean() == 0
    assert crossfade(a, b, 1.0).mean() == 255


def test_speed_lines_preserves_shape():
    frame = np.full((32, 32, 3), 40, dtype=np.uint8)
    out = apply_speed_lines(frame, mask=None, intensity=1.0)
    assert out.shape == frame.shape
    assert out.dtype == np.uint8


def test_compose_teleport_ends_on_background_when_going_out():
    live = np.zeros((16, 16, 3), dtype=np.uint8)
    bg = np.full((16, 16, 3), 200, dtype=np.uint8)
    out = compose_teleport(live, bg, mask=None, progress=1.0, going_out=True)
    assert abs(int(out.mean()) - 200) <= 1
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/test_effects.py -v`

- [ ] **Step 3: Implement effects**

```python
# Outline for src/instant_transmission/effects.py
# - crossfade via np.clip((1-t)*a + t*b)
# - speed lines: draw vertical white/cyan strokes where mask>0 (or full frame);
#   intensity scales alpha
# - compose_teleport: map progress → line_intensity + fade_t; blend accordingly
```

Use OpenCV `cv2.line` for comic vertical strokes seeded stably per-frame from progress so animation flickers slightly.

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/test_effects.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/instant_transmission/effects.py tests/test_effects.py
git commit -m "$(cat <<'EOF'
feat: add speed-line and crossfade teleport effects

EOF
)"
```

---

### Task 6: Capture, audio, and output adapters

**Files:**
- Create: `src/instant_transmission/capture.py`
- Create: `src/instant_transmission/audio.py`
- Create: `src/instant_transmission/output.py`
- Create: `tests/test_audio.py` (missing file / disabled behavior only — no real device)

**Interfaces:**
- `CameraCapture(camera: int, width: int, height: int, fps: int)`
  - `read() -> np.ndarray`
  - `close() -> None`
  - raises `RuntimeError` if camera won't open
- `SfxPlayer(path: Path, enabled: bool)`
  - `play() -> None`  # non-blocking; warn once if missing
  - `close() -> None`
- `FrameOutput(width, height, fps, show_preview: bool = True, virtual_camera: bool = False, virtual_backend: str | None = None)`
  - `send(frame_bgr: np.ndarray) -> None`
  - `close() -> None`
  - If virtual camera fails: print warning, continue preview-only

- [ ] **Step 1: Write audio unit tests**

```python
# tests/test_audio.py
from pathlib import Path
from instant_transmission.audio import SfxPlayer


def test_missing_sfx_does_not_raise(tmp_path: Path):
    player = SfxPlayer(tmp_path / "missing.mp3", enabled=True)
    player.play()  # warns once, no exception
    player.play()
    player.close()


def test_disabled_sfx_noop(tmp_path: Path):
    player = SfxPlayer(tmp_path / "missing.mp3", enabled=False)
    player.play()
    player.close()
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/test_audio.py -v`

- [ ] **Step 3: Implement capture / audio / output**

`capture.py`: `cv2.VideoCapture`, set width/height/fps props, `read` raises if grab fails repeatedly.

`audio.py`: init pygame mixer if enabled and file exists; `Sound.play()`; set `_warned` flag for missing file.

`output.py`:
- Always `cv2.imshow("shunkan-ido", frame)` when preview on
- If `virtual_camera`: try `pyvirtualcam.Camera(..., fmt=PixelFormat.BGR)`; on failure warn and disable
- `send` resizes frame to camera size if needed, `cam.send(np.ascontiguousarray(frame))`

- [ ] **Step 4: Run audio tests — expect pass**

Run: `pytest tests/test_audio.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/instant_transmission/capture.py src/instant_transmission/audio.py \
  src/instant_transmission/output.py tests/test_audio.py
git commit -m "$(cat <<'EOF'
feat: add webcam capture, sfx player, and frame output

EOF
)"
```

---

### Task 7: Main loop wiring

**Files:**
- Create: `src/instant_transmission/main.py`
- Modify: `README.md` with run instructions (full polish in Task 8)

**Interfaces:**
- Consumes: all modules above + `AppConfig`
- Produces: `main() -> None` entrypoint; `run(config: AppConfig) -> int`

Loop logic:

1. Open capture + output + gesture + sfx + calibrator + controller  
2. Clock with `time.perf_counter()`  
3. While True:
   - `frame = capture.read()` (mirror with `cv2.flip(frame, 1)` for natural UX)
   - If calibrating: `cal.update`; overlay progress text “Step out of frame…”; on done `controller.finish_calibration()`
   - Else if state VISIBLE or VANISHED: `if gesture.process(frame):` and `controller.on_gesture(now)` → `sfx.play()`
   - Build `display`:
     - CALIBRATING / VISIBLE: live frame
     - VANISHED: background
     - TELEPORTING_*: `compose_teleport(...)` (mask optional: try MediaPipe SelfieSegmentation inside effects helper or gesture module; if unavailable pass `None`)
   - `controller.update(now, dt)`
   - `output.send(display)`
   - Quit on `q` / Esc (`cv2.waitKey(1)`)
4. `finally`: close all resources

- [ ] **Step 1: Implement `main.py` as above** (manual integration; no flaky camera unit test)

Include:

```python
def main() -> None:
    raise SystemExit(run(parse_args()))
```

- [ ] **Step 2: Smoke-check CLI help**

Run: `shunkan-ido --help`  (or `python -m instant_transmission.main --help`)  
Expected: usage text listing `--virtual-camera`, `--sfx`, `--no-sfx`, etc.

- [ ] **Step 3: Run full unit suite**

Run: `pytest -v`  
Expected: all unit tests PASS

- [ ] **Step 4: Manual preview run (developer machine with webcam)**

Run: `shunkan-ido`  
Expected: window opens; after calibration, Instant Transmission vanishes/reappears.

- [ ] **Step 5: Commit**

```bash
git add src/instant_transmission/main.py
git commit -m "$(cat <<'EOF'
feat: wire Instant Transmission main loop

EOF
)"
```

---

### Task 8: README + platform virtual-camera docs + final polish

**Files:**
- Modify: `README.md`
- Create: `assets/README.md` (SFX drop-in instructions)

**Content requirements:**

- What it does (1 short paragraph)
- Install: Python 3.11+, `pip install -e .`
- Place SFX at `assets/instant_transmission.mp3` (user-supplied; not redistributed)
- Usage examples:
  - `shunkan-ido`
  - `shunkan-ido --virtual-camera`
  - `shunkan-ido --no-sfx`
- Virtual camera setup:
  - Windows/macOS: install OBS → Start Virtual Camera once → use OBS Virtual Camera in meeting apps
  - Linux: install/load `v4l2loopback`, note device path if needed via `--virtual-backend`
- Meeting apps: select virtual camera in Zoom / Teams / Meet
- Privacy: local-only processing
- Disclaimer: personal/demo use; don’t misuse for deceptive attendance

- [ ] **Step 1: Write README + assets/README.md**

- [ ] **Step 2: Run full test suite once more**

Run: `pytest -v`

- [ ] **Step 3: Commit**

```bash
git add README.md assets/README.md
git commit -m "$(cat <<'EOF'
docs: add setup, sfx, and virtual camera instructions

EOF
)"
```

- [ ] **Step 4: Push to Pushkar1510/shunkan-ido** (after `gh auth login` as Pushkar1510)

```bash
git push -u origin main
```

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Immediate Instant Transmission trigger | 4, 7 |
| No countdown; cooldown after effect | 2, 7 |
| Empty-room calibration | 3, 7 |
| Speed-lines + vanish/reappear | 5, 7 |
| SFX from local asset; missing OK | 6, 8 |
| Preview always | 6, 7 |
| Optional virtual camera | 6, 7, 8 |
| Linux / Windows / macOS docs | 8 |
| No bundled copyrighted audio | 1, 8 + gitignore |
| CLI flags | 1, 7 |
| Error handling (cam / vcam / sfx) | 6, 7 |
| Unit tests for gesture/state | 2, 4 |

## Self-review notes

- Audio library locked to **pygame** (matches design).
- Package path matches design: `src/instant_transmission/`.
- Segmentation is best-effort (`mask=None` fallback) per design §7.
- No TBD placeholders left in tasks.
