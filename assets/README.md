# Sound assets

This folder holds **user-supplied** sound files. The repository does **not** ship copyrighted audio from *Dragon Ball* or other sources.

## Default sound file

Place a short MP3 at:

```text
assets/instant_transmission.mp3
```

That path is the default for `shunkan-ido` (see `--sfx` in the main [README](../README.md) to use another file).

## Git and licensing

- `*.mp3`, `*.wav`, and `*.ogg` under `assets/` are listed in [`.gitignore`](../.gitignore) so local copies are not committed by mistake.
- Only use audio you **own** or are **licensed** to use.
- Do not commit third-party or copyrighted clips to the repo.

## If the file is missing

The app still runs: preview (and virtual camera, if enabled) work; a missing file triggers a one-time warning and sound is skipped. Use `--no-sfx` if you do not want sound at all.
