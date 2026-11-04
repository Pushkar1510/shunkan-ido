# Phoenix Snap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect a vision-only finger snap and show a procedural glowing fireball orb on the palm for ~1–1.5s, while Instant Transmission keeps working.

**Architecture:** Extend `GestureDetector.process` to return IT boolean plus hand samples in one MediaPipe pass. `SnapDetector` consumes multi-frame tip distances; `phoenix_fx.draw_orbs` composites procedural glows. Main loop applies snap only when `VISIBLE` and IT did not fire.

**Tech Stack:** Existing Python 3.11+, OpenCV, MediaPipe, NumPy, pygame (optional SFX), pytest

## Global Constraints

- Branch: `feature/phoenix-snap`
- Spec: `docs/superpowers/specs/2026-11-04-phoenix-snap-design.md`
- Vision-only snap (no mic)
- Both Phoenix and Instant Transmission always available; IT forehead pose wins on that frame
- Orb only while `AppState.VISIBLE`
- Procedural VFX (no Valorant assets); optional local `assets/phoenix_snap.mp3` gitignored
- Single MediaPipe pass per frame
- `--no-phoenix` disables the feature
- Author Pushkar1510; commit locally; push only if asked

## File Structure

| Path | Responsibility |
|------|----------------|
| `src/instant_transmission/gesture.py` | Add `HandSample`, richer `process` / `FrameGestureResult` |
| `src/instant_transmission/snap_gesture.py` | `SnapDetector`, `SnapEvent` |
| `src/instant_transmission/phoenix_fx.py` | `PhoenixOrb`, `draw_orbs` |
| `src/instant_transmission/config.py` | `phoenix_enabled`, `phoenix_sfx_path` |
| `src/instant_transmission/main.py` | Wire snap + orbs |
| `tests/test_snap_gesture.py` | Snap sequences |
| `tests/test_phoenix_fx.py` | Orb drawing |
| `tests/test_gesture.py` | Keep IT tests; adapt to new return type if needed |
| `tests/test_config.py` | New flags |
| `README.md` | Short Phoenix note |

---

### Task 1: Expose hand samples from GestureDetector

**Files:**
- Modify: `src/instant_transmission/gesture.py`
- Modify: `src/instant_transmission/main.py` (call site for new return type)
- Modify: `tests/test_gesture.py` if needed
- Create: `tests/test_gesture_result.py` (optional small test for HandSample packing)

**Interfaces:**
- Produces:
```python
@dataclass(frozen=True)
class HandSample:
    hand_id: int
    landmarks: Sequence  # landmark list with .x .y
    width: int
    height: int

    def tip_distance_thumb_middle(self) -> float: ...  # normalized 0..hypot(1,1) style or baseline px
    def palm_xy(self) -> tuple[float, float]: ...  # pixel coords; use landmark 0 (wrist) or average of wrist+index_mcp+pinky_mcp

@dataclass(frozen=True)
class FrameGestureResult:
    instant_transmission: bool
    hands: tuple[HandSample, ...]

# GestureDetector.process(frame_bgr) -> FrameGestureResult
```

- [ ] **Step 1:** Add failing test that `FrameGestureResult` / packing helpers work on synthetic landmarks (or update main temporarily).

- [ ] **Step 2:** Change `process` to return `FrameGestureResult`. Keep `is_instant_transmission` logic. Store hands from `hand_result.hand_landmarks` with indices as `hand_id`.

- [ ] **Step 3:** Update `main.py` `_loop` to use `result = gesture.process(frame); result.instant_transmission`.

- [ ] **Step 4:** `pytest -v` green; commit:
```bash
git commit -m "$(cat <<'EOF'
feat: return hand samples from gesture detector

EOF
)"
```

---

### Task 2: SnapDetector (TDD)

**Files:**
- Create: `src/instant_transmission/snap_gesture.py`
- Create: `tests/test_snap_gesture.py`

