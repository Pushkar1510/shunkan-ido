#!/usr/bin/env bash
# Build an amd64 .deb that friends can install with: sudo apt install ./shunkan-ido_*.deb
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG_NAME="shunkan-ido"
cd "$ROOT"
VERSION="$(python3 - <<'PY'
from pathlib import Path
text = Path("pyproject.toml").read_text(encoding="utf-8")
for line in text.splitlines():
    if line.startswith("version"):
        print(line.split("=", 1)[1].strip().strip('"'))
        break
else:
    raise SystemExit("version not found in pyproject.toml")
PY
)"
ARCH="$(dpkg --print-architecture)"
OUT_DIR="${OUT_DIR:-$ROOT/dist}"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/${PKG_NAME}-deb.XXXXXX")"
OPT_ROOT="/opt/${PKG_NAME}"
STAGE_OPT="${STAGE}${OPT_ROOT}"

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "This script builds amd64 packages (got $(uname -m))." >&2
  exit 1
fi

echo "==> Staging tree in ${STAGE}"
mkdir -p \
  "${STAGE_OPT}/assets" \
  "${STAGE_OPT}/packaging/ubuntu" \
  "${STAGE}/usr/bin" \
  "${STAGE}/usr/share/applications" \
  "${STAGE}/usr/share/icons/hicolor/256x256/apps" \
  "${STAGE}/usr/share/doc/${PKG_NAME}" \
  "${STAGE}/DEBIAN"

echo "==> Creating venv + installing ${PKG_NAME} ${VERSION}"
python3 -m venv "${STAGE_OPT}/venv"
# shellcheck disable=SC1091
source "${STAGE_OPT}/venv/bin/activate"
python -m pip install --upgrade pip wheel
python -m pip install "${ROOT}"
deactivate

echo "==> Rewriting venv paths for /opt install"
# Staging path is .../opt/shunkan-ido; strip the STAGE prefix so shebangs
# and pyvenv.cfg point at /opt/shunkan-ido after dpkg install.
while IFS= read -r -d '' file; do
  if grep -q "$STAGE" "$file" 2>/dev/null; then
    sed -i "s|${STAGE}||g" "$file"
  fi
done < <(find "${STAGE_OPT}/venv" -type f \( -path '*/bin/*' -o -name '*.cfg' -o -name '*.pth' \) -print0)

echo "==> Copying brand assets + setup script"
cp -a "${ROOT}/assets/Shunkan_ido_bg.jpg" "${STAGE_OPT}/assets/" 2>/dev/null || true
cp -a "${ROOT}/assets/shunkan_ido_logo.png" "${STAGE_OPT}/assets/" 2>/dev/null || true
cp -a "${ROOT}/assets/shunkan_ido_icon.png" "${STAGE_OPT}/assets/" 2>/dev/null || true
# Optional SFX (often gitignored) — include when present so friends hear teleport.
if [[ -f "${ROOT}/assets/instant_transmission.mp3" ]]; then
  cp -a "${ROOT}/assets/instant_transmission.mp3" "${STAGE_OPT}/assets/"
fi
cp -a "${ROOT}/packaging/ubuntu/setup-virtual-camera.sh" "${STAGE_OPT}/packaging/ubuntu/"
chmod 755 "${STAGE_OPT}/packaging/ubuntu/setup-virtual-camera.sh"

echo "==> Wrappers, desktop entry, icon"
cat > "${STAGE}/usr/bin/shunkan-ido" <<EOF
#!/bin/bash
export SHUNKAN_IDO_ASSETS=${OPT_ROOT}/assets
export SHUNKAN_IDO_ROOT=${OPT_ROOT}
exec ${OPT_ROOT}/venv/bin/shunkan-ido "\$@"
EOF
cat > "${STAGE}/usr/bin/shunkan-ido-gui" <<EOF
#!/bin/bash
export SHUNKAN_IDO_ASSETS=${OPT_ROOT}/assets
export SHUNKAN_IDO_ROOT=${OPT_ROOT}
exec ${OPT_ROOT}/venv/bin/shunkan-ido-gui "\$@"
EOF
chmod 755 "${STAGE}/usr/bin/shunkan-ido" "${STAGE}/usr/bin/shunkan-ido-gui"

