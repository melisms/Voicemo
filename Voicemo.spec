
# Voicemo.spec
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all

project_root = Path.cwd()

datas = [
    (str(project_root / "app" / "ui" / "theme.qss"), "app/ui"),
]
binaries = []
hiddenimports = [
    "funasr",
    "modelscope",
    "huggingface_hub",
    "whisper",
    "torch",
    "torchaudio",
    "soundfile",
    "sounddevice",
    "scipy",
    "sklearn",
    "librosa",
    "yaml",
]

# Collect package resources and dynamic imports.
packages = [
    "funasr",
    "modelscope",
    "huggingface_hub",
    "whisper",
    "torchaudio",
    "soundfile",
    "sounddevice",
]

if sys.platform == "win32":
    packages.append("pyaudiowpatch")
    hiddenimports.append("pyaudiowpatch")

for package in packages:
    try:
        package_datas, package_binaries, package_hiddenimports = (
            collect_all(package)
        )
        datas += package_datas
        binaries += package_binaries
        hiddenimports += package_hiddenimports
    except Exception as exc:
        print(f"Could not collect {package}: {exc}")
        raise

a = Analysis(
    ["app/main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Voicemo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Voicemo",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Voicemo.app",
        bundle_identifier="com.melisms.voicemo",
        info_plist={
            "NSMicrophoneUsageDescription": (
                "Voicemo needs microphone access to analyze speech "
                "during online meetings."
            ),
        },
    )
else:
    app = coll
