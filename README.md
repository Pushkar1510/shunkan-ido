# shunkan-ido

**Instant Transmission** for your webcam: strike the pose (index and middle fingers together at your forehead) to vanish with speed lines and optional sound, then strike it again to reappear. A local preview window always opens; you can mirror the effect into a virtual camera for Zoom, Microsoft Teams, or Google Meet.

**Supported platforms for meeting virtual camera:** **Ubuntu** and **Windows**. macOS is not supported.

Design notes:

- Original cam design: [`docs/superpowers/specs/2026-10-30-instant-transmission-cam-design.md`](docs/superpowers/specs/2026-10-30-instant-transmission-cam-design.md)
- Ubuntu/Windows virtual cam: [`docs/superpowers/specs/2026-11-03-ubuntu-windows-virtual-cam-design.md`](docs/superpowers/specs/2026-11-03-ubuntu-windows-virtual-cam-design.md)

## Requirements

- Python **3.11+**
- A webcam
- Ubuntu: `v4l2loopback` (installed by our setup script)
- Windows: OBS Studio once (installed by our setup script via winget — not bundled)

## Install

From the project root, with a virtual environment activated:

```bash
pip install -e .
```

This installs the `shunkan-ido` console command and dependencies (OpenCV, MediaPipe, pygame, pyvirtualcam, etc.).

## Sound effects (optional)

The app looks for **`assets/instant_transmission.mp3`** by default. That file is **not** included in the repo (copyright). Supply your own short MP3 and place it at that path, or pass `--sfx /path/to/your.mp3`. Use `--no-sfx` to run silently.

See [`assets/README.md`](assets/README.md) for drop-in instructions.

## Usage

**Preview only** (default):

```bash
shunkan-ido
```

**Preview + virtual camera** (Meet / Zoom / Teams):

```bash
# One-time OS setup (see packaging/):
#   Ubuntu:  bash packaging/ubuntu/setup-virtual-camera.sh
#   Windows: powershell -File packaging/windows/setup-virtual-camera.ps1

shunkan-ido --setup-virtual-camera   # verify / prime
shunkan-ido --virtual-camera         # daily use
```

**No sound:**

```bash
shunkan-ido --no-sfx
```

Development equivalent:

```bash
python -m instant_transmission.main
python -m instant_transmission.main --help
```

### In the app

1. On startup, the preview waits. **Step out of the frame**, then press **Space** or **Enter** to start empty-room calibration.
2. While **visible**, use the Instant Transmission pose to **vanish**; while **vanished**, use the same pose to **reappear**.
3. Press **`q`**, **`Q`**, or **Esc** to quit. **Ctrl+C** also stops the app.

### Useful flags

| Flag | Purpose |
|------|---------|
| `--camera N` | Webcam index (default `0`) |
| `--width`, `--height`, `--fps` | Capture size and rate |
| `--virtual-camera` | Also send frames to a virtual camera |
| `--setup-virtual-camera` | One-time virtual camera setup / verify, then exit |
| `--virtual-backend NAME` | Force backend (`v4l2loopback`, `obs`, `unitycapture`, …) |
| `--sfx PATH` | Custom sound file |
| `--no-sfx` | Disable sound |
| `--calibration-seconds` | Empty-room calibration duration |

Missing SFX or an unavailable virtual camera **does not** stop the preview.

## Virtual camera setup

### Ubuntu (recommended path — no OBS)

See [`packaging/ubuntu/README.md`](packaging/ubuntu/README.md).

```bash
bash packaging/ubuntu/setup-virtual-camera.sh
shunkan-ido --setup-virtual-camera
shunkan-ido --virtual-camera
```

In Meet/Zoom/Teams choose **Shunkan-Ido**.

### Windows

See [`packaging/windows/README.md`](packaging/windows/README.md).

OBS Virtual Camera is the provider (`pyvirtualcam` `obs` backend). OBS is installed **separately** (winget) because it is GPL — we do not ship OBS inside this package.

```powershell
powershell -ExecutionPolicy Bypass -File packaging/windows/setup-virtual-camera.ps1
shunkan-ido --setup-virtual-camera
shunkan-ido --virtual-camera
```

In Meet/Zoom/Teams choose **OBS Virtual Camera**.

Optional: `--virtual-backend unitycapture` if you already use Unity Capture.

### macOS

Not supported.

## Privacy

All processing runs **locally** on your machine. Nothing is uploaded by this app.

## Disclaimer

This project is for **personal and demo use**. Do **not** use it to misrepresent attendance or deceive meeting participants. You are responsible for complying with your meeting platform and local laws.

## Tests

```bash
pytest -v
```
