"""The Voicemo application window — file analysis plus a live meeting mode.

File mode:  [ Open audio file ] [ Analyze ]        → one-shot analysis of a file.
Live mode:  [ Source ▾ ] [ ● Start listening ]     → continuous analysis of the
            microphone or the meeting's audio (system/loopback), with a smoothed
            current emotion, a streaming transcript, and an emotion timeline.

Nothing blocks the UI: file analysis and each live window run on background
threads. Live can be started and stopped as many times as you like without
restarting the app.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import AUDIO_CHUNK_SECONDS
from app.core.aggregator import EmotionAggregator
from app.ui.components import EmotionCard, MiniBar, TimelinePanel, TranscriptPanel
from app.ui.emotion_style import DisplayResult, style_for
from app.ui.live import LiveCapture, LiveWindowWorker
from app.ui.worker import AnalysisWorker

_AUDIO_FILTER = "Audio files (*.wav *.mp3 *.m4a *.flac *.ogg);;All files (*)"
_ISTANBUL = timezone(timedelta(hours=3))  # UTC+3, no DST


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Voicemo")
        self.resize(980, 680)
        self.setMinimumSize(820, 600)

        # file mode state
        self._audio_path: Path | None = None
        self._run_id = 0
        self._file_workers: list[AnalysisWorker] = []

        # live mode state
        self._capture: LiveCapture | None = None
        self._live_worker: LiveWindowWorker | None = None
        self._pending_window = None
        self._aggregator = EmotionAggregator(window_size=5)
        self._live_started_at = 0.0
        self._mini = MiniBar()
        self._mini.restore_requested.connect(self._restore_from_mini)

        self._build_ui()
        self.setStyleSheet(_load_stylesheet())

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 22, 28, 20)
        outer.setSpacing(16)

        outer.addLayout(self._build_header())
        outer.addWidget(self._build_controls())
        outer.addLayout(self._build_body(), stretch=1)

        self._timeline = TimelinePanel()
        outer.addWidget(self._timeline)

        self._status = QLabel("Ready")
        self._status.setObjectName("status")
        outer.addWidget(self._status)

        self.setCentralWidget(root)

    def _build_header(self) -> QVBoxLayout:
        title = QLabel("Voicemo")
        title.setObjectName("appTitle")
        subtitle = QLabel("Speech emotion analysis for accessible online meetings")
        subtitle.setObjectName("appSubtitle")
        box = QVBoxLayout()
        box.setSpacing(3)
        box.addWidget(title)
        box.addWidget(subtitle)
        return box

    def _build_controls(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("controlBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)

        # --- file controls ---
        self._open_btn = QPushButton("Open audio file")
        self._open_btn.clicked.connect(self._on_open_file)

        self._analyze_btn = QPushButton("Analyze")
        self._analyze_btn.setObjectName("primary")
        self._analyze_btn.setEnabled(False)
        self._analyze_btn.clicked.connect(self._on_analyze)

        self._file_label = QLabel("No file")
        self._file_label.setObjectName("fileName")

        # --- live controls ---
        self._source = QComboBox()
        self._source.addItem("Microphone", "mic")
        self._source.addItem("Meeting audio (system)", "system")

        self._live_btn = QPushButton("Start listening")
        self._live_btn.setObjectName("primary")
        self._live_btn.clicked.connect(self._on_toggle_live)

        row.addWidget(self._open_btn)
        row.addWidget(self._analyze_btn)
        row.addWidget(self._file_label, stretch=1)
        row.addWidget(_divider())
        row.addWidget(QLabel("Live:"))
        row.addWidget(self._source)
        row.addWidget(self._live_btn)
        return bar

    def _build_body(self) -> QGridLayout:
        self._emotion_card = EmotionCard()
        self._transcript = TranscriptPanel()
        body = QGridLayout()
        body.setSpacing(16)
        body.addWidget(self._emotion_card, 0, 0)
        body.addWidget(self._transcript, 0, 1)
        body.setColumnStretch(0, 4)
        body.setColumnStretch(1, 6)
        return body

    # ============================================================== FILE MODE
    def _on_open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select audio file", "", _AUDIO_FILTER
        )
        if path:
            self._audio_path = Path(path)
            self._file_label.setText(self._audio_path.name)
            self._analyze_btn.setEnabled(True)
            self._status.setText(f"Loaded {self._audio_path.name}")

    def _on_analyze(self) -> None:
        if self._audio_path is None or self._capture is not None:
            return
        self._run_id += 1
        run_id = self._run_id
        self._emotion_card.show_waiting()
        self._transcript.clear()
        self._open_btn.setEnabled(False)
        self._analyze_btn.setEnabled(False)
        self._status.setText(f"Analyzing {self._audio_path.name}")

        worker = AnalysisWorker(run_id, self._audio_path)
        worker.succeeded.connect(self._on_file_result)
        worker.failed.connect(self._on_file_error)
        worker.finished.connect(lambda w=worker: self._cleanup_file_worker(w))
        self._file_workers.append(worker)
        worker.start()

    def _on_file_result(self, run_id: int, result: DisplayResult) -> None:
        if run_id != self._run_id:
            return
        self._emotion_card.show_result(result)
        self._transcript.set_text(result.transcript)
        self._status.setText(f"Done — {result.label.lower()}")
        self._reset_file_buttons()

    def _on_file_error(self, run_id: int, message: str) -> None:
        if run_id != self._run_id:
            return
        self._emotion_card.reset()
        self._status.setText(f"Couldn't analyze: {message}")
        self._reset_file_buttons()
        QMessageBox.warning(self, "Analysis failed", message)

    def _cleanup_file_worker(self, worker: AnalysisWorker) -> None:
        if worker in self._file_workers:
            self._file_workers.remove(worker)
        worker.deleteLater()

    def _reset_file_buttons(self) -> None:
        self._open_btn.setEnabled(True)
        self._analyze_btn.setEnabled(self._audio_path is not None)

    # ============================================================== LIVE MODE
    def _on_toggle_live(self) -> None:
        if self._capture is None:
            self._start_live()
        else:
            self._stop_live()

    def _start_live(self) -> None:
        source = self._source.currentData()

        if source == "system" and not LiveCapture.system_available():
            if sys.platform == "win32":
                msg = ("Capturing the meeting's audio needs PyAudioWPatch.\n\n"
                       "Install it, then try again:\n    pip install PyAudioWPatch")
            else:
                msg = ("To capture the meeting's audio on macOS you need a virtual\n"
                       "audio device that sends system sound back in as an input.\n\n"
                       "1. Install BlackHole:   brew install blackhole-2ch\n"
                       "2. In Audio MIDI Setup, create a Multi-Output Device that\n"
                       "   includes both your speakers and BlackHole, and select it\n"
                       "   as the system output.\n"
                       "3. Start listening again and pick \"Meeting audio\".")
            QMessageBox.information(self, "Meeting audio", msg)
            return
        if source == "mic" and not LiveCapture.mic_available():
            QMessageBox.information(
                self, "Microphone",
                "Microphone capture needs sounddevice:\n    pip install sounddevice",
            )
            return

        # fresh session
        self._aggregator = EmotionAggregator(window_size=5)
        self._pending_window = None
        self._timeline.clear()
        self._mini.reset()
        self._transcript.clear()
        self._emotion_card.show_listening()
        self._live_started_at = time.monotonic()

        self._capture = LiveCapture(source=source, window_seconds=AUDIO_CHUNK_SECONDS)
        self._capture.window_ready.connect(self._on_window)
        self._capture.error.connect(self._on_capture_error)
        self._capture.start()

        self._set_live_running(True)
        label = "the meeting" if source == "system" else "your microphone"
        self._status.setText(f"Listening to {label}…")

    def _stop_live(self) -> None:
        if self._capture is not None:
            self._capture.window_ready.disconnect(self._on_window)
            self._capture.stop()
            self._capture = None
        self._set_live_running(False)
        self._mini.hide()
        self._emotion_card.reset()
        self._status.setText("Stopped listening")

    def _on_window(self, audio) -> None:
        # single-flight: keep only the most recent window if we're still busy
        if self._live_worker is not None:
            self._pending_window = audio
            return
        self._start_window_worker(audio)

    def _start_window_worker(self, audio) -> None:
        worker = LiveWindowWorker(audio)
        worker.done.connect(self._on_segment)
        worker.failed.connect(self._on_live_error)
        worker.finished.connect(self._on_window_worker_done)
        self._live_worker = worker
        worker.start()

    def _on_window_worker_done(self) -> None:
        if self._live_worker is not None:
            self._live_worker.deleteLater()
        self._live_worker = None
        if self._pending_window is not None and self._capture is not None:
            pending, self._pending_window = self._pending_window, None
            self._start_window_worker(pending)

    def _on_segment(self, seg: dict) -> None:
        if self._capture is None:
            return  # a late segment after stop — ignore

        emotion = seg.get("emotion", "unknown")
        confidence = float(seg.get("confidence", 0.0))
        transcript = seg.get("transcription", "")

        # hero shows the smoothed (dominant-over-window) emotion so it doesn't flicker
        smoothed = self._aggregator.add_emotion(emotion, confidence)
        hero = style_for(smoothed)
        self._emotion_card.show_result(DisplayResult(
            transcript=transcript, emotion=smoothed, confidence=confidence,
            emoji=hero.emoji, color=hero.color, label=hero.label,
            confident=confidence >= 0.60,
        ))

        stamp = self._timestamp()
        if transcript.strip():
            self._transcript.append_line(transcript, prefix=f"[{stamp}] ")

        raw = style_for(emotion)  # the per-window (instantaneous) emotion
        self._timeline.add(raw.emoji, raw.label, raw.color, stamp)
        self._mini.add(raw.emoji, raw.label, raw.color, stamp)
        self._status.setText(f"Listening… current mood: {hero.label.lower()}")

    def _on_capture_error(self, message: str) -> None:
        self._status.setText(f"Capture error: {message}")
        self._stop_live()
        QMessageBox.warning(self, "Couldn't capture audio", message)

    def _on_live_error(self, message: str) -> None:
        self._status.setText(f"Analysis error: {message}")

    def _timestamp(self) -> str:
        # elapsed since listening started + wall-clock Istanbul time (UTC+3)
        secs = int(time.monotonic() - self._live_started_at)
        elapsed = f"{secs // 60:02d}:{secs % 60:02d}"
        clock = datetime.now(_ISTANBUL).strftime("%H:%M:%S")
        return f"{elapsed}  ·  {clock}"

    def _set_live_running(self, running: bool) -> None:
        self._live_btn.setText("Stop" if running else "Start listening")
        self._live_btn.setObjectName("recording" if running else "primary")
        self._live_btn.style().unpolish(self._live_btn)
        self._live_btn.style().polish(self._live_btn)
        self._source.setEnabled(not running)
        self._open_btn.setEnabled(not running)
        self._analyze_btn.setEnabled(not running and self._audio_path is not None)

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.WindowStateChange:
            # while a live session runs, minimising pops the floating mini bar
            if self.isMinimized() and self._capture is not None:
                self._mini.dock_bottom()
                self._mini.show()
            else:
                self._mini.hide()
        super().changeEvent(event)

    def _restore_from_mini(self) -> None:
        self._mini.hide()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:  # stop capture cleanly on window close
        if self._capture is not None:
            self._capture.stop()
        self._mini.close()
        super().closeEvent(event)


# --- small helpers ---------------------------------------------------------
def _divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.VLine)
    return line


def _load_stylesheet() -> str:
    from app.ui.theme import load_stylesheet
    return load_stylesheet()