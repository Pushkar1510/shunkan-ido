#!/usr/bin/env bash
# One-time Ubuntu/Debian virtual camera setup for shunkan-ido.
# Creates a v4l2loopback device labeled "Shunkan-Ido" (no OBS).
set -euo pipefail

LABEL="Shunkan-Ido"
VIDEO_NR="${VIDEO_NR:-10}"

echo "==> Installing v4l2loopback (requires sudo)…"
sudo apt-get update -y
sudo apt-get install -y v4l2loopback-dkms v4l2loopback-utils

CONF=/etc/modprobe.d/shunkan-ido.conf
echo "==> Persisting module options in ${CONF}…"
echo "options v4l2loopback devices=1 video_nr=${VIDEO_NR} card_label=${LABEL} exclusive_caps=1" | sudo tee "${CONF}" >/dev/null

echo "==> Reloading module with card_label=${LABEL}…"
# Always unload first: a loaded module ignores new parameters, and Chrome/Meet
# can leave the node stuck without VIDEO_OUTPUT (pyvirtualcam then fails).
if lsmod | grep -q '^v4l2loopback'; then
  sudo modprobe -r v4l2loopback || {
    echo "Could not unload v4l2loopback (close Meet/Chrome camera previews and retry)." >&2
    exit 1
  }
fi
sudo modprobe v4l2loopback \
  devices=1 \
  "video_nr=${VIDEO_NR}" \
  "card_label=${LABEL}" \
  exclusive_caps=1

echo "==> Devices:"
if command -v v4l2-ctl >/dev/null 2>&1; then
  v4l2-ctl --list-devices || true
  v4l2-ctl -d "/dev/video${VIDEO_NR}" --all 2>/dev/null | head -20 || true
fi
ls -l /dev/video* 2>/dev/null || true

echo
echo "Done. Verify with:  shunkan-ido --setup-virtual-camera"
echo "Daily use:          start shunkan-ido --virtual-camera *before* Meet"
echo "In Meet/Zoom/Teams pick the camera named: ${LABEL}"
