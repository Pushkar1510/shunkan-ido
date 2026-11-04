# Phoenix Snap — Design Spec

**Date:** 2026-11-04  
**Status:** Ready for user review  
**Branch:** `feature/phoenix-snap`  
**Parent:** Instant Transmission cam (`shunkan-ido`)

## 1. Summary

Add a Valorant Phoenix–inspired **finger snap** effect: when the user snaps (vision-only), a procedural glowing fireball-style orb appears at that hand’s palm, flickers briefly, then fades. Instant Transmission continues to work as today. No throw / flash / full-screen blind in v1.

## 2. Goals

- Detect a finger snap from MediaPipe hand landmarks (no microphone).
- Spawn a procedural warm energy orb at the palm for ~1.0–1.5s.
- Coexist with Instant Transmission: both always available.
- Work in the same preview + optional virtual-camera frame pipeline.
- Optional local snap SFX (user-supplied or synthetic; not copyrighted game audio).

## 3. Non-Goals (v1)

- Throwing the orb across the frame.
- Flashing / whitening the whole meeting video (Curveball “blind”).
- Mic-based snap detection.
- Shipping Valorant / Riot copyrighted audio or art.
- Separate Phoenix-only mode flag (both abilities always on).

## 4. User experience

1. App runs as today (calibrate with Space, Instant Transmission works).
2. User snaps fingers in view of the webcam (not in Instant Transmission pose).
3. A glowing orange/red/yellow orb appears on that palm, pulses with subtle noise, then fades out (~1–1.5s).
4. User can snap again after a short cooldown.
5. Forehead Instant Transmission pose still vanishes/reappears as before.

## 5. Gesture rules

### 5.1 Snap (vision)

- Track thumb tip vs middle tip (fallback: ring tip) distance in normalized image space.
- **Close phase:** tips approach within a pinch threshold.
- **Open phase:** tips separate past a release threshold within a short window (~80–150ms after the close).
- Emit one snap event on the completed open, with palm position = hand palm landmark (MediaPipe index 0 / wrist–palm midpoint as implemented).
- Per-hand tracking so left/right snaps are independent.
- Cooldown ~0.4–0.6s after a successful snap (per hand or global — **global** for v1 simplicity).

### 5.2 Priority vs Instant Transmission

- If the current frame matches Instant Transmission (existing detector) → **teleport wins**; do not start a snap orb from that frame.
- Else evaluate snap gesture history.
- Orb drawing runs only when app state is `VISIBLE` (not during `CALIBRATING`, teleport animations, or `VANISHED`).

## 6. Architecture

```
Webcam frame
  → existing capture / calibrate / IT gesture / teleport compose
  → (if VISIBLE) snap detector update(hand landmarks)
  → if snap fired: start PhoenixOrb at palm
  → draw procedural orbs onto display frame
  → preview / virtual camera
```

### 6.1 New modules

| Module | Responsibility |
|--------|----------------|
| `snap_gesture.py` | Multi-frame snap detector from hand landmarks |
| `phoenix_fx.py` | Procedural orb render (radial glow + noise flicker) |
| Optional: extend `gesture.py` | Expose raw hand landmarks / palm points to callers without double MediaPipe runs |

### 6.2 Interfaces (proposed)

```python
# snap_gesture.py
class SnapDetector:
    def update(self, hands: list[HandSample], now: float) -> list[SnapEvent]:
        """Return zero or more snap events this frame."""

@dataclass(frozen=True)
class SnapEvent:
    palm_xy: tuple[float, float]  # pixel coords in current frame
    hand_id: int

# phoenix_fx.py
@dataclass
class PhoenixOrb:
    x: float
    y: float
    born_at: float
    duration: float = 1.25

def draw_orbs(frame_bgr: np.ndarray, orbs: list[PhoenixOrb], now: float) -> np.ndarray:
    """Composite active orbs; drop expired."""
```

`GestureDetector` should expose landmarks used for snap (e.g. `process` returns a richer result, or a parallel `last_hands` property) so MediaPipe still runs **once** per frame.

### 6.3 Procedural VFX

- Soft radial gradient at palm (warm colors: deep red → orange → yellow core).
- Time-based noise / sine modulation for flicker.
- Scale envelope: ease-in (~15% of duration) → hold → fade-out.
- Additive-style blend (or screen blend via OpenCV) so it reads as energy, not a sticker.
- Tunable constants: radius, duration, colors at top of `phoenix_fx.py`.

## 7. Audio (optional)

- Default path: `assets/phoenix_snap.mp3` (gitignored like other SFX).
- Missing file → warn once, visuals still work (same pattern as Instant Transmission SFX).
- Do not bundle Riot/Valorant audio.

## 8. CLI / config

| Flag / field | Meaning |
|--------------|---------|
| `--no-phoenix` | Disable snap orb feature |
| `--phoenix-sfx PATH` | Optional snap sound |
| (defaults) | Phoenix enabled when not `--no-phoenix` |

Keep existing IT flags unchanged.

## 9. Error handling

| Situation | Behavior |
|-----------|----------|
| No hands | No snap; no orb |
| Snap during IT pose | Ignored |
| Snap while vanished / calibrating / teleporting | Ignored |
| Missing phoenix SFX | Warn once; continue |
| Multiple hands snap same frame | Spawn orb for each valid event (still respect global cooldown if set) |

## 10. Testing

**Unit**

- Snap detector: synthetic landmark sequences for close→open → one event; no event on slow pinch; cooldown suppresses doubles.
- `draw_orbs`: shape preserved; expired orbs not drawn; intensity at t=0 and t=duration endpoints.

**Manual**

- Snap produces palm orb in preview.
- Instant Transmission still works; snapping during forehead pose does not fire orb.
- Virtual camera shows the orb when `--virtual-camera` is on.
- `--no-phoenix` disables the feature.

## 11. Implementation phases

1. Expose hand landmarks from gesture pipeline (single MediaPipe pass).
2. `SnapDetector` + unit tests.
3. `phoenix_fx.draw_orbs` + unit tests.
4. Wire into `main` (VISIBLE only; IT priority).
5. Optional SFX + CLI flags + README note.
6. Manual Meet/preview check on `feature/phoenix-snap`.

## 12. Success criteria

- Snapping in view creates a visible procedural palm orb that fades within ~1.5s.
- Instant Transmission behavior unchanged when snapping is not happening.
- Forehead pose does not falsely trigger a snap orb.
- Feature can be disabled with `--no-phoenix`.
- No copyrighted Valorant assets in the repo.
