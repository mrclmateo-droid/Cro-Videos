import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

HEX = r"^#[0-9A-Fa-f]{6}$"


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- proyectos / videos ----------
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectOut(ORM):
    id: uuid.UUID
    name: str
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class VideoOut(ORM):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    size: int | None
    duration: float | None
    width: int | None
    height: int | None
    fps: float | None
    upload_status: str
    created_at: datetime


class ProjectStatusOut(BaseModel):
    project: ProjectOut
    video: VideoOut | None
    highlights_count: int


# ---------- subida multipart ----------
class UploadStart(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    size: int = Field(gt=0)
    content_type: str = "video/mp4"


class PartUrl(BaseModel):
    part_number: int
    url: str


class UploadStartOut(BaseModel):
    video_id: uuid.UUID
    part_size: int
    parts: list[PartUrl]


class PartDone(BaseModel):
    part_number: int = Field(ge=1, le=10000)
    etag: str


class UploadComplete(BaseModel):
    parts: list[PartDone] = Field(min_length=1)


class SignedUrlOut(BaseModel):
    url: str
    expires_in: int


# ---------- transcripción / highlights ----------
class WordOut(BaseModel):
    w: str
    s: float
    e: float


class SegmentOut(ORM):
    idx: int
    start: float
    end: float
    text: str
    speaker_id: uuid.UUID | None
    words: list[WordOut]


class TranscriptOut(BaseModel):
    video_id: uuid.UUID
    language: str | None
    status: str
    segments: list[SegmentOut]


class HighlightOut(ORM):
    id: uuid.UUID
    video_id: uuid.UUID
    start: float
    end: float
    title: str
    reason: str
    category: str | None
    scores: dict[str, float]
    overall: float  # indicador heurístico 0-100, NO una predicción de viralidad

    @computed_field
    @property
    def duration(self) -> float:
        return round(self.end - self.start, 2)


# ---------- clips / subtítulos ----------
class ClipCreate(BaseModel):
    highlight_id: uuid.UUID | None = None
    video_id: uuid.UUID | None = None
    start: float | None = None
    end: float | None = None
    preset: str | None = None


class ClipUpdate(BaseModel):
    start: float | None = None
    end: float | None = None
    preset: str | None = None


class ClipOut(ORM):
    id: uuid.UUID
    project_id: uuid.UUID
    video_id: uuid.UUID
    highlight_id: uuid.UUID | None
    start: float
    end: float
    preset: str
    status: str
    created_at: datetime

    @computed_field
    @property
    def duration(self) -> float:
        return round(self.end - self.start, 2)


class CaptionStyleUpdate(BaseModel):
    font: str | None = Field(default=None, max_length=64)
    font_size_pct: float | None = Field(default=None, ge=2, le=15)
    primary_color: str | None = Field(default=None, pattern=HEX)
    highlight_color: str | None = Field(default=None, pattern=HEX)
    outline_color: str | None = Field(default=None, pattern=HEX)
    outline_width: float | None = Field(default=None, ge=0, le=10)
    shadow: float | None = Field(default=None, ge=0, le=6)
    bold: bool | None = None
    uppercase: bool | None = None
    max_words: int | None = Field(default=None, ge=1, le=8)
    highlight_active_word: bool | None = None


class CaptionRequest(BaseModel):
    style: CaptionStyleUpdate | None = None
    regenerate_words: bool = True


class CaptionOut(ORM):
    id: uuid.UUID
    clip_id: uuid.UUID
    style: dict
    words: list[WordOut]


# ---------- render / export ----------
class RenderCreate(BaseModel):
    aspect: Literal["9:16", "1:1", "16:9"] = "9:16"
    resolution: Literal["720p", "1080p"] = "1080p"


class RenderOut(BaseModel):
    id: uuid.UUID
    clip_id: uuid.UUID
    aspect: str
    resolution: str
    status: str
    progress: float
    error: str | None
    attempts: int
    export_id: uuid.UUID | None = None


class DownloadOut(BaseModel):
    url: str
    expires_in: int
    filename: str
