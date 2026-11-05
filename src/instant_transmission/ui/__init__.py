"""PySide6 desktop launcher for Shunkan-Ido."""

from __future__ import annotations

__all__ = ["run_gui"]


def run_gui() -> int:
    from instant_transmission.ui.app import main

    return main()
