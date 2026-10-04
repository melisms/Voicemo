"""Reusable widgets for the main window's body.

Three panels: the emotion display (hero), the transcript panel (which can either
show one result or stream lines in live mode), and the emotion timeline that
fills up as a live conversation goes on.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.emotion_style import DisplayResult


class Card(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("card")


class EmotionCard(Card):
    """The hero: large emoji, emotion word, and a confidence bar."""

    def __init__(self) -> None:
        super().__init__()

        self._emoji = QLabel("\U0001F3A4")  # mic
        self._emoji.setObjectName("emotionEmoji")
        self._emoji.setAlignment(Qt.AlignCenter)

        self._label = QLabel("Ready")
        self._label.setObjectName("emotionLabel")
        self._label.setAlignment(Qt.AlignCenter)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)

        self._meta = QLabel("Load or record audio to begin")
        self._meta.setObjectName("emotionMeta")
        self._meta.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 32, 28, 28)
        layout.setSpacing(16)
        layout.addStretch(1)
        layout.addWidget(self._emoji)
        layout.addWidget(self._label)
        layout.addWidget(self._bar)
        layout.addWidget(self._meta)
        layout.addStretch(1)

    def show_result(self, result: DisplayResult) -> None:
        self._emoji.setText(result.emoji)
        self._label.setText(result.label)
        self._label.setStyleSheet(f"color: {result.color};")
        self._bar.setRange(0, 100)
        self._bar.setValue(round(result.confidence * 100))
        self._bar.setStyleSheet(
            "QProgressBar::chunk { border-radius: 5px; "
            f"background-color: {result.color}; }}"
        )
        pct = f"{result.confidence * 100:.0f}%"
        self._meta.setText(
            f"{pct} confidence" if result.confident else f"Low confidence ({pct})"
        )

    def show_waiting(self) -> None:
        self._emoji.setText("\u23F3")
        self._label.setText("Analyzing")
        self._label.setStyleSheet("")
        self._bar.setStyleSheet("")
        self._bar.setRange(0, 0)
        self._meta.setText("Running Whisper and emotion2vec")

    def show_listening(self) -> None:
        self._emoji.setText("\U0001F3A7")  # headphones
        self._label.setText("Listening")
        self._label.setStyleSheet("")
        self._bar.setStyleSheet("")
        self._bar.setRange(0, 0)
        self._meta.setText("Waiting for speech")

    def reset(self) -> None:
        self._emoji.setText("\U0001F3A4")
        self._label.setText("Ready")
        self._label.setStyleSheet("")
        self._bar.setStyleSheet("")
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._meta.setText("Load or record audio to begin")


class TranscriptPanel(Card):
    """Shows the recognised speech — one result, or a running stream."""

    def __init__(self) -> None:
        super().__init__()

        heading = QLabel("Transcript")
        heading.setObjectName("panelHeading")

        self._text = QTextEdit()
        self._text.setObjectName("transcript")
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("The transcript will appear here.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(self._text, stretch=1)

    def set_text(self, text: str) -> None:
        self._text.setPlainText(text or "(No speech detected.)")

    def append_line(self, text: str, prefix: str = "") -> None:
        text = (text or "").strip()
        if not text:
            return
        self._text.append(f"{prefix}{text}" if prefix else text)

    def clear(self) -> None:
        self._text.clear()


class TimelinePanel(Card):
    """A horizontal strip of emotion pills that grows as a conversation goes."""

    _MAX_PILLS = 40

    def __init__(self) -> None:
        super().__init__()

        heading = QLabel("Emotion timeline")
        heading.setObjectName("panelHeading")

        self._placeholder = QLabel("Emotions will appear here as people speak.")
        self._placeholder.setObjectName("emotionMeta")

        self._strip = QWidget()
        self._row = QHBoxLayout(self._strip)
        self._row.setContentsMargins(2, 2, 2, 2)
        self._row.setSpacing(8)
        self._row.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("timeline")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFixedHeight(56)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setWidget(self._strip)
        self._scroll.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(heading)
        layout.addWidget(self._placeholder)
        layout.addWidget(self._scroll)

        self._pills: list[QLabel] = []

    def add(self, emoji: str, label: str, color: str, time_str: str) -> None:
        if not self._scroll.isVisible():
            self._placeholder.hide()
            self._scroll.show()

        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        pill = QLabel(f"{emoji}  {time_str}")
        pill.setToolTip(label)
        pill.setStyleSheet(
            f"background: rgba({r},{g},{b},0.12);"
            f"color: {color}; border: 1px solid rgba({r},{g},{b},0.45);"
            "border-radius: 12px; padding: 6px 12px; font-weight: 600;"
        )
        self._row.insertWidget(self._row.count() - 1, pill)  # before the stretch
        self._pills.append(pill)

        while len(self._pills) > self._MAX_PILLS:
            old = self._pills.pop(0)
            old.setParent(None)
            old.deleteLater()

        bar = self._scroll.horizontalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    def clear(self) -> None:
        for pill in self._pills:
            pill.setParent(None)
            pill.deleteLater()
        self._pills = []
        self._scroll.hide()
        self._placeholder.show()