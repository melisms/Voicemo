"""Reusable widgets for the main window's body, plus the floating mini bar."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.emotion_style import DisplayResult


def _rgb(color: str):
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def make_pill(emoji: str, label: str, color: str, time_str: str) -> QLabel:
    """Labelled chip (emoji + time) for the full-window timeline."""
    r, g, b = _rgb(color)
    pill = QLabel(f"{emoji}  {time_str}")
    pill.setToolTip(label)
    pill.setStyleSheet(
        f"background: rgba({r},{g},{b},0.12);"
        f"color: {color}; border: 1px solid rgba({r},{g},{b},0.45);"
        "border-radius: 12px; padding: 6px 12px; font-weight: 600;"
    )
    return pill


def make_emoji_chip(emoji: str, label: str, color: str, time_str: str) -> QLabel:
    """Compact emoji-only chip (time in the tooltip) for the mini bar."""
    r, g, b = _rgb(color)
    chip = QLabel(emoji)
    chip.setAlignment(Qt.AlignCenter)
    chip.setFixedSize(34, 34)
    chip.setToolTip(f"{label} · {time_str}")
    chip.setStyleSheet(
        f"background: rgba({r},{g},{b},0.16);"
        f"border: 1px solid rgba({r},{g},{b},0.30);"
        "border-radius: 10px; font-size: 19px;"
    )
    return chip


class _PillStrip:
    """Mixin: a horizontal, auto-scrolling, capped row of chips/pills."""

    _MAX_ITEMS = 60

    def _init_strip(self, height: int, show_scrollbar: bool = True) -> QScrollArea:
        self._strip = QWidget()
        self._row = QHBoxLayout(self._strip)
        self._row.setContentsMargins(2, 2, 2, 2)
        self._row.setSpacing(8)
        self._row.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("timeline")
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(height)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded if show_scrollbar else Qt.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self._strip)
        self._scroll = scroll
        self._items: list[QWidget] = []
        return scroll

    def _add_item(self, widget: QWidget) -> None:
        self._row.insertWidget(self._row.count() - 1, widget)  # before the stretch
        self._items.append(widget)
        while len(self._items) > self._MAX_ITEMS:
            old = self._items.pop(0)
            old.setParent(None)
            old.deleteLater()
        bar = self._scroll.horizontalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    def _clear_items(self) -> None:
        for w in self._items:
            w.setParent(None)
            w.deleteLater()
        self._items = []


class Card(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("card")


class EmotionCard(Card):
    """The hero: large emoji, emotion word, and a confidence bar."""

    def __init__(self) -> None:
        super().__init__()
        self._emoji = QLabel("\U0001F3A4")
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
        self._emoji.setText("\U0001F3A7")
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


class TimelinePanel(Card, _PillStrip):
    """Full-window timeline: labelled pills (emoji + time)."""

    def __init__(self) -> None:
        super().__init__()
        heading = QLabel("Emotion timeline")
        heading.setObjectName("panelHeading")
        self._placeholder = QLabel("Emotions will appear here as people speak.")
        self._placeholder.setObjectName("emotionMeta")
        scroll = self._init_strip(height=56, show_scrollbar=True)
        scroll.hide()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(heading)
        layout.addWidget(self._placeholder)
        layout.addWidget(scroll)

    def add(self, emoji: str, label: str, color: str, time_str: str) -> None:
        if not self._scroll.isVisible():
            self._placeholder.hide()
            self._scroll.show()
        self._add_item(make_pill(emoji, label, color, time_str))

    def clear(self) -> None:
        self._clear_items()
        self._scroll.hide()
        self._placeholder.show()


class MiniBar(QWidget, _PillStrip):
    """Floating always-on-top strip streaming instantaneous emotions as compact
    emoji chips, with no scrollbar. Double-click or ⤢ restores the main window."""

    restore_requested = Signal()

    def __init__(self) -> None:
        flags = (Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                 | Qt.WindowDoesNotAcceptFocus)
        # Tool keeps it out of the taskbar, but on macOS a Tool window hides
        # whenever the app is inactive — exactly what we must avoid here.
        if sys.platform != "darwin":
            flags |= Qt.Tool
        super().__init__(None, flags)
        self.setObjectName("miniBarWindow")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._drag = None

        # some window managers push a frameless window behind others on a
        # focus change; re-assert top every so often while it's visible.
        self._raise_timer = QTimer(self)
        self._raise_timer.setInterval(1200)
        self._raise_timer.timeout.connect(self._keep_on_top)

        card = QFrame()
        card.setObjectName("miniBar")

        self._cur_emoji = QLabel("\U0001F3A7")
        self._cur_emoji.setObjectName("miniEmoji")
        self._cur_label = QLabel("Listening")
        self._cur_label.setObjectName("miniLabel")

        divider = QFrame()
        divider.setObjectName("miniDivider")
        divider.setFrameShape(QFrame.VLine)

        scroll = self._init_strip(height=38, show_scrollbar=False)

        self._restore_btn = QPushButton("\u2922")  # ⤢
        self._restore_btn.setObjectName("miniRestore")
        self._restore_btn.setToolTip("Back to the full window")
        self._restore_btn.setFixedSize(32, 32)
        self._restore_btn.clicked.connect(self.restore_requested.emit)

        inner = QHBoxLayout(card)
        inner.setContentsMargins(16, 8, 10, 8)
        inner.setSpacing(12)
        inner.addWidget(self._cur_emoji)
        inner.addWidget(self._cur_label)
        inner.addWidget(divider)
        inner.addWidget(scroll, stretch=1)
        inner.addWidget(self._restore_btn)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

    def add(self, emoji: str, label: str, color: str, time_str: str) -> None:
        self._cur_emoji.setText(emoji)
        self._cur_label.setText(label)
        self._cur_label.setStyleSheet(f"color: {color}; font-weight: 700;")
        self._add_item(make_emoji_chip(emoji, label, color, time_str))

    def reset(self) -> None:
        self._cur_emoji.setText("\U0001F3A7")
        self._cur_label.setText("Listening")
        self._cur_label.setStyleSheet("")
        self._clear_items()

    def dock_bottom(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        w = min(820, screen.width() - 40)
        self.resize(w, 58)
        self.move(screen.center().x() - w // 2, screen.bottom() - 58 - 16)

    def _keep_on_top(self) -> None:
        if self.isVisible():
            self.raise_()

    def showEvent(self, e) -> None:
        self._raise_timer.start()
        self.raise_()
        super().showEvent(e)

    def hideEvent(self, e) -> None:
        self._raise_timer.stop()
        super().hideEvent(e)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:
        if self._drag is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e) -> None:
        self._drag = None

    def mouseDoubleClickEvent(self, e) -> None:
        self.restore_requested.emit()