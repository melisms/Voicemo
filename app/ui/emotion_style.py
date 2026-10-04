"""Presentation styling for emotions — the UI's own layer.

The backend says *which* emotion was detected; how it *looks* (emoji, accent
colour, display word) is a UI decision and lives here, so both the file mode and
the live mode render emotions the same way from one place.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmotionStyle:
    label: str
    emoji: str
    color: str


@dataclass(frozen=True)
class DisplayResult:
    transcript: str
    emotion: str
    confidence: float
    emoji: str
    color: str
    label: str
    confident: bool = True


_STYLES: dict[str, EmotionStyle] = {
    "angry":     EmotionStyle("Angry",     "\U0001F620", "#D64545"),
    "disgusted": EmotionStyle("Disgusted", "\U0001F922", "#5E8C3E"),
    "fearful":   EmotionStyle("Fearful",   "\U0001F628", "#6B5BD2"),
    "happy":     EmotionStyle("Happy",     "\U0001F60A", "#C98A00"),
    "neutral":   EmotionStyle("Neutral",   "\U0001F610", "#6B7280"),
    "sad":       EmotionStyle("Sad",       "\U0001F622", "#3B74C4"),
    "surprised": EmotionStyle("Surprised", "\U0001F62E", "#C14D9E"),
    "other":     EmotionStyle("Other",     "\U0001F914", "#6B7280"),
    "unknown":   EmotionStyle("Unknown",   "\u2753",     "#9AA2AE"),
}

_FALLBACK = EmotionStyle("Unknown", "\u2753", "#9AA2AE")


def style_for(emotion: str) -> EmotionStyle:
    return _STYLES.get((emotion or "").lower(), _FALLBACK)