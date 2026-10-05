from funasr import AutoModel
from pathlib import Path
import wave
import audioop

class Emotion2VecModel:
    def __init__(self, model_id: str = "iic/emotion2vec_plus_large"):
        self.model = AutoModel(
            model=model_id,      # finetuned 9-sınıf SER modeli
            hub="ms",
            disable_update=True,
        )
    # predict() ve _normalize_label() aynen kalıyor
    
    def predict(self, audio_path: str | Path) -> dict:
        
        if not self.has_speech(audio_path):
            return {
                "emotion": "unknown",
                "confidence": 1.0
            }
        
        result = self.model.generate(
            input=str(audio_path),  # Convert Path to str if necessary
            granularity="utterance",
            extract_embedding=False,
        )
        
        prediction = result[0]
        
        labels = prediction["labels"]
        scores = prediction["scores"]
        index =  max(range(len(scores)), key=lambda i: scores[i])
        
        emotion = self._normalize_label(labels[index])
        confidence = float(scores[index])
        
        if confidence < 0.60:
            emotion = "unknown"
        
        return {
            "emotion": emotion,
            "confidence": confidence
        }
        
    @staticmethod
    def has_speech(audio_path: str | Path, threshold: int = 50) -> bool:
        try:
            with wave.open(str(audio_path), 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                if not frames:
                    return False
                rms_value = audioop.rms(
                    frames,
                    wf.getsampwidth()
                )
                print(f"RMS value: {rms_value}")
                return rms_value >= threshold
        except Exception:
            return False
    
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