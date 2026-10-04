"""Runs the backend pipeline off the GUI thread.

Each run carries a ``run_id``; the window ignores any result whose id is not the
latest, so a late-arriving result can never overwrite a newer one. The backend
pipeline is created once, on the worker thread, and cached so the models load
only a single time.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.confidence import is_confident
from app.ui.emotion_style import DisplayResult, style_for


class AnalysisWorker(QThread):
    succeeded = Signal(int, object)   # run_id, DisplayResult
    failed = Signal(int, str)         # run_id, error message

    _pipeline = None  # shared across runs so the models load only once

    def __init__(self, run_id: int, audio_path: str | Path) -> None:
        super().__init__()
        self._run_id = run_id
        self._audio_path = str(audio_path)

    def run(self) -> None:  # executed on the worker thread
        try:
            pipeline = self._get_pipeline()
            raw = pipeline.process(self._audio_path)
            result = self._to_display(raw)
        except Exception as exc:  # noqa: BLE001 — surfaced to the UI
            self.failed.emit(self._run_id, self._friendly_error(exc))
        else:
            self.succeeded.emit(self._run_id, result)

    @classmethod
    def _get_pipeline(cls):
        if cls._pipeline is None:
            from app.inference.pipeline import VoicemoPipeline

            cls._pipeline = VoicemoPipeline()
        return cls._pipeline

    @staticmethod
    def _to_display(raw: dict) -> DisplayResult:
        emotion = raw.get("emotion", "unknown")
        confidence = float(raw.get("confidence", 0.0))
        style = style_for(emotion)
        return DisplayResult(
            transcript=raw.get("transcription", ""),
            emotion=emotion,
            confidence=confidence,
            emoji=style.emoji,
            color=style.color,
            label=style.label,
            confident=is_confident(confidence),
        )

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        message = str(exc)
        looks_like_ffmpeg = (
            isinstance(exc, FileNotFoundError)
            or "WinError 2" in message
            or "ffmpeg" in message.lower()
        )
        if looks_like_ffmpeg:
            return (
                "Couldn't read the audio — ffmpeg doesn't seem to be on your "
                "PATH. Install ffmpeg and restart the app, then try again."
            )
        return message