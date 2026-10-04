"""Loads the Qt stylesheet and exposes the design tokens shared with it.

Most styling lives in ``theme.qss``. These Python constants mirror a few of its
values so the UI can build style fragments at runtime — chiefly recolouring the
emotion display with the colour of the emotion that was just detected.
"""

from pathlib import Path

_QSS_PATH = Path(__file__).with_name("theme.qss")

# Neutral chrome — kept deliberately quiet so the detected emotion's colour is
# the only strong colour on screen.
BG = "#F3F4F6"
SURFACE = "#FFFFFF"
BORDER = "#E3E6EB"
INK = "#1B2330"
MUTED = "#616B7A"
ACCENT = "#1E6F64"   # calm teal, used for the primary action


def load_stylesheet() -> str:
    try:
        return _QSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""