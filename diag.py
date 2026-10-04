"""Quick backend diagnostic — bypasses the UI entirely.

Runs the backend pipeline directly on every audio file in tests/audio and
prints the emotion, confidence and transcript for each.

How to read it:
  * Two DIFFERENT files print the SAME emotion AND the SAME transcript
      -> the problem is audio decoding / the backend, not the UI.
  * They print DIFFERENT results here, but the app still shows a stale one
      -> the problem is in the UI.

Run from the project root:   python diag.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.inference.pipeline import VoicemoPipeline

AUDIO_DIR = ROOT / "tests" / "audio"
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def main() -> None:
    files = sorted(p for p in AUDIO_DIR.iterdir() if p.suffix.lower() in AUDIO_EXTS)
    if not files:
        print(f"No audio files found in {AUDIO_DIR}")
        return

    print("Loading models (first run may download them)...\n")
    pipe = VoicemoPipeline()

    for p in files:
        try:
            r = pipe.process(str(p))
            print(f"{p.name}")
            print(f"   emotion   : {r['emotion']}  ({r['confidence']:.2f})")
            print(f"   transcript: {r['transcription'][:80]!r}\n")
        except Exception as exc:  # noqa: BLE001
            print(f"{p.name}  -> ERROR: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()