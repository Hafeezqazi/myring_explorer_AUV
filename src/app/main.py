"""
Application entry point.
"""

from __future__ import annotations

import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def run_app(argv: Optional[list[str]] = None) -> int:
    """
    Launch the GUI application.
    """

    args = argv if argv is not None else sys.argv
    app = QApplication(args)
    main_window = MainWindow()
    main_window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())
