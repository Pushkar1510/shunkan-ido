# Ubuntu packaging

## `.deb` for friends (amd64)

On this machine (Ubuntu amd64), from the repo root:

```bash
bash packaging/ubuntu/build-deb.sh
```

Output: `dist/shunkan-ido_<version>_amd64.deb`

Friend install:

```bash
sudo apt install ./shunkan-ido_0.1.0_amd64.deb
```

Then open **Shunkan-Ido** from the app grid → **Setup virtual camera** → **Start calibrating** → in Meet pick **Shunkan-Ido**.

## Virtual camera

Shunkan-ido publishes Instant Transmission frames to a **v4l2loopback** device named **Shunkan-Ido**. Meeting apps (Google Meet, Zoom, etc.) select that camera. **OBS is not required** on Ubuntu.

## One-time setup

From the repo root:

```bash
bash packaging/ubuntu/setup-virtual-camera.sh
```

This installs `v4l2loopback-dkms` / `v4l2loopback-utils` and loads:

```text
v4l2loopback devices=1 video_nr=10 card_label=Shunkan-Ido exclusive_caps=1
```

Verify:

```bash
shunkan-ido --setup-virtual-camera
```

## Daily use

```bash
pip install -e .   # once per environment
shunkan-ido --virtual-camera
```

In Meet/Zoom/Teams choose **Shunkan-Ido** (or Video Loopback).

## Persist across reboot

Create `/etc/modprobe.d/shunkan-ido.conf`:

```text
options v4l2loopback devices=1 video_nr=10 card_label=Shunkan-Ido exclusive_caps=1
```

And ensure the module loads at boot (e.g. add `v4l2loopback` to `/etc/modules-load.d/shunkan-ido.conf`).

## Notes

- Kernel upgrades may require rebuilding DKMS modules (`sudo apt install --reinstall v4l2loopback-dkms`).
- If `--virtual-camera` fails, re-run the setup script or `shunkan-ido --setup-virtual-camera` for guidance.
