"""Live audio capture and per-window analysis for the meeting mode.

Cross-platform capture, chosen by source and OS:

  * "mic"            — default microphone (sounddevice), on Windows and macOS.
  * "system" on Win  — WASAPI loopback (PyAudioWPatch): captures what you hear.
  * "system" on mac  — a virtual loopback input device (e.g. BlackHole) read via
                       sounddevice; macOS can't capture system output directly,
                       so the user installs BlackHole and routes audio to it.

PyAudioWPatch is Windows-only and is imported only on Windows, so nothing breaks
on macOS. Each window is analysed without ffmpeg: Whisper is fed a numpy array
directly, and emotion2vec reads a short temp WAV via torchaudio.
"""

from __future__ import annotations

import os
import sys
import tempfile

import numpy as np
from PySide6.QtCore import QThread, Signal

TARGET_SR = 16000

# Names that usually mean "captures what you hear" (virtual loopback devices).
_LOOPBACK_HINTS = (
    "blackhole", "loopback", "soundflower", "stereo mix",
    "vb-audio", "vb-cable", "voicemeeter",
)


def resample_to_16k(mono: np.ndarray, sr: int) -> np.ndarray:
    """Linear resample a mono signal to 16 kHz (good enough for speech)."""
    mono = mono.astype(np.float32)
    if sr == TARGET_SR or len(mono) == 0:
        return mono
    n = int(round(len(mono) * TARGET_SR / sr))
    x_old = np.linspace(0.0, 1.0, len(mono), endpoint=False)
    x_new = np.linspace(0.0, 1.0, n, endpoint=False)
    return np.interp(x_new, x_old, mono).astype(np.float32)


def _is_loopback_name(name: str) -> bool:
    name = (name or "").lower()
    return any(hint in name for hint in _LOOPBACK_HINTS)


def _find_loopback_device():
    """Index of an input device that looks like a virtual loopback, or None."""
    import sounddevice as sd

    for index, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0 and _is_loopback_name(dev["name"]):
            return index
    return None


class LiveCapture(QThread):
    """Captures audio in fixed windows and emits them as 16 kHz mono arrays."""

    window_ready = Signal(object)  # np.ndarray, 16k mono float32
    error = Signal(str)

    def __init__(self, source: str = "mic", window_seconds: float = 4.0) -> None:
        super().__init__()
        self.source = source
        self.window_seconds = float(window_seconds)
        self._running = False

    @staticmethod
    def mic_available() -> bool:
        try:
            import sounddevice  # noqa: F401
            return True
        except Exception:
            return False

    @staticmethod
    def system_available() -> bool:
        if sys.platform == "win32":
            try:
                import pyaudiowpatch  # noqa: F401
                return True
            except Exception:
                return False
        # macOS / Linux: need a virtual loopback input device (e.g. BlackHole)
        try:
            return _find_loopback_device() is not None
        except Exception:
            return False

    def stop(self) -> None:
        self._running = False
        self.wait(4000)

    def run(self) -> None:
        self._running = True
        try:
            if self.source == "system":
                if sys.platform == "win32":
                    self._run_system_windows()
                else:
                    self._run_system_device()
            else:
                self._run_mic()
        except Exception as exc:  # noqa: BLE001 — reported to the UI
            self.error.emit(f"{type(exc).__name__}: {exc}")

    # ---- microphone (sounddevice, all platforms) ----
    def _run_mic(self) -> None:
        import sounddevice as sd

        self._stream_from_device(sd, device=None, sr=TARGET_SR, channels=1)

    # ---- system audio on macOS/Linux: a virtual loopback input device ----
    def _run_system_device(self) -> None:
        import sounddevice as sd

        device = _find_loopback_device()
        if device is None:
            self.error.emit(
                "No virtual audio device found. On macOS, install BlackHole "
                "(brew install blackhole-2ch) and route system / meeting audio "
                "to it, then pick it up here."
            )
            return
        info = sd.query_devices(device)
        sr = int(info["default_samplerate"]) or 48000
        channels = min(2, int(info["max_input_channels"])) or 1
        self._stream_from_device(sd, device=device, sr=sr, channels=channels)

    def _stream_from_device(self, sd, device, sr: int, channels: int) -> None:
        block = max(1, int(sr * 0.1))
        win = int(sr * self.window_seconds)
        buf = np.empty(0, dtype=np.float32)
        with sd.InputStream(samplerate=sr, device=device, channels=channels,
                            dtype="float32", blocksize=block) as stream:
            while self._running:
                data, _ = stream.read(block)
                if data.ndim > 1 and data.shape[1] > 1:
                    mono = data.mean(axis=1)
                else:
                    mono = data.reshape(-1)
                buf = np.concatenate([buf, mono])
                while len(buf) >= win:
                    self.window_ready.emit(resample_to_16k(buf[:win].copy(), sr))
                    buf = buf[win:]

    # ---- system audio on Windows: WASAPI loopback (PyAudioWPatch) ----
    def _run_system_windows(self) -> None:
        import pyaudiowpatch as pyaudio

        with pyaudio.PyAudio() as p:
            lb = p.get_default_wasapi_loopback()
            if lb is None:
                self.error.emit("No WASAPI loopback device found.")
                return

            sr = int(lb["defaultSampleRate"])
            ch = int(lb["maxInputChannels"]) or 2
            stream = p.open(format=pyaudio.paInt16, channels=ch, rate=sr,
                            input=True, input_device_index=lb["index"],
                            frames_per_buffer=1024)

            win = int(sr * self.window_seconds)
            raw = bytearray()
            samples = 0
            try:
                while self._running:
                    raw.extend(stream.read(1024, exception_on_overflow=False))
                    samples += 1024
                    if samples >= win:
                        audio = (np.frombuffer(bytes(raw), dtype=np.int16)
                                 .astype(np.float32) / 32768.0)
                        if ch > 1:
                            audio = audio.reshape(-1, ch).mean(axis=1)
                        self.window_ready.emit(resample_to_16k(audio, sr))
                        raw = bytearray()
                        samples = 0
            finally:
                stream.stop_stream()
                stream.close()


class LiveAnalyzer:
    """Loads the models once and analyses one window without touching ffmpeg."""

    _whisper = None
    _emotion = None

    @classmethod
    def _load(cls) -> None:
        if cls._whisper is None:
            from app.models.whisper_model import WhisperModel
            cls._whisper = WhisperModel()
        if cls._emotion is None:
            from app.models.emotion2vec_model import Emotion2VecModel
            cls._emotion = Emotion2VecModel()

    @classmethod
    def analyze(cls, audio: np.ndarray) -> dict:
        cls._load()

        # Whisper accepts a numpy array directly — no file, so no ffmpeg.
        transcript = cls._whisper.transcribe(audio)

        # emotion2vec wants a path; a temp WAV is read via torchaudio (no ffmpeg).
        import soundfile as sf

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        try:
            sf.write(tmp.name, audio, TARGET_SR)
            pred = cls._emotion.predict(tmp.name)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

        return {
            "transcription": transcript,
            "emotion": pred["emotion"],
            "confidence": float(pred["confidence"]),
        }


class LiveWindowWorker(QThread):
    """Analyses a single captured window off the UI thread."""

    done = Signal(object)   # dict: transcription, emotion, confidence
    failed = Signal(str)

    def __init__(self, audio: np.ndarray) -> None:
        super().__init__()
        self._audio = audio

    def run(self) -> None:
        try:
            result = LiveAnalyzer.analyze(self._audio)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.done.emit(result)