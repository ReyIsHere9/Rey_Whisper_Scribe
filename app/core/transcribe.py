from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Protocol

from app.core.models import JobCancelled, JobConfig, Segment
from app.core.normalize_fa import normalize_persian
from app.paths import models_dir

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


class EngineUnavailable(RuntimeError):
    pass


MODEL_ALIASES = {"large-v3": "large-v3", "turbo": "large-v3-turbo"}
AUTO_LANGUAGES = {"auto", "mixed"}
PERSIAN_PROMPT = (
    "این یک رونویسی فارسی است. متن را با املای درست و علائم نگارشی فارسی بنویس. "
    "کلمات و اصطلاحات انگلیسی را به انگلیسی حفظ کن."
)


def engine_available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def _cuda_available() -> bool:
    try:
        import torch  # noqa: F401, I001 - load CUDA/cuDNN DLLs before ctranslate2
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:  # noqa: BLE001 - optional dependency probe
        return False


class TranscriptionEngine(Protocol):
    def transcribe(
        self,
        audio_path: Path,
        config: JobConfig,
        progress=None,
        should_stop=None,
    ) -> list[Segment]: ...


def _model_source(model_name: str) -> str:
    local = models_dir() / model_name
    if (local / "model.bin").exists():
        return str(local)
    return model_name


def _load_audio(path: Path):
    """Decode to mono float32 at 16 kHz without relying on PyAV's unstable API."""
    import numpy as np
    import soundfile as sf

    data, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1) if data.shape[1] > 1 else data[:, 0]
    if sample_rate != 16000:
        from math import gcd

        from scipy.signal import resample_poly

        factor = gcd(16000, sample_rate)
        mono = resample_poly(mono, 16000 // factor, sample_rate // factor)
    return np.ascontiguousarray(mono, dtype=np.float32)


class FasterWhisperEngine:
    def transcribe(
        self,
        audio_path: Path,
        config: JobConfig,
        progress=None,
        should_stop=None,
    ) -> list[Segment]:
        if not engine_available():
            raise EngineUnavailable(
                "faster-whisper is not installed. Run: pip install -r requirements-ml.txt"
            )

        from faster_whisper import WhisperModel

        device = "cuda" if (config.device == "auto" and _cuda_available()) else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        model_name = MODEL_ALIASES.get(config.model, config.model)

        model = WhisperModel(
            _model_source(model_name),
            device=device,
            compute_type=compute_type,
            download_root=str(models_dir()),
        )
        if progress:
            progress(0.0, 0)

        audio = _load_audio(audio_path)
        language = None if config.language in AUTO_LANGUAGES else config.language
        initial_prompt = (
            PERSIAN_PROMPT if config.language in {"fa", "mixed"} else None
        )
        raw_segments, info = model.transcribe(
            audio,
            language=language,
            task="transcribe",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 300},
            condition_on_previous_text=True,
            repetition_penalty=1.05,
            initial_prompt=initial_prompt,
            word_timestamps=True,
        )

        duration = float(getattr(info, "duration", 0) or 0)
        if duration <= 0:
            duration = max(1.0, len(audio) / 16000)

        result: list[Segment] = []
        for item in raw_segments:
            if should_stop and should_stop():
                raise JobCancelled("Transcription cancelled")
            text = normalize_persian(item.text)
            if not text:
                continue
            words = [
                {
                    "start_ms": int(word.start * 1000),
                    "end_ms": int(word.end * 1000),
                    "word": word.word,
                    "probability": word.probability,
                }
                for word in (item.words or [])
            ]
            result.append(
                Segment(
                    start_ms=int(item.start * 1000),
                    end_ms=int(item.end * 1000),
                    text=text,
                    confidence=getattr(item, "avg_logprob", None),
                    words=words,
                )
            )
            if progress:
                progress(min(1.0, item.end / duration), len(result))
        return result
