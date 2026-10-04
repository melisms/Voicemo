"""Application entry point.

Run from the project root with:

    python -m app.main

The sys.path line also lets ``python app/main.py`` work directly, by putting
the project root on the import path.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

# Re-exported so `from app.main import MainWindow` keeps working.
from app.ui.main_window import MainWindow

__all__ = ["MainWindow", "main"]


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Voicemo")
    app.setApplicationDisplayName("Voicemo")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()