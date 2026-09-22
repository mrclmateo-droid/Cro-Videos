from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)


@dataclass
class TranscriptionResult:
    language: str
    segments: list[Segment]


class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: str, language: str | None = None) -> TranscriptionResult: ...
