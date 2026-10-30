from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "WhisperScribe"

PACKAGE_DIR = Path(__file__).resolve().parent
ROOT_DIR = PACKAGE_DIR.parent
ASSETS_DIR = PACKAGE_DIR / "assets"


def data_dir() -> Path:
    override = os.environ.get("WHISPERSCRIBE_DATA")
    path = Path(override) if override else ROOT_DIR / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "whisper_scribe.db"


def models_dir() -> Path:
    override = os.environ.get("WHISPERSCRIBE_MODELS")
    path = Path(override) if override else ROOT_DIR / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def hf_cache_dir() -> Path:
    return models_dir() / "hf"


os.environ["HF_HOME"] = str(hf_cache_dir())
os.environ["HF_HUB_CACHE"] = str(hf_cache_dir() / "hub")


def exports_dir() -> Path:
    path = data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def asset(name: str) -> Path:
    return ASSETS_DIR / name
