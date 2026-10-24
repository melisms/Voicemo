# Voicemo

**A local-first desktop accessibility app for more inclusive online meetings.**

Voicemo helps deaf and hard-of-hearing people follow online meetings by providing speech recognition and audio emotion analysis — even when their camera is turned off.

Built with Python and PySide6, Voicemo is designed to process audio locally, making accessibility support more privacy-conscious while displaying speech and emotional cues through a desktop interface.

## ✨ Key Features

- **Speech Recognition:** Transcribes spoken content in Turkish and English using OpenAI Whisper.
- **Audio Emotion Analysis:** Uses `emotion2vec` to identify emotional cues in audio.
- **Visual Emotion Indicators:** Presents detected emotional cues through emojis for quick, accessible interpretation.
- **Local-First Processing:** Designed to run speech and emotion analysis locally instead of relying on a remote inference service.
- **Desktop Interface:** Built with PySide6 for a native Python desktop experience.
- **Meeting Accessibility:** Supports users who need additional visual cues while participating in online meetings without turning on their cameras.
- **Cross-Platform Audio Support:** Explores system-audio capture on Windows and macOS, with platform-specific audio configuration where necessary.

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Language | Python |
| Desktop UI | PySide6 |
| Speech Recognition | OpenAI Whisper |
| Emotion Recognition | FunASR, emotion2vec |
| Inference | PyTorch, ONNX Runtime |
| Audio Processing | SoundDevice, SoundFile, NumPy |
| Testing | pytest, pytest-qt |

## 🧠 How It Works

1. **Audio Capture:** Receives audio from a supported audio input or system-audio capture setup.
2. **Speech Recognition:** Uses Whisper to transcribe spoken content in Turkish or English.
3. **Emotion Analysis:** Analyzes audio segments with an emotion recognition model.
4. **Visual Feedback:** Presents recognized speech and detected emotional cues in the desktop interface.

The speech and emotion analysis components serve complementary purposes: transcription helps users follow *what is being said*, while emotion analysis provides additional context about *how it may sound*.

> Emotion recognition is an estimate based on audio patterns, not a definitive measurement of a speaker's feelings.

## 🏗️ Architecture

Voicemo separates its desktop interface, audio capture, speech recognition, and emotion analysis into distinct components. This structure helps keep the application maintainable and makes individual components easier to test and improve.

- **Presentation Layer:** Desktop interface built with PySide6.
- **Audio Layer:** Audio input and system-audio capture.
- **Speech Layer:** Whisper-based transcription.
- **Emotion Layer:** `emotion2vec`-based audio emotion analysis.
- **Testing Layer:** Automated tests using pytest and pytest-qt.

## 🚀 Getting Started

### Prerequisites

- Python 3.12
- Git
- A supported audio input or system-audio capture configuration
- Additional platform-specific audio setup, if required

### Installation

Clone the repository:

```bash
git clone https://github.com/melisms/Voicemo.git
cd Voicemo
```

Create and activate a virtual environment:

**macOS / Linux**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

**Windows**

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the project's dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the application using the project's configured entry point.

> **Note:** Audio capture setup depends on your operating system. On macOS, a virtual audio device such as BlackHole may be required to capture system audio. Windows may require a compatible loopback or audio input configuration. Check the repository for the latest setup instructions before running the application.

## 🧪 Testing

Run the automated tests with:

```bash
python -m pytest
```

The project uses pytest and pytest-qt to support testing of application components.

## 🔒 Privacy and Accessibility

Voicemo is designed around local-first audio processing to reduce reliance on external services. Audio capture permissions, model behavior, and the actual processing path depend on the current implementation and configuration.

The project aims to make online meetings more accessible by providing visual information that complements existing meeting interfaces. It is intended as an assistive tool rather than a replacement for professional interpretation, captions, or other accessibility services.

## 🗺️ Roadmap

Potential areas for continued development include:

- Improving speech recognition and emotion-analysis accuracy.
- Enhancing the desktop interface and accessibility options.
- Expanding audio-device compatibility and simplifying setup.
- Increasing automated test coverage.
- Improving performance and resource usage during real-time processing.

## 👩‍💻 About This Project

Voicemo is a Python desktop application exploring the intersection of **accessibility, speech recognition, audio emotion analysis, and privacy-conscious AI**.

It combines AI inference with desktop application development to address a practical challenge: making online conversations easier to follow for people who benefit from visual speech and emotion cues.

## 📄 License

See the repository's `LICENSE` file for licensing terms.
