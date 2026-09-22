"""Tareas Celery. Cada etapa es idempotente: si ya se hizo, se salta. Los reintentos son seguros."""
from __future__ import annotations

import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone

from celery import Task
from sqlalchemy import delete, func, select

from app import storage
from app.config import get_settings
from app.db import session_scope
from app.errors import PermanentError
from app.models import (Caption, Clip, Export, Highlight, Project, RenderJob, Transcript,
                        TranscriptSegment, Video)
from app.services import presets
from providers.llm import get_llm_provider
from providers.reframe import get_reframer
from providers.transcription import get_transcription_provider
from workers.celery_app import celery
from workers.ffmpeg import audio as ff_audio
from workers.ffmpeg import probe as ff_probe
from workers.ffmpeg import render as ff_render
from workers.ffmpeg import subtitles
from workers.pipeline import highlights as hl

log = logging.getLogger(__name__)
settings = get_settings()

# Reintenta errores transitorios (red, S3, rate limits) con backoff; los PermanentError fallan de inmediato.
RETRY = dict(
    autoretry_for=(Exception,),
    dont_autoretry_for=(PermanentError,),
    retry_backoff=10,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)


def _short(exc: BaseException) -> str:
    msg = str(exc) if isinstance(exc, PermanentError) else f"{type(exc).__name__}: {exc}"
    return msg[:500]


