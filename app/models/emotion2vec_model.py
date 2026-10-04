from funasr import AutoModel
from pathlib import Path

class Emotion2VecModel:
    def __init__(self, model_id: str = "iic/emotion2vec_plus_large"):
        self.model = AutoModel(
            model=model_id,      # finetuned 9-sınıf SER modeli
            hub="ms",
            disable_update=True,
        )
    # predict() ve _normalize_label() aynen kalıyor
    
    def predict(self, audio_path: str | Path) -> dict:
        result = self.model.generate(
            input=str(audio_path),  # Convert Path to str if necessary
            granularity="utterance",
            extract_embedding=False,
        )
        
        prediction = result[0]
        
        labels = prediction["labels"]
        scores = prediction["scores"]
        index =  max(range(len(scores)), key=lambda i: scores[i])
        
        return {
            "emotion": self._normalize_label(labels[index]),
            "confidence": float(scores[index])
        }
    
    @staticmethod
    def _normalize_label(label: str) -> str:
        emotion=label.split("/")[-1]
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
        return mapping.get(emotion, "unknown")