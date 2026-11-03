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

**Preview + virtual camera** (for Zoom / Teams / Meet):

```bash
# One-time only (installs/primes OBS Virtual Camera — OBS need not stay open later):
shunkan-ido --setup-virtual-camera

# Daily use:
shunkan-ido --virtual-camera
# Mac with Continuity Camera: prefer the built-in cam, e.g. --camera 1
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

1. On startup, the preview waits. **Step out of the frame**, then press **Space** or **Enter** to start empty-room calibration.
2. While **visible**, use the Instant Transmission pose to **vanish**; while **vanished**, use the same pose to **reappear**. There is a short cooldown between triggers.
3. Press **`q`**, **`Q`**, or **Esc** to quit. **Ctrl+C** also stops the app when the terminal receives the signal.

### Useful flags

| Flag | Purpose |
|------|---------|
| `--camera N` | Webcam index (default `0`) |
| `--width`, `--height`, `--fps` | Capture size and rate |
| `--virtual-camera` | Also send frames to a virtual camera |
| `--setup-virtual-camera` | One-time OBS Virtual Camera prime, then exit |
| `--virtual-backend NAME` | Force backend (`obs`, `v4l2loopback`, etc.) |
| `--sfx PATH` | Custom sound file |
| `--no-sfx` | Disable sound |
| `--calibration-seconds` | Empty-room calibration duration |

Missing SFX or an unavailable virtual camera **does not** stop the preview. A missing or unusable webcam stops the app before any preview window opens.

## Virtual camera setup

Meeting apps need a **virtual camera device** that shows the same frames as the preview. Setup depends on your OS.

### Windows and macOS (OBS Virtual Camera)

Meeting apps need a virtual camera device. OBS provides that **once**; you do **not** need the OBS window open on every call afterward.

1. Install [OBS Studio](https://obsproject.com/) once (macOS: `brew install --cask obs`).
2. Run **one-time** setup: `shunkan-ido --setup-virtual-camera`  
   (or in OBS: **Start Virtual Camera** once, then Stop, then quit).  
   On macOS, allow the OBS **camera extension** if System Settings prompts you.
3. Daily: `shunkan-ido --virtual-camera` (add `--camera 1` if the Mac picks your iPhone).
4. In Zoom, Teams, or Meet, choose **OBS Virtual Camera**.

If `--virtual-camera` fails, the app prints install/prime steps and keeps the local preview running. On failure it also tries an automatic OBS prime when OBS is already installed.

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

The app sends frames to the **first available v4l2loopback device** (a `/dev/video*` node from the module). `--virtual-backend v4l2loopback` selects that **backend** when auto-detection would use another (for example OBS); it does not choose a specific `/dev/videoN` path.

List devices with `v4l2-ctl --list-devices` or `ls /dev/video*`. In your meeting app, select the **Video Loopback** (or similarly named) camera.

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
