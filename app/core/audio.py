from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.paths import app_dir

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".ts"}

SUPPORTED_EXTS = AUDIO_EXTS | VIDEO_EXTS

_CREATE_NO_WINDOW = 0x08000000


def _tool(name: str) -> str | None:
    local = app_dir() / "ffmpeg" / f"{name}.exe"
    if local.exists():
        return str(local)
    return shutil.which(name)


def ffmpeg_path() -> str | None:
    return _tool("ffmpeg")


def ffprobe_path() -> str | None:
    return _tool("ffprobe")


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTS


def extract_audio(source: str | Path, destination: str | Path, sample_rate: int = 16000) -> Path:
    source = Path(source)
    destination = Path(destination)
    if not source.exists():
        raise FileNotFoundError(source)
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg was not found on PATH or in the app's ffmpeg folder."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-af",
        "loudnorm=I=-18:TP=-1.5:LRA=11",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr.strip()[-800:]}")
    return destination


def probe_duration_ms(path: str | Path, fallback: int = 0) -> int:
    probe = ffprobe_path()
    if not probe:
        return fallback
    command = [
        probe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
        check=False,
    )
    try:
        return int(float(result.stdout.strip()) * 1000)
    except (TypeError, ValueError):
        return fallback
