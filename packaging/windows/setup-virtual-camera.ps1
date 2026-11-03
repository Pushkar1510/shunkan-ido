# One-time Windows virtual camera setup for shunkan-ido.
# Installs OBS Studio (GPL) via winget when available, then primes OBS Virtual Camera.
# We do not bundle OBS binaries; winget/download keeps licensing clear.
$ErrorActionPreference = "Stop"

Write-Host "==> Checking for OBS Studio…"

function Find-ObsExe {
    $candidates = @(
        "$env:ProgramFiles\obs-studio\bin\64bit\obs64.exe",
        "${env:ProgramFiles(x86)}\obs-studio\bin\64bit\obs64.exe",
        "$env:LOCALAPPDATA\Programs\obs-studio\bin\64bit\obs64.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    return $null
}

$obs = Find-ObsExe
if (-not $obs) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "==> Installing OBS Studio with winget (OBSProject.OBSStudio)…"
        winget install -e --id OBSProject.OBSStudio --accept-package-agreements --accept-source-agreements
        $obs = Find-ObsExe
    } else {
        Write-Host "winget not found. Install OBS from https://obsproject.com/ then re-run this script."
        exit 1
    }
}

if (-not $obs) {
    Write-Host "OBS was not found after install. Open OBS once manually, then re-run."
    exit 1
}

Write-Host "==> Priming OBS Virtual Camera: $obs"
Start-Process -FilePath $obs -ArgumentList "--startvirtualcam","--minimize-to-tray" | Out-Null
Start-Sleep -Seconds 5

Write-Host @"

Done.
Daily use:   shunkan-ido --virtual-camera
In Meet/Zoom/Teams pick: OBS Virtual Camera

License note: OBS Studio is GPL software installed separately (winget/download),
not redistributed inside the shunkan-ido package.

"@
