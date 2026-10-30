from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from app.core.models import JobCancelled, JobConfig, SpeakerTurn
from app.paths import ROOT_DIR

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


class DiarizationUnavailable(RuntimeError):
    pass


def diarizer_available() -> bool:
    return importlib.util.find_spec("pyannote.audio") is not None


def hf_token() -> str | None:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if token:
        return token.strip()
    for name in ("tokenhg.txt", "hf_token.txt", ".hf_token"):
        path = ROOT_DIR / name
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
    return None


MODEL_ID = "pyannote/speaker-diarization-community-1"


def _load_pipeline(token: str | None):
    import huggingface_hub.constants as hf
    from pyannote.audio import Pipeline

    offline = hf.HF_HUB_OFFLINE
    hf.HF_HUB_OFFLINE = True
    try:
        return Pipeline.from_pretrained(MODEL_ID, token=token)
    except Exception:  # noqa: BLE001 - first run may still need a download
        hf.HF_HUB_OFFLINE = offline
        return Pipeline.from_pretrained(MODEL_ID, token=token)
    finally:
        hf.HF_HUB_OFFLINE = offline


def _load_waveform(path: Path) -> dict:
    """Decode ourselves and hand pyannote a tensor, avoiding torchcodec/FFmpeg DLLs."""
    import numpy as np
    import soundfile as sf
    import torch

    data, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    waveform = torch.from_numpy(np.ascontiguousarray(data.T))
    return {"waveform": waveform, "sample_rate": sample_rate}


def diarize(
    audio_path: Path,
    config: JobConfig,
    progress=None,
    should_stop=None,
) -> list[SpeakerTurn]:
    if should_stop and should_stop():
        raise JobCancelled("Diarization cancelled")
    if not diarizer_available():
        raise DiarizationUnavailable(
            "pyannote.audio is not installed. Run: pip install -r requirements-ml.txt"
        )
    token = hf_token()

    os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "0")

    try:
        pipeline = _load_pipeline(token)
    except Exception as error:
        raise DiarizationUnavailable(
            "Diarization models are not available locally. Accept the model terms at "
            "https://huggingface.co/pyannote/speaker-diarization-community-1 and put a "
            "read token in tokenhg.txt or set HF_TOKEN."
        ) from error

    try:
        import torch

        if torch.cuda.is_available():
            pipeline.to(torch.device("cuda"))
    except Exception:  # noqa: BLE001, S110 - GPU is optional
        pass

    if should_stop and should_stop():
        raise JobCancelled("Diarization cancelled")

    kwargs = {}
    if config.expected_speakers and config.expected_speakers > 0:
        kwargs["num_speakers"] = config.expected_speakers

    try:
        output = pipeline(_load_waveform(audio_path), **kwargs)
    except TypeError:
        output = pipeline(_load_waveform(audio_path))

    annotation = getattr(output, "speaker_diarization", output)
    if hasattr(annotation, "itertracks"):
        pairs = (
            (turn, label)
            for turn, _track, label in annotation.itertracks(yield_label=True)
        )
    else:
        pairs = annotation

    turns: list[SpeakerTurn] = []
    for turn, label in pairs:
        turns.append(
            SpeakerTurn(
                start_ms=int(turn.start * 1000),
                end_ms=int(turn.end * 1000),
                label=str(label),
            )
        )
    turns.sort(key=lambda t: t.start_ms)
    if progress:
        progress(1.0)
    return turns
