from celery import Celery

from app.config import get_settings

_s = get_settings()

celery = Celery("reelforge", broker=_s.redis_url, include=["workers.tasks"])
celery.conf.update(
    task_default_queue="media",
    task_routes={"workers.tasks.find_highlights": {"queue": "llm"}},
    task_ignore_result=True,
    task_acks_late=True,              # si un worker muere, la tarea se reentrega
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,     # tareas largas: no acaparar
    broker_connection_retry_on_startup=True,
    # Con acks_late en Redis, si una tarea dura más que esto se reentrega (duplicada).
    broker_transport_options={"visibility_timeout": 12 * 3600},
)
