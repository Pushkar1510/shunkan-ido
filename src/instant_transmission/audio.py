from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)


class SfxPlayer:
    def __init__(self, path: Path, enabled: bool) -> None:
        self._path = Path(path)
        self._enabled = enabled
        self._sound: Any = None
        self._warned = False
        self._mixer: Any = None
        self._unavailable_reason: str | None = None

        if not enabled:
            return
        if not self._path.is_file():
            self._unavailable_reason = f"SFX file not found ({self._path})"
            return

        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init()
                self._mixer = pygame.mixer
            self._sound = pygame.mixer.Sound(str(self._path))
        except Exception as exc:
            self._sound = None
            self._unavailable_reason = f"SFX could not be loaded ({self._path}): {exc}"
            if self._mixer is not None:
                self._mixer.quit()
                self._mixer = None

    def play(self) -> None:
        if not self._enabled:
            return
        if self._sound is None:
            self._warn_once()
            return
        try:
            self._sound.play()
        except Exception as exc:
            self._unavailable_reason = f"SFX playback failed ({self._path}): {exc}"
            self._sound = None
            self._warn_once()

    def close(self) -> None:
        self._sound = None
        if self._mixer is not None:
            self._mixer.quit()
            self._mixer = None

    def _warn_once(self) -> None:
        if self._warned:
            return
        self._warned = True
        reason = self._unavailable_reason or f"SFX file not found ({self._path})"
        _log.warning("warning: %s; continuing without sound", reason)
