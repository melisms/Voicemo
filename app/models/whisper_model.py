import numpy as np
import whisper


class WhisperModel:
    """Wrapper around the OpenAI Whisper speech recognition model."""

    LANGUAGES = {
        "en",
        "tr",
        # Add more language codes and names as needed
    }
    
    def __init__(self, model_name: str = "base"):
        self.model = whisper.load_model(model_name)

    def transcribe(self, audio: np.ndarray) -> str:
        
        if audio is None or len(audio) == 0:
            return ""
        
        audio = audio.astype(np.float32)
        rms = np.sqrt(np.mean(audio**2))
        print(f"RMS Whisper: {rms}")
        if rms < 0.001:
            return ""
        
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(
            audio,
            n_mels=self.model.dims.n_mels
        ).to(self.model.device)
        
        _, probs = self.model.detect_language(mel)

        language = max(probs, key=probs.get)
        
        if language not in self.LANGUAGES:
            return ""
        
        result = self.model.transcribe(
            audio,
            language=language,
            temperature=0,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            logprob_threshold=-1.0,
            compression_ratio_threshold=2.4, 
        )
        
        if result.get("no_speech_prob", 0) > 0.6:
            return ""
        
        return result["text"].strip()