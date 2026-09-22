import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=_now)


def _updated() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    created_at: Mapped[datetime] = _created()


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # created | uploading | transcribing | analyzing | finding_highlights | ready | error
    status: Mapped[str] = mapped_column(String(32), default="created")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()


class Video(Base):
    __tablename__ = "videos"
    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    s3_key: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(100), default="video/mp4")
    size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    upload_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|uploading|uploaded
    audio_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    silences: Mapped[list] = mapped_column(JSONB, default=list)  # [{"start":..,"end":..}]
    created_at: Mapped[datetime] = _created()


class Transcript(Base):
    __tablename__ = "transcripts"
    id: Mapped[uuid.UUID] = _uuid_pk()
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), unique=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | done


class Speaker(Base):
    """Reservado para diarización (fuera del MVP)."""
    __tablename__ = "speakers"
    id: Mapped[uuid.UUID] = _uuid_pk()
    transcript_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transcripts.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(64))


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id: Mapped[uuid.UUID] = _uuid_pk()
    transcript_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transcripts.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    start: Mapped[float] = mapped_column(Float, index=True)
    end: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    speaker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("speakers.id", ondelete="SET NULL"), nullable=True)
    words: Mapped[list] = mapped_column(JSONB, default=list)  # [{"w":..,"s":..,"e":..}]


class Highlight(Base):
    __tablename__ = "highlights"
    id: Mapped[uuid.UUID] = _uuid_pk()
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String(300))
    reason: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scores: Mapped[dict] = mapped_column(JSONB, default=dict)  # heurísticos 0-10, no predicciones
    overall: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    created_at: Mapped[datetime] = _created()


class Clip(Base):
    __tablename__ = "clips"
    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    highlight_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("highlights.id", ondelete="SET NULL"), nullable=True)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    preset: Mapped[str] = mapped_column(String(32), default="podcast_viral")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()


class Caption(Base):
    __tablename__ = "captions"
    id: Mapped[uuid.UUID] = _uuid_pk()
    clip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clips.id", ondelete="CASCADE"), unique=True)
    style: Mapped[dict] = mapped_column(JSONB, default=dict)
    words: Mapped[list] = mapped_column(JSONB, default=list)  # tiempos relativos al inicio del clip


class Edit(Base):
    """Reservado para ediciones (zoom, cortes, B-roll) — fuera del MVP."""
    __tablename__ = "edits"
    id: Mapped[uuid.UUID] = _uuid_pk()
    clip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clips.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = _created()


class RenderJob(Base):
    __tablename__ = "render_jobs"
    id: Mapped[uuid.UUID] = _uuid_pk()
    clip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clips.id", ondelete="CASCADE"), index=True)
    aspect: Mapped[str] = mapped_column(String(8))
    resolution: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|rendering|completed|error
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()


class Export(Base):
    __tablename__ = "exports"
    id: Mapped[uuid.UUID] = _uuid_pk()
    render_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("render_jobs.id", ondelete="CASCADE"), unique=True)
    s3_key: Mapped[str] = mapped_column(String(512))
    size: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