sed "s|^Exec=.*|Exec=shunkan-ido-gui|; s|^Icon=.*|Icon=shunkan-ido|" \
  "${ROOT}/packaging/ubuntu/shunkan-ido.desktop" \
  > "${STAGE}/usr/share/applications/shunkan-ido.desktop"

if [[ -f "${ROOT}/assets/shunkan_ido_icon.png" ]]; then
  cp -a "${ROOT}/assets/shunkan_ido_icon.png" \
    "${STAGE}/usr/share/icons/hicolor/256x256/apps/shunkan-ido.png"
fi

cat > "${STAGE}/usr/share/doc/${PKG_NAME}/README.Debian" <<EOF
Shunkan-Ido ${VERSION}
====================

1. Install:  sudo apt install ./${PKG_NAME}_${VERSION}_${ARCH}.deb
2. Open "Shunkan-Ido" from the app grid (or run shunkan-ido-gui).
3. Click "Setup virtual camera" once (password prompt).
4. Click "Start calibrating", then in Meet/Zoom pick camera "Shunkan-Ido"
   (not Integrated Camera). Start this app before opening Meet.

Virtual-camera helper: ${OPT_ROOT}/packaging/ubuntu/setup-virtual-camera.sh
EOF
gzip -9n -c "${STAGE}/usr/share/doc/${PKG_NAME}/README.Debian" \
  > "${STAGE}/usr/share/doc/${PKG_NAME}/README.Debian.gz"
rm -f "${STAGE}/usr/share/doc/${PKG_NAME}/README.Debian"
cp -a "${ROOT}/LICENSE" "${STAGE}/usr/share/doc/${PKG_NAME}/copyright" 2>/dev/null \
  || printf 'Copyright (c) Pushkar1510. All rights reserved.\n' \
    > "${STAGE}/usr/share/doc/${PKG_NAME}/copyright"

echo "==> DEBIAN metadata"
SIZE_KB="$(du -sk "${STAGE}" | awk '{print $1}')"
cat > "${STAGE}/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: video
Priority: optional
Architecture: ${ARCH}
Maintainer: Pushkar1510 <pushkargharat2001@gmail.com>
Installed-Size: ${SIZE_KB}
Depends: python3 (>= 3.11), libgl1, libglib2.0-0, libxkbcommon0, libdbus-1-3, libegl1, libfontconfig1, libfreetype6, libxcb-cursor0, libxcb-xinerama0, libasound2t64 | libasound2
Recommends: v4l2loopback-dkms, v4l2loopback-utils
Description: Instant Transmission webcam vanish for video meetings
 Shunkan-Ido vanishes you from the webcam with an Instant Transmission
 effect and can publish frames to a virtual camera for Meet, Zoom, or Teams.
EOF

cat > "${STAGE}/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
EOF
chmod 755 "${STAGE}/DEBIAN/postinst"

# Drop compile/pyc caches to shrink the package a bit
find "${STAGE_OPT}/venv" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "${STAGE_OPT}/venv" -type f -name '*.pyc' -delete 2>/dev/null || true

mkdir -p "${OUT_DIR}"
DEB_PATH="${OUT_DIR}/${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo "==> Building ${DEB_PATH}"
dpkg-deb --root-owner-group --build "${STAGE}" "${DEB_PATH}"
echo
echo "Built: ${DEB_PATH}"
ls -lh "${DEB_PATH}"
echo
echo "Friend install:"
echo "  sudo apt install ./${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo "  # or: sudo apt install ${DEB_PATH}"
