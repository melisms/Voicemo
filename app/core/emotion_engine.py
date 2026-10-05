from collections import deque


class EmotionEngine:
    """
    Stabilizes emotion predictions over multiple audio segments.
    """

    def __init__(
        self,
        window_size: int = 5,
        confidence_threshold: float = 0.60,
    ):
        self.window_size = window_size
        self.confidence_threshold = confidence_threshold

        self.history = deque(maxlen=window_size)

    def update(
        self,
        emotion: str,
        confidence: float,
    ) -> dict:

        # Unknown is not added as an emotional state.
        if emotion == "unknown":
            return {
                "emotion": "unknown",
                "confidence": confidence,
            }

        # Low-confidence predictions are ignored.
        if confidence < self.confidence_threshold:
            return {
                "emotion": "unknown",
                "confidence": confidence,
            }

        self.history.append({
            "emotion": emotion,
            "confidence": confidence,
        })

        if not self.history:
            return {
                "emotion": "unknown",
                "confidence": 0.0,
            }
        
        scores = {}

        for item in self.history:
            emotion_name = item["emotion"]
            score = item["confidence"]

            scores[emotion_name] = (
                scores.get(emotion_name, 0.0)
                + score
            )

        final_emotion = max(
            scores,
            key=scores.get,
        )

        total = sum(scores.values())

        final_confidence = (
            scores[final_emotion] / total
            if total > 0
            else 0.0
        )

        return {
            "emotion": final_emotion,
            "confidence": final_confidence,
        }

    def reset(self):
        self.history.clear()