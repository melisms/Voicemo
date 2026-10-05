from funasr import AutoModel
from pathlib import Path

from app.audio.vad import VoiceActivityDetector


class Emotion2VecModel:
    def __init__(
        self,
        model_id: str = "iic/emotion2vec_plus_large",
        vad_threshold: int = 50,
    ):
        self.model = AutoModel(
            model=model_id,
            hub="ms",
            disable_update=True,
        )

        self.vad = VoiceActivityDetector(
            threshold=vad_threshold
        )

    def predict(self, audio_path: str | Path) -> dict:

        if not self.vad.has_speech(audio_path):
            return {
                "emotion": "unknown",
                "confidence": 1.0,
            }

        result = self.model.generate(
            input=str(audio_path),
            granularity="utterance",
            extract_embedding=False,
        )

        prediction = result[0]

        labels = prediction["labels"]
        scores = prediction["scores"]

        index = max(
            range(len(scores)),
            key=lambda i: scores[i],
        )

        emotion = self._normalize_label(
            labels[index]
        )

        confidence = float(
            scores[index]
        )

        return {
            "emotion": emotion,
            "confidence": confidence,
        }

    @staticmethod
    def _normalize_label(label: str) -> str:
        emotion = label.split("/")[-1]

        mapping = {
            "angry": "angry",
            "disgusted": "disgusted",
            "fearful": "fearful",
            "happy": "happy",
            "neutral": "neutral",
            "other": "other",
            "sad": "sad",
            "surprised": "surprised",
            "<unk>": "unknown",
        }

        return mapping.get(
            emotion,
            "unknown",
        )