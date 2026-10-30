from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from app.paths import exports_dir


def _safe(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "-", name).strip(" .-")
    return cleaned or "transcript"


def _short(ms: int) -> str:
    seconds = max(0, int(ms // 1000))
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _srt_time(ms: int) -> str:
    millis = max(0, int(ms))
    seconds, millis = divmod(millis, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def default_path(job) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    return exports_dir() / f"{_safe(job['title'])}-{stamp}.txt"


def export_transcript(job, segments, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()

    if suffix == ".srt":
        lines: list[str] = []
        for index, segment in enumerate(segments, start=1):
            lines.append(str(index))
            lines.append(
                f"{_srt_time(segment['start_ms'])} --> {_srt_time(segment['end_ms'])}"
            )
            speaker = segment["speaker_name"] or "Speaker"
            lines.append(f"{speaker}: {segment['text']}")
            lines.append("")
        target.write_text("\n".join(lines), encoding="utf-8")
    else:
        header = f"{job['title']}\n{'=' * len(job['title'])}\n\n"
        body = "\n".join(
            f"[{_short(segment['start_ms'])}] {segment['speaker_name'] or 'Speaker'}: "
            f"{segment['text']}"
            for segment in segments
        )
        target.write_text(header + body + "\n", encoding="utf-8")

    return target
