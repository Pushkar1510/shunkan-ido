#!/usr/bin/env bash
# One-time Ubuntu/Debian virtual camera setup for shunkan-ido.
# Creates a v4l2loopback device labeled "Shunkan-Ido" (no OBS).
set -euo pipefail

LABEL="Shunkan-Ido"
VIDEO_NR="${VIDEO_NR:-10}"

echo "==> Installing v4l2loopback (requires sudo)…"
sudo apt-get update -y
sudo apt-get install -y v4l2loopback-dkms v4l2loopback-utils

echo "==> Loading module with card_label=${LABEL}…"
# Reload cleanly if an unlabeled loopback was already present.
if lsmod | grep -q '^v4l2loopback'; then
  sudo modprobe -r v4l2loopback || true
fi
sudo modprobe v4l2loopback \
  devices=1 \
  "video_nr=${VIDEO_NR}" \
  "card_label=${LABEL}" \
  exclusive_caps=1

echo "==> Devices:"
if command -v v4l2-ctl >/dev/null 2>&1; then
  v4l2-ctl --list-devices || true
fi
ls -l /dev/video* 2>/dev/null || true

echo
echo "Done. Verify with:  shunkan-ido --setup-virtual-camera"
echo "Daily use:          shunkan-ido --virtual-camera"
echo "In Meet/Zoom/Teams pick the camera named: ${LABEL}"
