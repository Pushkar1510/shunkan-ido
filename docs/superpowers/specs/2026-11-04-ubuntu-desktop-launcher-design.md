# Ubuntu Desktop Launcher + `.deb` — Design Spec

**Date:** 2026-11-04  
**Status:** Ready for user review  
**Branch (proposed):** `feature/ubuntu-desktop-launcher` (from Instant Transmission / virtual-cam line)  
**Platforms:** Ubuntu first; Windows deferred  

## 1. Summary

Ship **Shunkan-Ido** as an Ubuntu `.deb` with a polished **PySide6** launcher: full-bleed background (user-supplied art), brand title, virtual-camera status, and two buttons — **Setup virtual camera** and **Start calibrating**. Start launches the existing Instant Transmission pipeline with virtual camera enabled. Friends install via `.deb` and use the app menu; CLI remains available for developers.

## 2. Goals

- One-click-ish Ubuntu install via `.deb` + desktop entry.
- Good launcher UI (not a bare dialog): hero brand, readable overlay, primary/secondary CTAs, light motion.
- Two-button flow: Setup (once) → Start calibrating (daily).
- Reuse existing Instant Transmission core (`run` / capture / gesture / effects / virtual cam).
- Brand art in `assets/`: `Shunkan_ido_bg.jpg`, `shunkan_ido_logo.png`, `shunkan_ido_icon.png` (distributor/legal owns rights); code falls back if a file is missing.
- Keep `shunkan-ido` CLI working.

## 3. Non-Goals (this phase)

- Windows installer / `.exe` (next phase).
- Phoenix snap UI.
- Flatpak / AppImage (`.deb` only for v1).
- Bundling copyrighted Dragon Ball assets in the public git repo.
- Rewriting the OpenCV preview into Qt (preview stays OpenCV window for v1).

## 4. User experience

### 4.1 Install

1. Download `shunkan-ido_<version>_amd64.deb`.
2. Install with Ubuntu Software or `sudo apt install ./shunkan-ido_*.deb`.
3. Launch **Shunkan-Ido** from the app grid.

### 4.2 Launcher

- Window: fixed or min size suitable for laptop (~960×600 or similar), full-bleed background.
- Overlay: dark translucent panel so type and buttons stay legible on any image.
- Hero: **SHUNKAN-IDO** (dominant), one short tagline (e.g. Instant Transmission for your meetings).
- Status chip: **Ready** / **Needs setup** / **Running** / error snippet.
- Buttons:
  - **Setup virtual camera** (secondary) — runs Ubuntu v4l2loopback setup (pkexec/sudo as needed), then refreshes status.
  - **Start calibrating** (primary, larger) — starts Instant Transmission with `virtual_camera=True`.
- Motion: fade-in on open; hover/press on primary; subtle status pulse when Running.
- While running: primary becomes **Stop** (or a Stop control appears); Stop ends the cam loop and frees the webcam.

### 4.3 After Start

Same process as today:

1. Preview opens; user steps out; presses Space/Enter to calibrate (existing waiting state).
2. Instant Transmission pose vanishes/reappears.
3. Meet/Zoom selects **Shunkan-Ido** virtual camera.

### 4.4 Background art

- Preferred path: `assets/launcher_bg.png` (or packaged data dir equivalent).
- **Not committed** to git if copyrighted; listed in `.gitignore`.
- If missing: ship a non-character fallback (dark energy / abstract Instant Transmission vibe) so UI never looks broken.
- User/distributor is responsible for rights to any character art they ship privately.

## 5. Architecture

```
.shunkan-ido.deb
  → PySide6 launcher + Python core + packaging scripts + desktop entry

Launcher (UI thread)
  ├── Setup → pkexec/sudo + packaging/ubuntu/setup-virtual-camera.sh
  │           → virtual_cam status probe
  └── Start → worker thread/process runs Instant Transmission loop
              (AppConfig with virtual_camera=True)
              → Stop / window close → teardown
```

### 5.1 New modules

| Path | Responsibility |
|------|----------------|
| `src/instant_transmission/ui/app.py` | `QApplication` entry |
| `src/instant_transmission/ui/launcher.py` | Main window: background, brand, status, buttons, animations |
| `src/instant_transmission/ui/worker.py` | Run cam loop off UI thread; start/stop signals |
| `src/instant_transmission/ui/assets.py` | Resolve background path + fallback |
| `packaging/ubuntu/build-deb.sh` | Build `.deb` |
| `packaging/ubuntu/shunkan-ido.desktop` | App menu entry |
| Icon asset (simple non-DBZ icon) | Desktop icon |

