from pathlib import Path

from instant_transmission.audio import SfxPlayer


def test_missing_sfx_does_not_raise(tmp_path: Path):
    player = SfxPlayer(tmp_path / "missing.mp3", enabled=True)
    player.play()  # warns once, no exception
    player.play()
    player.close()


def test_disabled_sfx_noop(tmp_path: Path):
    player = SfxPlayer(tmp_path / "missing.mp3", enabled=False)
    player.play()
    player.close()
