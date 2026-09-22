"""Encolado de tareas por nombre (la API no importa el código pesado de los workers)."""
import uuid

from celery import chain

from workers.celery_app import celery


def _sig(name: str, entity_id: uuid.UUID):
    return celery.signature(name, args=(str(entity_id),), immutable=True)


def enqueue_pipeline(video_id: uuid.UUID) -> None:
    chain(
        _sig("workers.tasks.probe_video", video_id),
        _sig("workers.tasks.extract_audio", video_id),
        _sig("workers.tasks.transcribe_video", video_id),
        _sig("workers.tasks.detect_silences", video_id),
        _sig("workers.tasks.find_highlights", video_id),
    ).apply_async()


def enqueue_render(render_job_id: uuid.UUID) -> None:
    _sig("workers.tasks.render_clip", render_job_id).apply_async()
