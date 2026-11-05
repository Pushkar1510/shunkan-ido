"""GUI entry point for Shunkan-Ido."""

from __future__ import annotations

import logging
import sys


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from PySide6.QtWidgets import QApplication

    from instant_transmission.ui.launcher import LauncherWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Shunkan-Ido")
    app.setOrganizationName("Shunkan-Ido")
    window = LauncherWindow()
    window.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
