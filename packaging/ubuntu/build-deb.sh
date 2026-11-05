#!/usr/bin/env bash
# Scaffold for building an amd64 .deb. Full fpm/dh packaging can replace this later.
# For now: documents the install layout friends will use after `pip install` / future .deb.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "Shunkan-Ido Ubuntu packaging"
echo "Repo root: $ROOT"
echo
echo "Until the .deb pipeline is finished, friends can:"
echo "  1. git clone the repo (or receive a release tarball)"
echo "  2. python3 -m venv .venv && source .venv/bin/activate"
echo "  3. pip install -e ."
echo "  4. shunkan-ido-gui"
echo
echo "Desktop entry template: packaging/ubuntu/shunkan-ido.desktop"
echo "Icon source: assets/shunkan_ido_icon.png"
