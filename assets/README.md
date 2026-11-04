# Sound assets

This folder holds **user-supplied** sound files. The repository does **not** ship copyrighted audio from *Dragon Ball* or other sources.

## Default sound file

Place a short MP3 at:

```text
assets/instant_transmission.mp3
```

That path is the default for `shunkan-ido` (see `--sfx` in the main [README](../README.md) to use another file).

## Phoenix snap sound (optional)

For the finger-snap palm orb, place a short MP3 at:

```text
assets/phoenix_snap.mp3
```

Default for Phoenix snap SFX (see `--phoenix-sfx` and `--no-phoenix` in the main [README](../README.md)). You can use any short clip you own or generate a synthetic snap locally; do not use copyrighted game audio.

## Git and licensing

- `*.mp3`, `*.wav`, and `*.ogg` under `assets/` are listed in [`.gitignore`](../.gitignore) so local copies are not committed by mistake.
- Only use audio you **own** or are **licensed** to use.
- Do not commit third-party or copyrighted clips to the repo.

## If the file is missing

The app still runs: preview (and virtual camera, if enabled) work; a missing file triggers a one-time warning and sound is skipped. Use `--no-sfx` if you do not want sound at all.
