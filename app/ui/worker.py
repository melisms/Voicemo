"""Runs file analysis off the GUI thread — without ffmpeg.

The audio file is loaded into a numpy array with soundfile (no ffmpeg), then
analysed exactly like a live window: Whisper runs on the array directly, and
emotion2vec reads a short temp WAV via torchaudio. Each run carries a run_id so
only the latest result is shown. (This bypasses the backend's VoicemoPipeline,
whose path-based Whisper call is what needed ffmpeg.)
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.confidence import is_confident
from app.ui.emotion_style import DisplayResult, style_for
from app.ui.live import LiveAnalyzer, resample_to_16k


class AnalysisWorker(QThread):
    succeeded = Signal(int, object)   # run_id, DisplayResult
    failed = Signal(int, str)         # run_id, error message

    def __init__(self, run_id: int, audio_path: str | Path) -> None:
        super().__init__()
        self._run_id = run_id
        self._audio_path = str(audio_path)

    def run(self) -> None:
        try:
            audio = self._load_audio(self._audio_path)
            raw = LiveAnalyzer.analyze(audio)
            result = self._to_display(raw)
        except Exception as exc:  # noqa: BLE001 — surfaced to the UI
            self.failed.emit(self._run_id, self._friendly_error(exc))
        else:
            self.succeeded.emit(self._run_id, result)

    @staticmethod
    def _load_audio(path: str):
        """Load any WAV/FLAC/OGG (and MP3 on recent libsndfile) as 16 kHz mono."""
        import soundfile as sf

        audio, sr = sf.read(path, dtype="float32", always_2d=False)
        if getattr(audio, "ndim", 1) > 1:   # stereo -> mono
            audio = audio.mean(axis=1)
        return resample_to_16k(audio, sr)

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
        low = message.lower()
        if "format not recognised" in low or "error opening" in low:
            return ("Couldn't read this audio format. Try a WAV, FLAC or OGG "
                    "file (or convert it first).")
        return message