class VideoTask(Task):
    """Al fallar definitivamente, deja el error visible en el proyecto."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        log.error("Tarea %s falló: %s", self.name, exc)
        try:
            with session_scope() as db:
                video = db.get(Video, uuid.UUID(args[0]))
                if video:
                    project = db.get(Project, video.project_id)
                    project.status = "error"
                    project.error = _short(exc)
        except Exception:
            log.exception("No se pudo registrar el error del proyecto")


class RenderTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        log.error("Render %s falló: %s", args[0], exc)
        try:
            with session_scope() as db:
                job = db.get(RenderJob, uuid.UUID(args[0]))
                if job:
                    job.status = "error"
                    job.error = _short(exc)
        except Exception:
            log.exception("No se pudo registrar el error del render")


def _get_video(db, video_id: str) -> Video:
    video = db.get(Video, uuid.UUID(video_id))
    if video is None:
        raise PermanentError("El video no existe")
    return video


def _set_status(db, project_id: uuid.UUID, status: str) -> None:
    project = db.get(Project, project_id)
    project.status = status
    project.error = None


# ---------------------------------------------------------------- pipeline
@celery.task(name="workers.tasks.probe_video", base=VideoTask, **RETRY)
def probe_video(video_id: str) -> None:
    with session_scope() as db:
        video = _get_video(db, video_id)
        if video.duration:
            return
        _set_status(db, video.project_id, "transcribing")
        key = video.s3_key
    info = ff_probe.probe(storage.presign_internal(key))
    if info.duration > settings.max_video_seconds:
        raise PermanentError(f"El video supera el máximo de {settings.max_video_seconds // 3600} horas")
    if not info.has_audio:
        raise PermanentError("El video no tiene pista de audio, no se puede transcribir")
    with session_scope() as db:
        video = _get_video(db, video_id)
        video.duration, video.width, video.height, video.fps = info.duration, info.width, info.height, info.fps


@celery.task(name="workers.tasks.extract_audio", base=VideoTask, **RETRY)
def extract_audio(video_id: str) -> None:
    with session_scope() as db:
        video = _get_video(db, video_id)
        if video.audio_key and storage.object_size(video.audio_key):
            return
        key, vid = video.s3_key, video.id
    audio_key = f"audio/{vid}.flac"
    with tempfile.TemporaryDirectory(prefix="audio_") as tmp:
        out = os.path.join(tmp, "audio.flac")
        ff_audio.extract_audio(storage.presign_internal(key), out)
        storage.upload_file(out, audio_key, "audio/flac")
    with session_scope() as db:
        _get_video(db, video_id).audio_key = audio_key


@celery.task(name="workers.tasks.transcribe_video", base=VideoTask, **RETRY)
def transcribe_video(video_id: str) -> None:
    with session_scope() as db:
        video = _get_video(db, video_id)
        transcript = db.scalar(select(Transcript).where(Transcript.video_id == video.id))
        if transcript and transcript.status == "done":
            return
        _set_status(db, video.project_id, "transcribing")
        audio_key, vid = video.audio_key, video.id
    if not audio_key:
        raise PermanentError("Falta el audio extraído")

    with tempfile.TemporaryDirectory(prefix="stt_") as tmp:
        path = os.path.join(tmp, "audio.flac")
        storage.download_file(audio_key, path)
        result = get_transcription_provider().transcribe(path)
    if not any(s.text.strip() for s in result.segments):
        raise PermanentError("No se detectó voz en el video")

    with session_scope() as db:  # todo en una transacción: 'done' solo si los segmentos quedaron guardados
        transcript = db.scalar(select(Transcript).where(Transcript.video_id == vid))
        if transcript is None:
            transcript = Transcript(video_id=vid, status="pending")
            db.add(transcript)
            db.flush()
        db.execute(delete(TranscriptSegment).where(TranscriptSegment.transcript_id == transcript.id))
        db.add_all([
            TranscriptSegment(
                transcript_id=transcript.id, idx=i, start=s.start, end=s.end, text=s.text,
                words=[{"w": w.text, "s": w.start, "e": w.end} for w in s.words],
            )
            for i, s in enumerate(result.segments)
        ])
        transcript.language = result.language
        transcript.status = "done"


@celery.task(name="workers.tasks.detect_silences", base=VideoTask, **RETRY)
def detect_silences(video_id: str) -> None:
    with session_scope() as db:
        video = _get_video(db, video_id)
        _set_status(db, video.project_id, "analyzing")
        audio_key = video.audio_key
    if not audio_key:
        raise PermanentError("Falta el audio extraído")
    silences = ff_audio.detect_silences(storage.presign_internal(audio_key))
    with session_scope() as db:
        _get_video(db, video_id).silences = silences  # sobrescribe: idempotente


@celery.task(name="workers.tasks.find_highlights", base=VideoTask, **RETRY)
def find_highlights(video_id: str) -> None:
    with session_scope() as db:
        video = _get_video(db, video_id)
        vid, duration, audio_key = video.id, video.duration, video.audio_key
        existing = db.scalar(select(func.count()).select_from(Highlight).where(Highlight.video_id == vid)) or 0
        if existing:
            _set_status(db, video.project_id, "ready")
            return
        _set_status(db, video.project_id, "finding_highlights")
        rows = db.scalars(
            select(TranscriptSegment)
            .join(Transcript, Transcript.id == TranscriptSegment.transcript_id)
            .where(Transcript.video_id == vid)
            .order_by(TranscriptSegment.idx)
        ).all()
        segs = [
            hl.Seg(r.start, r.end, r.text, [hl.Word(w["w"], w["s"], w["e"]) for w in (r.words or [])])
            for r in rows
        ]
    if not segs:
        raise PermanentError("No hay transcripción para analizar")

    cfg = hl.Config(min_s=settings.min_highlight_seconds, max_s=settings.max_highlight_seconds)
    candidates = hl.find_candidates(get_llm_provider(), segs, duration, cfg)

    with session_scope() as db:
        video = _get_video(db, video_id)
        db.add_all([
            Highlight(video_id=vid, start=c.start, end=c.end, title=c.title, reason=c.reason,
                      category=c.category, scores=c.scores, overall=c.overall)
            for c in candidates
        ])
        _set_status(db, video.project_id, "ready")
        video.audio_key = None
    if audio_key:  # limpieza: el audio intermedio ya no se necesita
        try:
            storage.delete_object(audio_key)
        except Exception:
            log.warning("No se pudo borrar %s", audio_key)


# ------------------------------------------------------------------ render
def _progress_cb(job_id: uuid.UUID):
    state = {"t": 0.0, "p": -100.0}

    def cb(pct: float) -> None:
        now = time.monotonic()
        if pct - state["p"] < 2 and now - state["t"] < 3:
            return
        state["t"], state["p"] = now, pct
        with session_scope() as db:
            job = db.get(RenderJob, job_id)
            if job:
                job.progress = round(pct, 1)

    return cb


@celery.task(name="workers.tasks.render_clip", base=RenderTask, **RETRY)
def render_clip(render_job_id: str) -> None:
    job_id = uuid.UUID(render_job_id)
    with session_scope() as db:
        job = db.get(RenderJob, job_id)
        if job is None:
            raise PermanentError("El render no existe")
        if job.status == "completed":
            return
        clip = db.get(Clip, job.clip_id)
        video = db.get(Video, clip.video_id)
        caption = db.scalar(select(Caption).where(Caption.clip_id == clip.id))
        if not (video.width and video.height):
            raise PermanentError("El video no fue analizado todavía")
        job.status, job.progress, job.error = "rendering", 0.0, None
        job.attempts += 1
        p = dict(
            aspect=job.aspect, resolution=job.resolution, start=clip.start, end=clip.end,
            s3_key=video.s3_key, src_w=video.width, src_h=video.height, project_id=clip.project_id,
            words=list(caption.words) if caption else [],
            style=dict(caption.style) if caption and caption.style else presets.caption_style(clip.preset),
        )

    out_w, out_h = ff_render.output_size(p["aspect"], p["resolution"])
    source_url = storage.presign_internal(p["s3_key"])
    plan = get_reframer().plan(src_w=p["src_w"], src_h=p["src_h"], target_aspect=out_w / out_h,
                               source_url=source_url, start=p["start"], end=p["end"])
    key = f"exports/{p['project_id']}/{job_id}.mp4"

    with tempfile.TemporaryDirectory(prefix="render_") as tmp:
        out_path = os.path.join(tmp, "out.mp4")
        ass_path = None
        if p["words"]:
            ass_path = os.path.join(tmp, "subs.ass")
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(subtitles.build_ass(p["words"], p["style"], out_w, out_h, p["aspect"]))
        ff_render.render_clip(
            source_url=source_url, out_path=out_path, ass_path=ass_path, start=p["start"],
            duration=p["end"] - p["start"], crop=plan, out_w=out_w, out_h=out_h,
            on_progress=_progress_cb(job_id),
        )
        size = os.path.getsize(out_path)
        storage.upload_file(out_path, key, "video/mp4")

    expires = datetime.now(timezone.utc) + timedelta(hours=settings.export_ttl_hours)
    with session_scope() as db:
        job = db.get(RenderJob, job_id)
        job.status, job.progress = "completed", 100.0
        export = db.scalar(select(Export).where(Export.render_job_id == job_id))
        if export is None:
            db.add(Export(render_job_id=job_id, s3_key=key, size=size, expires_at=expires))
        else:
            export.s3_key, export.size, export.expires_at = key, size, expires
