from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from app.core.audio import extract_audio, probe_duration_ms
from app.core.diarize import DiarizationUnavailable, diarize
from app.core.models import JobConfig
from app.core.pipeline import assign_speakers
from app.core.transcribe import EngineUnavailable, FasterWhisperEngine


def _clock(ms: int) -> str:
    seconds = max(0, ms // 1000)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the offline engine on one file.")
    parser.add_argument("file")
    parser.add_argument("--lang", default="fa", choices=["fa", "en", "auto"])
    parser.add_argument("--model", default="large-v3", choices=["large-v3", "turbo"])
    parser.add_argument("--speakers", type=int, default=0, help="0 skips diarization")
    parser.add_argument("--cpu", action="store_true", help="force CPU transcription")
    args = parser.parse_args()

    source = Path(args.file)
    if not source.exists():
        print(f"File not found: {source}")
        return 2

    config = JobConfig(
        language=args.lang,
        model=args.model,
        expected_speakers=max(1, args.speakers),
        diarize=args.speakers > 0,
        device="cpu" if args.cpu else "auto",
    )

    try:
        with tempfile.TemporaryDirectory(prefix="ws-smoke-") as tmp:
            print("extracting audio...")
            wav = extract_audio(source, Path(tmp) / "audio.wav")
            print(f"duration: {_clock(probe_duration_ms(wav))}")

            print("transcribing (first run downloads the model)...")
            segments = FasterWhisperEngine().transcribe(
                wav,
                config,
                progress=lambda ratio, count: print(
                    f"\r  {ratio * 100:5.1f}%  {count} segments",
                    end="",
                    flush=True,
                ),
            )
            print()

            turns = []
            if config.diarize:
                print("diarizing...")
                try:
                    turns = diarize(wav, config)
                    print(f"  {len(turns)} speaker turns")
                except DiarizationUnavailable as error:
                    print(f"  skipped: {error}")
            assign_speakers(segments, turns)

            print()
            for segment in segments:
                print(
                    f"[{_clock(segment.start_ms)}] "
                    f"{segment.speaker or 'Speaker'}: {segment.text}"
                )
    except EngineUnavailable as error:
        print(f"Engine not ready: {error}")
        return 1
    except Exception as error:  # noqa: BLE001 - surface the full failure in a dev tool
        print(f"Failed: {error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
