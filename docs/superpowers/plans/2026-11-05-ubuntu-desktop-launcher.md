# Ubuntu Desktop Launcher Implementation Plan

> **For agentic workers:** Use subagent-driven-development or execute inline. Steps use checkbox syntax.

**Goal:** Ship a PySide6 launcher that uses the project brand assets and starts Instant Transmission + virtual camera setup on Ubuntu.

**Architecture:** `ui/assets.py` resolves logo/icon/bg; `ui/launcher.py` is the window; `ui/worker.py` runs `main.run` off the UI thread; `ui/app.py` is the entry. `.deb` packaging follows once the GUI works.

**Tech Stack:** PySide6, existing Instant Transmission core, packaging/ubuntu scripts

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-04-ubuntu-desktop-launcher-design.md`
- Brand assets (committed per user/legal):
  - `assets/Shunkan_ido_bg.jpg`
  - `assets/shunkan_ido_logo.png`
  - `assets/shunkan_ido_icon.png`
- Ubuntu first; Windows deferred
- Author Pushkar1510; no AI co-author trailer when committing

## Tasks

1. Asset resolver + tests  
2. Launcher UI (background, logo, status, Setup + Start)  
3. Worker Start/Stop + Setup → virtual cam script  
4. Entry point `shunkan-ido-gui`, pyproject, README  
5. Desktop file + build-deb.sh (basic)
