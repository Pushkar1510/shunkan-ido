# Windows packaging — virtual camera

On Windows, shunkan-ido feeds **OBS Virtual Camera** through `pyvirtualcam` (backend `obs`). Users install OBS **once** via our setup script (or winget); they do **not** need to operate the OBS UI on every call afterward.

## License choice

| Option | Choice |
|--------|--------|
| Provider | [OBS Studio](https://obsproject.com/) Virtual Camera |
| Distribution | **Not bundled** — installed via `winget` / official installer |
| Why | OBS is GPL; shipping its binaries inside our package would force GPL on redistribution. Calling the system-installed virtual camera from Python is the clean approach. |

Unity Capture (`--virtual-backend unitycapture`) remains an optional advanced path for users who already use it.

## One-time setup

From an elevated or normal PowerShell prompt (winget may prompt for elevation):

```powershell
powershell -ExecutionPolicy Bypass -File packaging/windows/setup-virtual-camera.ps1
```

Or manually:

```powershell
winget install -e --id OBSProject.OBSStudio
shunkan-ido --setup-virtual-camera
```

## Daily use

```powershell
pip install -e .
shunkan-ido --virtual-camera
```

In Meet / Zoom / Teams select **OBS Virtual Camera**.

## Installer sketch (future MSI/Inno)

A future Windows installer should:

1. Install the Python app (or frozen binary).
2. Run / invoke the equivalent of `setup-virtual-camera.ps1` (winget OBS or silent OBS installer with user consent).
3. Create a Start Menu shortcut: `shunkan-ido --virtual-camera`.
