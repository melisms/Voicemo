from pathlib import Path
import audioop
import wave


class VoiceActivityDetector:
    """
    Returns False for silence or very low-energy audio.
    """

    def __init__(self, threshold: int = 50):
        self.threshold = threshold

    def has_speech(self, audio_path: str | Path) -> bool:
        try:
            with wave.open(str(audio_path), "rb") as wf:
                frames = wf.readframes(wf.getnframes())

                if not frames:
                    return False

                rms = audioop.rms(
                    frames,
                    wf.getsampwidth(),
                )

                return rms >= self.threshold

        except Exception:
            return False