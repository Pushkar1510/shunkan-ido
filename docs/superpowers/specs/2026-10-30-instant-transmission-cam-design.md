# Instant Transmission Cam — Design Spec

**Date:** 2026-10-30  
**Status:** Ready for user review  
**Inspired by:** VanishCam / @nicosmartworking “leave meetings” demo (Goku Instant Transmission)

## 1. Summary

A local desktop Python app that lets you vanish from and reappear in video meetings by performing Goku’s Instant Transmission pose (index + middle finger to the forehead). The processed feed is shown in a preview window and can optionally be sent to a virtual camera so Zoom, Microsoft Teams, Google Meet, and other apps see the effect.

## 2. Goals

- Instant Transmission gesture triggers teleport **immediately** (no hold countdown).
- Comic speed-lines on the silhouette, then swap to an empty-room background (vanish); reverse on reappear.
- Play a short Instant Transmission **sound effect** from a local asset file.
- Preview always available; virtual camera optional for real meetings.
- Work on **Linux, Windows, and macOS**.
- Process video locally; do not upload frames to the cloud.

## 3. Non-Goals (v1)

- Other vanish modes (Naruto, particles, V-sign-only, etc.).
- iOS / Android native apps.
- Automatically clicking “Leave meeting” in Zoom/Teams/Meet.
- Shipping copyrighted Dragon Ball Z audio in the repository.
- Cloud inference or accounts.

## 4. User experience

### 4.1 Happy path

1. User starts the app (CLI).
2. Preview window opens.
3. App asks the user to leave the frame for a few seconds and captures the **empty room** background.
4. User returns; live feed is shown (and optionally pushed to the virtual camera).
5. User performs Instant Transmission → **immediately**:
   - speed-lines on silhouette
   - SFX plays
   - crossfade / teleport into empty background (vanished)
6. Same gesture again → reverse animation + SFX → user reappears.
7. User quits with `Q`, Esc, or Ctrl+C.

### 4.2 Meeting apps

User selects the virtual camera device in Zoom / Teams / Meet / Discord / etc. Those apps need no plugins; they only consume a camera device.

| Platform | Typical virtual camera |
|----------|------------------------|
| Windows / macOS | OBS Virtual Camera (via `pyvirtualcam`) |
| Linux | `v4l2loopback` device (via `pyvirtualcam`) |

### 4.3 Sound

- App plays `assets/instant_transmission.mp3` (path configurable).
- The authentic DBZ Instant Transmission SFX is **not** bundled (copyright).
- User places their own allowed SFX file at that path.
- If the file is missing: warn once; visuals still work.

## 5. Architecture

```
Webcam
  → Capture (OpenCV)
  → Gesture detect (MediaPipe Hands + Face)
  → Effect engine (state machine)
  → Preview window (always)
  → Optional virtual camera (pyvirtualcam)
```

### 5.1 Components

| Module | Responsibility |
|--------|----------------|
| `capture` | Open webcam; read BGR frames at target resolution/FPS |
| `gesture` | Detect Instant Transmission; emit trigger on first valid frame |
| `background` | Capture and store empty-room frame(s) during calibration |
| `effects` | Speed-lines + vanish/reappear transition compositing |
| `audio` | Play SFX on teleport start (non-blocking) |
| `output` | Preview (`cv2.imshow`) + optional `pyvirtualcam` send |
| `main` | CLI, main loop, wiring, graceful shutdown |

### 5.2 State machine

```
CALIBRATING → VISIBLE → TELEPORTING_OUT → VANISHED → TELEPORTING_IN → VISIBLE → …
```

- `CALIBRATING`: accumulate empty background; no gesture handling.
- `VISIBLE`: live person; listen for Instant Transmission.
- `TELEPORTING_OUT` / `TELEPORTING_IN`: play animation to completion even if gesture is lost.
- `VANISHED`: show empty background; listen for Instant Transmission to return.
- After an animation completes: short **cooldown** so one continuous pose does not double-fire.

## 6. Gesture rules

**Pose:** Index and middle fingers extended and together; ring and pinky folded; fingertips near the forehead (face landmarks).

