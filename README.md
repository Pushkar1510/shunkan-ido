# shunkan-ido

**Instant Transmission** for your webcam: strike the pose (index and middle fingers together at your forehead) to vanish with speed lines and optional sound, then strike it again to reappear. A local preview window always opens; you can optionally mirror the effect into a virtual camera for Zoom, Microsoft Teams, or Google Meet.

Design notes: [`docs/superpowers/specs/2026-10-30-instant-transmission-cam-design.md`](docs/superpowers/specs/2026-10-30-instant-transmission-cam-design.md).

## Requirements

- Python **3.11+**
- A webcam
- Optional: sound file and virtual-camera software (see below)

## Install

From the project root, with a virtual environment activated:

```bash
pip install -e .
```

This installs the `shunkan-ido` console command and dependencies (OpenCV, MediaPipe, pygame, pyvirtualcam, etc.).

## Sound effects (optional)

The app looks for **`assets/instant_transmission.mp3`** by default. That file is **not** included in the repo (copyright). Supply your own short MP3 and place it at that path, or pass `--sfx /path/to/your.mp3`. Use `--no-sfx` to run silently.

If the file is missing, the app logs a warning once and continues with preview (and virtual camera, if enabled).

See [`assets/README.md`](assets/README.md) for drop-in instructions.

## Usage

**Preview only** (default):

```bash
shunkan-ido
```

**Preview + virtual camera** (for meeting apps):

```bash
shunkan-ido --virtual-camera
```

**No sound:**

```bash
shunkan-ido --no-sfx
```

Development equivalent without installing the entry point:

```bash
python -m instant_transmission.main
python -m instant_transmission.main --help
```

### In the app

1. On startup, **step out of the frame** until calibration finishes (empty-room background).
2. While **visible**, use the Instant Transmission pose to **vanish**; while **vanished**, use the same pose to **reappear**. There is a short cooldown between triggers.
3. Press **`q`**, **`Q`**, or **Esc** to quit. **Ctrl+C** also stops the app when the terminal receives the signal.

### Useful flags

| Flag | Purpose |
|------|---------|
| `--camera N` | Webcam index (default `0`) |
| `--width`, `--height`, `--fps` | Capture size and rate |
| `--virtual-camera` | Also send frames to a virtual camera |
| `--virtual-backend NAME` | Force backend (`obs`, `v4l2loopback`, etc.) |
| `--sfx PATH` | Custom sound file |
| `--no-sfx` | Disable sound |
| `--calibration-seconds` | Empty-room calibration duration |

Missing camera, missing SFX, or an unavailable virtual camera **does not** stop the preview when the rest of the pipeline can still run.

## Virtual camera setup

Meeting apps need a **virtual camera device** that shows the same frames as the preview. Setup depends on your OS.

### Windows and macOS (OBS Virtual Camera)

1. Install [OBS Studio](https://obsproject.com/).
2. Open OBS and click **Start Virtual Camera** at least once (OBS can stay in the background afterward).
3. Run `shunkan-ido --virtual-camera`.
4. In Zoom, Teams, or Meet, choose **OBS Virtual Camera** as your camera.

On Windows you may also use the `unitycapture` backend via `--virtual-backend unitycapture` if you use Unity Capture instead of OBS.

### Linux (v4l2loopback)

`pyvirtualcam` uses a **v4l2loopback** kernel module to create a `/dev/video*` device.

Example on Debian/Ubuntu:

```bash
sudo apt install v4l2loopback-dkms
sudo modprobe v4l2loopback devices=1
```

Then run:

```bash
shunkan-ido --virtual-camera
```

If you have several video devices, pick the loopback device explicitly:

```bash
shunkan-ido --virtual-camera --virtual-backend v4l2loopback
```

List devices with `v4l-ctl --list-devices` or `ls /dev/video*`. In your meeting app, select the **Video Loopback** (or similarly named) camera.

See the [v4l2loopback documentation](https://github.com/umlaeute/v4l2loopback) for persistence across reboots and permissions.

### Using the virtual camera in meetings

In **Zoom**, **Microsoft Teams**, or **Google Meet**, open camera settings and select:

- **OBS Virtual Camera** (Windows/macOS), or  
- Your **v4l2loopback** device (Linux).

Start `shunkan-ido --virtual-camera` **before** or during the call so the device is active when the app selects it.

## Privacy

All processing runs **locally** on your machine: webcam frames, pose detection, effects, and preview. Nothing is uploaded to a cloud service by this app.

## Disclaimer

This project is for **personal and demo use** (streams, jokes, tech demos). Do **not** use it to misrepresent attendance, impersonate others, or deceive employers, educators, or meeting participants. You are responsible for how you use it and for complying with the terms of your meeting platform and local laws.

## Tests

```bash
pytest -v
```
