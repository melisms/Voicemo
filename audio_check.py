"""Audio capture check — can your machine capture the mic AND the meeting?

Run from the project root:   python audio_check.py

It does three things:
  1. Lists your audio devices (so we can see which one is the meeting / system output).
  2. Records ~5s from your MICROPHONE and runs it through the pipeline.
  3. Records ~5s of SYSTEM / MEETING audio (what you hear) via WASAPI loopback
     and runs it through the pipeline.

Before running, for step 3 have sound playing — a YouTube video, or a Meet with
someone talking — so there is something to capture.

  * Mic capture uses `sounddevice` (already installed).
  * System / meeting capture uses `PyAudioWPatch`. Install it first:
        pip install PyAudioWPatch
    (plain sounddevice can't reliably capture system output on Windows.)
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

TARGET_SR = 16000
SECONDS = 5

_PIPE = None


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0


def to_16k_mono(audio: np.ndarray, sr: int) -> np.ndarray:
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float32)
    if sr != TARGET_SR and len(audio):
        n = int(round(len(audio) * TARGET_SR / sr))
        x_old = np.linspace(0, 1, len(audio), endpoint=False)
        x_new = np.linspace(0, 1, n, endpoint=False)
        audio = np.interp(x_new, x_old, audio).astype(np.float32)
    return audio


def save_wav(path: Path, audio16k: np.ndarray) -> None:
    import soundfile as sf

    sf.write(str(path), audio16k, TARGET_SR)


def run_pipeline(path: Path) -> None:
    global _PIPE
    try:
        if _PIPE is None:
            from app.inference.pipeline import VoicemoPipeline

            _PIPE = VoicemoPipeline()
        r = _PIPE.process(str(path))
        print(f"   -> emotion: {r['emotion']} ({r['confidence']:.2f}) "
              f"| transcript: {r['transcription'][:60]!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"   -> pipeline error: {type(exc).__name__}: {exc}")


def list_devices() -> None:
    import sounddevice as sd

    print("=== AUDIO DEVICES (sounddevice) ===")
    print(sd.query_devices())
    print()


def test_mic() -> None:
    import sounddevice as sd

    print(f"=== MIC: recording {SECONDS}s — please speak ===")
    try:
        audio = sd.rec(int(SECONDS * TARGET_SR), samplerate=TARGET_SR,
                       channels=1, dtype="float32")
        sd.wait()
    except Exception as exc:  # noqa: BLE001
        print(f"MIC ERROR: {type(exc).__name__}: {exc}\n")
        return
    audio = audio.reshape(-1)
    print(f"captured {len(audio)} samples, level(RMS)={rms(audio):.4f}")
    if rms(audio) < 1e-4:
        print("   warning: level ~0 — mic may be muted or blocked by Windows privacy settings")
    out = ROOT / "mic_test.wav"
    save_wav(out, audio)
    print(f"saved {out.name}")
    run_pipeline(out)
    print()


def test_loopback() -> None:
    print(f"=== SYSTEM / MEETING: recording {SECONDS}s — make sure audio is playing ===")
    try:
        import pyaudiowpatch as pyaudio
    except ImportError:
        print("PyAudioWPatch not installed. Install with:  pip install PyAudioWPatch")
        print("(needed to capture the meeting / system audio)\n")
        return

    try:
        with pyaudio.PyAudio() as p:
            lb = p.get_default_wasapi_loopback()
            if lb is None:
                print("No default WASAPI loopback device found.\n")
                return
            sr = int(lb["defaultSampleRate"])
            ch = int(lb["maxInputChannels"]) or 2
            print(f"loopback device: {lb['name']}  (sr={sr}, ch={ch})")

            stream = p.open(format=pyaudio.paInt16, channels=ch, rate=sr,
                            input=True, input_device_index=lb["index"],
                            frames_per_buffer=1024)
            frames = [stream.read(1024, exception_on_overflow=False)
                      for _ in range(int(sr / 1024 * SECONDS))]
            stream.stop_stream()
            stream.close()
    except Exception as exc:  # noqa: BLE001
        print(f"LOOPBACK ERROR: {type(exc).__name__}: {exc}\n")
        return

    raw = b"".join(frames)
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        audio = audio.reshape(-1, ch)
    audio16k = to_16k_mono(audio, sr)
    print(f"captured {len(audio16k)} samples @16k, level(RMS)={rms(audio16k):.4f}")
    if rms(audio16k) < 1e-4:
        print("   warning: level ~0 — nothing was playing, or the wrong device was picked")
    out = ROOT / "system_test.wav"
    save_wav(out, audio16k)
    print(f"saved {out.name}")
    run_pipeline(out)
    print()


def main() -> None:
    list_devices()
    test_mic()
    test_loopback()
    print("Done. Open mic_test.wav and system_test.wav and listen — "
          "they should contain the sound you expected.")


if __name__ == "__main__":
    main()