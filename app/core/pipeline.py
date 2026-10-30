from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.audio import extract_audio, probe_duration_ms
from app.core.diarize import DiarizationUnavailable, diarize
from app.core.models import JobCancelled, JobConfig, Segment, SpeakerTurn
from app.core.speakers import display_label
from app.core.transcribe import FasterWhisperEngine

Progress = Callable[[float, str, int], None]


def assign_speakers(segments: list[Segment], turns: list[SpeakerTurn]) -> None:
    if not turns:
        for segment in segments:
            segment.speaker = segment.speaker or "Speaker 1"
        return

    for segment in segments:
        best_label = None
        best_overlap = 0
        for turn in turns:
            overlap = min(segment.end_ms, turn.end_ms) - max(segment.start_ms, turn.start_ms)
            if overlap > best_overlap:
                best_overlap = overlap
                best_label = turn.label
        segment.speaker = display_label(best_label) if best_label else "Speaker 1"


def _ensure_speaker(db: Any, job_id: int, name: str, scope: str) -> int:
    existing = db.conn.execute(
        "SELECT id FROM speakers WHERE name = ? AND (job_id = ? OR is_global = 1)",
        (name, job_id),
    ).fetchone()
    if existing:
        return int(existing["id"])
    is_global = scope == "global"
    return db.add_speaker(None if is_global else job_id, name, is_global=is_global)


def run_job(
    db: Any,
    job_id: int,
    config: JobConfig | None = None,
    progress: Progress | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[Segment]:
    job = db.job(job_id)
    if job is None:
        raise ValueError(f"Unknown job {job_id}")
    source = Path(job["source_path"] or "")
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    def stage(ratio: float, key: str, count: int = 0) -> None:
        if progress:
            progress(max(0.0, min(1.0, ratio)), key, count)

    def check() -> None:
        if should_stop and should_stop():
            raise JobCancelled("Cancelled")

    cfg = config or JobConfig(
        language=job["language"],
        model=job["model"],
        diarize=bool(job["diarize"]),
        expected_speakers=job["expected_speakers"],
        speaker_scope=job["speaker_scope"],
    )

    db.set_job_status(job_id, "processing")

    with tempfile.TemporaryDirectory(prefix="whisper-scribe-") as tmp:
        stage(0.01, "extracting")
        check()
        wav_path = extract_audio(source, Path(tmp) / "audio.wav")

        stage(0.02, "loading")
        check()
        segments = FasterWhisperEngine().transcribe(
            wav_path,
            cfg,
            progress=lambda ratio, count: stage(0.03 + 0.72 * ratio, "transcribing", count),
            should_stop=should_stop,
        )
        check()

        stage(0.76, "saving")
        db.conn.execute("DELETE FROM segments WHERE job_id = ?", (job_id,))
        db.conn.executemany(
            "INSERT INTO segments(job_id, speaker_id, start_ms, end_ms, text, confidence) "
            "VALUES(?, NULL, ?, ?, ?, ?)",
            [
                (job_id, segment.start_ms, segment.end_ms, segment.text, segment.confidence)
                for segment in segments
            ],
        )
        db.conn.commit()
        segment_ids = [
            int(row["id"])
            for row in db.conn.execute(
                "SELECT id FROM segments WHERE job_id = ? ORDER BY id", (job_id,)
            )
        ]

        if cfg.diarize and segments:
            stage(0.80, "diarizing")
            check()
            turns: list[SpeakerTurn] = []
            try:
                turns = diarize(
                    wav_path,
                    cfg,
                    progress=lambda ratio: stage(0.80 + 0.15 * ratio, "diarizing"),
                    should_stop=should_stop,
                )
            except JobCancelled:
                raise
            except DiarizationUnavailable:
                turns = []
            except Exception:  # noqa: BLE001 - keep the unlabeled transcript
                turns = []

            check()
            if turns:
                stage(0.96, "saving")
                assign_speakers(segments, turns)
                cache: dict[str, int] = {}
                for segment_id, segment in zip(segment_ids, segments):
                    name = segment.speaker or "Speaker 1"
                    speaker_id = cache.get(name)
                    if speaker_id is None:
                        speaker_id = _ensure_speaker(db, job_id, name, cfg.speaker_scope)
                        cache[name] = speaker_id
                    db.conn.execute(
                        "UPDATE segments SET speaker_id = ? WHERE id = ?",
                        (speaker_id, segment_id),
                    )
                db.conn.commit()

        db.conn.execute(
            "UPDATE jobs SET status = 'transcribed', duration_ms = ? WHERE id = ?",
            (probe_duration_ms(wav_path), job_id),
        )
        db.conn.commit()

    stage(1.0, "done", len(segments))
    return segments