**Interfaces:**
```python
@dataclass(frozen=True)
class SnapEvent:
    palm_xy: tuple[float, float]
    hand_id: int

class SnapDetector:
    def __init__(self, *, cooldown_seconds: float = 0.5,
                 pinch_threshold: float = 0.05,  # normalized tip distance
                 release_threshold: float = 0.10,
                 max_snap_window_s: float = 0.15) -> None: ...
    def update(self, hands: Sequence[HandSample], now: float) -> list[SnapEvent]: ...
```

Detection: per `hand_id`, track tip distance; when distance goes below `pinch_threshold` mark pinched; if within `max_snap_window_s` distance rises above `release_threshold`, emit `SnapEvent` and start global cooldown.

- [ ] **Step 1:** Write tests: close→open emits one event; slow pinch no event; cooldown suppresses second snap; empty hands → [].

- [ ] **Step 2:** Implement `SnapDetector`.

- [ ] **Step 3:** `pytest tests/test_snap_gesture.py -v` pass; commit:
```bash
git commit -m "$(cat <<'EOF'
feat: detect finger snap from hand landmarks

EOF
)"
```

---

### Task 3: Procedural phoenix orb VFX (TDD)

**Files:**
- Create: `src/instant_transmission/phoenix_fx.py`
- Create: `tests/test_phoenix_fx.py`

**Interfaces:**
```python
@dataclass
class PhoenixOrb:
    x: float
    y: float
    born_at: float
    duration: float = 1.25

def draw_orbs(frame_bgr: np.ndarray, orbs: list[PhoenixOrb], now: float) -> np.ndarray:
    """Return frame with active orbs; remove expired from list in-place or return survivors."""
```

Render: soft radial glow (BGR warm colors), noise/sine flicker, ease-in/out envelope. Use OpenCV circles + additive blend on a float buffer.

- [ ] **Step 1:** Tests: shape/dtype preserved; at `now = born_at + duration` orb gone; mid-life pixels change vs input.

- [ ] **Step 2:** Implement `draw_orbs`.

- [ ] **Step 3:** pytest pass; commit:
```bash
git commit -m "$(cat <<'EOF'
feat: add procedural Phoenix palm orb VFX

EOF
)"
```

---

### Task 4: Config flags + main wiring

**Files:**
- Modify: `src/instant_transmission/config.py`
- Modify: `tests/test_config.py`
- Modify: `src/instant_transmission/main.py`
- Modify: `src/instant_transmission/audio.py` usage (second `SfxPlayer` or path switch — prefer separate `phoenix_sfx: SfxPlayer`)

**Behavior in `_loop` when `phoenix_enabled`:**
1. `result = gesture.process(frame)`
2. If VISIBLE or VANISHED and `result.instant_transmission` and `on_gesture` → IT sfx (unchanged).
3. Elif VISIBLE and not `result.instant_transmission`: `events = snap.update(result.hands, now)`; for each event append `PhoenixOrb` and play phoenix sfx.
4. After `_display_frame`, if VISIBLE: `display = draw_orbs(display, orbs, now)`.

- [ ] **Step 1:** Config tests for `--no-phoenix` and `--phoenix-sfx`.

- [ ] **Step 2:** Wire main; prune expired orbs each frame.

- [ ] **Step 3:** Full `pytest -v`; commit:
```bash
git commit -m "$(cat <<'EOF'
feat: wire Phoenix snap into preview loop

EOF
)"
```

---

### Task 5: README + synthetic local SFX helper note

**Files:**
- Modify: `README.md`
- Modify: `assets/README.md` (mention `phoenix_snap.mp3`)
- Optionally generate local `assets/phoenix_snap.mp3` (gitignored) like IT whoosh

- [ ] **Step 1:** Document snap pose, orb, `--no-phoenix`, coexistence with IT.

- [ ] **Step 2:** Generate a short synthetic local snap SFX if easy (same approach as IT).

- [ ] **Step 3:** pytest; commit docs:
```bash
git commit -m "$(cat <<'EOF'
docs: document Phoenix snap feature

EOF
)"
```

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| Vision snap | 2 |
| Procedural palm orb | 3 |
| IT priority / VISIBLE only | 4 |
| Single MediaPipe pass | 1 |
| `--no-phoenix` / SFX | 4, 5 |
| No Valorant assets | 3, 5 |
