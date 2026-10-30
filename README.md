# shunkan-ido

Instant Transmission webcam vanish for Zoom / Teams / Meet.

See `docs/superpowers/specs/2026-10-30-instant-transmission-cam-design.md`.

## Run

From a checkout with the virtualenv activated (Python 3.11+):

```bash
python -m instant_transmission.main
python -m instant_transmission.main --help
```

After `pip install -e .`, the same entry point is `shunkan-ido`.

Useful flags: `--camera`, `--width`, `--height`, `--fps`, `--virtual-camera`, `--virtual-backend`, `--sfx`, `--no-sfx`, `--calibration-seconds`.

On startup, step out of the frame until calibration finishes. The Instant Transmission pose (index and middle fingers together at the forehead) vanishes you; repeat it to reappear. Press `q` or Esc to quit. Preview always opens. `--virtual-camera` also sends the frame to a virtual camera when one is available. Missing audio or a missing virtual camera does not stop the preview.