### 5.2 Reuse

- `instant_transmission.main.run(AppConfig)`
- `virtual_cam.run_platform_setup` / readiness checks
- Existing `packaging/ubuntu/setup-virtual-camera.sh`
- CLI entry `shunkan-ido` unchanged

### 5.3 Entry points

- GUI: `shunkan-ido-gui` (or `shunkan-ido --gui`) — default for `.desktop`.
- CLI: `shunkan-ido` — existing flags.

### 5.4 Threading / lifecycle

- Never block the Qt event loop on the webcam loop.
- Worker must release camera and OpenCV windows on Stop/Quit.
- Starting twice while Running is ignored or treated as no-op.

## 6. Setup button behavior

1. Probe virtual camera (e.g. labeled Shunkan-Ido / loopback present).
2. If already Ready → status message “Already set up”; no sudo.
3. Else run setup script with elevated privileges (`pkexec` preferred, fallback instructions if unavailable).
4. Re-probe; update status chip.
5. On failure → show short actionable error (permissions, DKMS, reboot hint).

## 7. Start calibrating behavior

1. If status is Needs setup → warn in UI; optionally still allow Start for preview-only, but default is warn and prefer Setup first (virtual camera intended for friends’ Meet use).
2. Build `AppConfig(virtual_camera=True, …)` and start worker.
3. Set status Running; disable Setup or leave it inert while Running.
4. Stop → worker shutdown → status back to Ready/Needs setup.

Exact “block Start until setup” vs “warn only”: **warn + allow Start** so laptop preview still works without Meet; status remains clear.

## 8. `.deb` contents (high level)

- Package name: `shunkan-ido`
- Depends: as required for PySide6 / OpenCV / system libs (exact pins in packaging script)
- Installs under `/usr/lib/shunkan-ido/` or `/opt/shunkan-ido/` with wrappers in `/usr/bin/`
- Includes setup script path the GUI can invoke
- Does **not** require v4l2loopback preinstalled; Setup button installs/loads it
- Postinst may refresh desktop database

Build via `packaging/ubuntu/build-deb.sh` on an Ubuntu amd64 machine/CI.

## 9. Visual design notes

- CSS-like Qt stylesheets: clear Instant Transmission vibe (deep ink, warm gold/orange accent — not generic purple-on-white).
- Primary button: high contrast, large hit target.
- Secondary: quieter outline/ghost on the glass overlay.
- Typography: distinctive display font if embeddable and licensed; otherwise strong Qt font pairing with large title weight.
- First viewport = one composition: brand + tagline + status + two actions (no dashboard clutter).

## 10. Error handling

| Situation | Behavior |
|-----------|----------|
| Missing launcher background | Fallback background |
| pkexec/sudo denied | Status Needs setup + message |
| Webcam unavailable | Error in UI / log; worker exits |
| Virtual cam missing at Start | Warn; Start may continue with preview |
| Worker crash | Surface message; reset to idle |

## 11. Testing

**Automated**

- Asset resolver returns fallback when file missing.
- Launcher constructs without display if using offscreen Qt where feasible.
- Worker start/stop mocked around `run()` where practical.

**Manual (Ubuntu)**

1. Build `.deb`, install on clean-ish machine.
2. App appears in menu; launcher opens with fallback or custom bg.
3. Setup creates/labels Shunkan-Ido device.
4. Start → calibrate → Instant Transmission in preview.
5. Meet lists Shunkan-Ido; Stop frees webcam.

## 12. Implementation phases

1. PySide6 launcher shell (fallback bg, brand, two buttons, status).
2. Wire Setup → existing Ubuntu script + status probe.
3. Wire Start/Stop → worker + `run(AppConfig(virtual_camera=True))`.
4. Desktop entry + icon; `shunkan-ido-gui` entry point.
5. `build-deb.sh` + install smoke test.
6. README: friend install steps (Ubuntu).
7. (Later) Windows phase with same UI language.

## 13. Success criteria

- Friend can install `.deb` and open a polished launcher without using the terminal.
- Setup button configures virtual camera (with one password prompt when needed).
- Start calibrating runs the current Instant Transmission + virtual cam flow.
- Missing user art does not break the app.
- No copyrighted character art is required in the public repository.
- Windows remains explicitly out of scope until the next phase.
