# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = [
    ("app/assets", "app/assets"),
    ("app/db/schema.sql", "app/db"),
]
binaries = []
hiddenimports = [
    "pyannote.audio",
    "pyannote.audio.pipelines.speaker_diarization",
    "pyannote.audio.core.io",
    "pyannote.audio.core.inference",
    "faster_whisper",
    "ctranslate2",
    "torchcodec",
    "torchaudio",
    "soundfile",
    "av",
    "omegaconf",
    "matplotlib",
    "lightning",
    "pytorch_lightning",
    "torchmetrics",
    "speechbrain",
    "torch_audiomentations",
    "pytorch_metric_learning",
    "asteroid_filterbanks",
    "safetensors",
    "tokenizers",
    "yaml",
    "tqdm",
    "rich",
]

PACKAGES = [
    "pyannote.audio",
    "pyannote.core",
    "pyannote.pipeline",
    "pyannote.database",
    "pyannote.metrics",
    "pyannoteai",
    "faster_whisper",
    "ctranslate2",
    "torchcodec",
    "soundfile",
    "av",
    "huggingface_hub",
    "omegaconf",
    "lightning",
    "pytorch_lightning",
    "torchmetrics",
    "speechbrain",
    "torch_audiomentations",
    "pytorch_metric_learning",
    "asteroid_filterbanks",
    "safetensors",
    "tokenizers",
]

for package in PACKAGES:
    try:
        package_datas, package_binaries, package_hidden = collect_all(package)
    except Exception as error:  # noqa: BLE001 - optional packages may be absent
        print(f"skip collect_all({package}): {error}")
        continue
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "pytest",
        "ruff",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.QtQuick3D",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WhisperScribe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="app/assets/app.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="WhisperScribe",
)
