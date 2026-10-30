from __future__ import annotations

from pathlib import Path

from app.paths import data_dir

VOICEPRINTS_DIR = data_dir() / "voiceprints"


def available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("pyannote.audio") is not None
    except Exception:  # noqa: BLE001 - optional dependency probe
        return False


def voiceprint_path(speaker_id: int) -> Path:
    VOICEPRINTS_DIR.mkdir(parents=True, exist_ok=True)
    return VOICEPRINTS_DIR / f"speaker_{speaker_id}.npy"


def enroll(speaker_id: int, samples: list[Path]) -> Path:
    raise RuntimeError(
        "Voice enrollment is not implemented yet. It will embed the script reading with "
        "an ECAPA/WeSpeaker model and store a local .npy voiceprint."
    )


def match(turns: list, voiceprints: dict[int, Path], threshold: float = 0.72) -> dict[str, int]:
    return {}


def display_label(label: str) -> str:
    return label.replace("SPEAKER_", "Speaker ")
