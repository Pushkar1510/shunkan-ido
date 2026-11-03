# Ubuntu + Windows virtual camera — Design

**Date:** 2026-11-03  
**Status:** Implemented on `feature/vc-apps-integration`  
**Scope:** Ubuntu first, Windows second. **macOS out of scope.**

## Summary

Ship Instant Transmission as a meeting camera: shared Python effects core + OS virtual-cam sink. Ubuntu uses labeled `v4l2loopback` (**Shunkan-Ido**). Windows uses system-installed OBS Virtual Camera via `pyvirtualcam` (OBS installed once by setup script; not bundled).

## Architecture

```
Webcam → capture → gesture/effects → preview
                                 ↘ VirtualCamSink → Meet/Zoom/Teams
```

- `sinks.PyVirtualCamSink` — pyvirtualcam wrapper  
- `output.FrameOutput` — preview + optional sink  
- `virtual_cam` — Linux detect/setup; Windows OBS detect/prime  

## Non-goals

- macOS Camera Extension / OBS product path  
- Bundling OBS GPL binaries inside the app package  
- Chrome extension  

## Setup entrypoints

| Platform | Script / command |
|----------|------------------|
| Ubuntu | `packaging/ubuntu/setup-virtual-camera.sh` then `shunkan-ido --setup-virtual-camera` |
| Windows | `packaging/windows/setup-virtual-camera.ps1` then `shunkan-ido --setup-virtual-camera` |
| Daily | `shunkan-ido --virtual-camera` |
