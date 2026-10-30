from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / "tokenhg.txt"
LOG_DIR = ROOT / "logs"
LOG_PATH = LOG_DIR / "download_models.log"


def models_root() -> Path:
    override = os.environ.get("WHISPERSCRIBE_MODELS")
    return Path(override) if override else ROOT / "models"


MODELS_ROOT = models_root()
os.environ["HF_HOME"] = str(MODELS_ROOT / "hf")
os.environ["HF_HUB_CACHE"] = str(MODELS_ROOT / "hf" / "hub")

COMMUNITY_MODEL = "pyannote/speaker-diarization-community-1"
COMMUNITY_URL = "https://huggingface.co/pyannote/speaker-diarization-community-1"


def log(message: str) -> None:
    line = f"[{datetime.now():%H:%M:%S}] {message}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def read_token() -> str:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN") or ""
    if not token and TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        import getpass

        token = getpass.getpass("Hugging Face read token (hf_...): ").strip()
    if token:
        os.environ["HF_TOKEN"] = token
    return token


def human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def folder_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def download_whisper() -> bool:
    root = models_root()
    local = root / "large-v3"
    if (local / "model.bin").exists():
        log(f"Local large-v3 already present: {local}")
        return True

    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from huggingface_hub import snapshot_download

    local.mkdir(parents=True, exist_ok=True)
    log(f"Whisper large-v3 -> {local}")
    log("About 3.1 GB. Downloads resume if interrupted; progress bars below.")
    started = time.time()
    try:
        snapshot_download(
            repo_id="Systran/faster-whisper-large-v3",
            local_dir=str(local),
            allow_patterns=[
                "config.json",
                "preprocessor_config.json",
                "tokenizer.json",
                "vocabulary.json",
                "model.bin",
            ],
        )
    except Exception as error:  # noqa: BLE001 - report and let the user retry
        log(f"Whisper download failed: {error}")
        return False

    if not (local / "model.bin").exists():
        log("Whisper download finished but model.bin is missing.")
        return False

    log(f"Whisper ready in {time.time() - started:.1f}s")
    log(f"models folder is now {human(folder_size(root))}")
    return True


def download_diarization() -> bool:
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        log("No Hugging Face token; skipping diarization.")
        return False

    os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "0")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from huggingface_hub.errors import GatedRepoError
    from pyannote.audio import Pipeline

    for attempt in range(1, 4):
        log(f"Diarization community-1 (attempt {attempt}/3)")
        try:
            Pipeline.from_pretrained(COMMUNITY_MODEL, token=token)
            log("Diarization models ready")
            return True
        except GatedRepoError:
            log("ACCESS DENIED: this model is gated.")
            log(f"Open {COMMUNITY_URL} while logged in as the token owner and click Agree.")
            if not sys.stdin.isatty():
                log("Not an interactive terminal; stopping diarization.")
                return False
            try:
                input("Accepted the terms? Press Enter to retry (Ctrl+C to abort)... ")
            except (EOFError, KeyboardInterrupt):
                log("Aborted by user.")
                return False
        except Exception as error:  # noqa: BLE001 - show the real reason
            log(f"Diarization failed: {error}")
            return False
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Whisper and diarization models.")
    parser.add_argument("--skip-whisper", action="store_true")
    parser.add_argument("--skip-diarization", action="store_true")
    args = parser.parse_args()

    log("Whisper Scribe model downloader")
    token = read_token()
    if token:
        try:
            from huggingface_hub import whoami

            log(f"Hugging Face user: {whoami().get('name', 'unknown')}")
        except Exception as error:  # noqa: BLE001
            log(f"Token check failed: {error}")
    else:
        log("No token found. Whisper can still download; diarization will be skipped.")

    ok = True
    if not args.skip_whisper:
        ok = download_whisper() and ok
    if not args.skip_diarization:
        ok = download_diarization() and ok

    log("Done." if ok else "Finished with errors - see the log above.")
    log(f"Log file: {LOG_PATH}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
