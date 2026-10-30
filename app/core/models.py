from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Language = Literal["fa", "en", "auto", "mixed"]
SpeakerScope = Literal["global", "job"]


class JobCancelled(RuntimeError):
    pass


@dataclass
class JobConfig:
    language: Language = "fa"
    model: str = "large-v3"
    diarize: bool = True
    expected_speakers: int = 0
    speaker_scope: SpeakerScope = "global"
    device: str = "auto"


@dataclass
class Segment:
    start_ms: int
    end_ms: int
    text: str
    speaker: str | None = None
    confidence: float | None = None
    words: list[dict] = field(default_factory=list)


@dataclass
class SpeakerTurn:
    start_ms: int
    end_ms: int
    label: str