**Trigger policy:** Fire on the first frame that matches (no countdown). Apply cooldown after effect completion.

**Implementation approach:** MediaPipe Hands + Face Mesh (or Face Landmarker) landmark geometry — distances and angles between finger tips and forehead landmarks. Prefer deterministic geometry over a custom trained classifier for v1.

## 7. Effects

1. Person/silhouette mask via MediaPipe selfie segmentation so speed-lines stick to the body. If segmentation fails on a frame, fall back to full-frame speed-lines (effect still runs).
2. Comic-style vertical speed-lines over the silhouette for a short duration (~0.3–0.6s).
3. Crossfade / dissolve between live frame and empty background (or reverse).
4. Total teleport visual roughly ~0.5–1.0s (tunable constants).

## 8. CLI / configuration

Suggested flags:

| Flag | Meaning |
|------|---------|
| `--camera N` | Webcam index (default `0`) |
| `--width` / `--height` / `--fps` | Capture preferences |
| `--virtual-camera` | Enable virtual camera output |
| `--virtual-backend` | Optional backend (`obs`, `v4l2loopback`, etc.) |
| `--sfx PATH` | Path to Instant Transmission SFX |
| `--no-sfx` | Disable sound |
| `--calibration-seconds N` | Empty-room capture duration (default ~4) |

## 9. Project layout (proposed)

```
DBZ/
  README.md
  requirements.txt
  pyproject.toml          # optional
  assets/
    instant_transmission.mp3   # user-supplied; not committed if copyrighted
    .gitkeep
  src/instant_transmission/
    __init__.py
    main.py
    capture.py
    gesture.py
    background.py
    effects.py
    audio.py
    output.py
    config.py
  docs/superpowers/specs/
    2026-10-30-instant-transmission-cam-design.md
```

## 10. Dependencies (v1)

- Python 3.11+
- `opencv-python`
- `mediapipe`
- `numpy`
- `pyvirtualcam` (optional at runtime if `--virtual-camera`)
- `pygame` for non-blocking SFX playback (cross-platform; swap later only if it proves unreliable)

Platform prerequisites for meetings:

- Windows/macOS: OBS Studio (Virtual Camera)
- Linux: `v4l2loopback` module + device permissions

## 11. Error handling

| Situation | Behavior |
|-----------|----------|
| Webcam unavailable | Clear error; exit non-zero |
| Virtual camera unavailable | Warn; continue with preview only |
| SFX missing | Warn once; continue silent |
| Gesture lost mid-animation | Finish current teleport animation |
| Ctrl+C / Esc / `Q` | Release camera, close windows, exit cleanly |

## 12. Privacy & safety

- All processing is local.
- No frame upload.
- README states: for personal / demo use; do not use to deceive in contexts where presence matters (work authenticity, exams, etc.).

## 13. Testing plan

**Manual**

1. Calibration captures stable empty background.
2. Instant Transmission vanishes immediately with speed-lines + SFX (if present).
3. Second gesture restores with reverse effect.
4. Cooldown prevents double-trigger while holding the pose.
5. Preview-only mode works without virtual camera installed.
6. With virtual camera: device appears in Zoom / Meet / Teams picker; effect visible to a second account or phone recording.

**Automated (lightweight)**

- Unit tests for gesture geometry helpers with synthetic landmarks.
- Unit tests for state transitions (VISIBLE → TELEPORTING_OUT → VANISHED → …).
- Smoke test that CLI `--help` works.

## 14. Implementation phases

1. Scaffold project + capture + preview loop.
2. Background calibration.
3. Gesture detection + state machine (hard cut vanish first).
4. Speed-lines + crossfade polish.
5. SFX playback + asset path docs.
6. Optional virtual camera output + platform README notes.
7. Manual verification on available OS; document Win/Mac/Linux setup.

## 15. Success criteria

- On a supported desktop OS, user can vanish and reappear via Instant Transmission in the preview within one run.
- With virtual camera set up, the same feed is selectable in at least one of Zoom / Meet / Teams.
- Missing SFX or virtual camera does not crash the app.
- No copyrighted DBZ audio is committed to the repo.
