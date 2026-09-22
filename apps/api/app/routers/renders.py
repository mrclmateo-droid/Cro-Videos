import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_db
from ..deps import get_current_user, owned_clip, owned_export, owned_render
from ..models import Export, RenderJob, User
from ..schemas import DownloadOut, RenderCreate, RenderOut
from ..services import queue

router = APIRouter(tags=["renders"])


def _render_out(db: Session, job: RenderJob) -> RenderOut:
    export_id = db.scalar(select(Export.id).where(Export.render_job_id == job.id))
    return RenderOut(id=job.id, clip_id=job.clip_id, aspect=job.aspect, resolution=job.resolution,
                     status=job.status, progress=job.progress, error=job.error, attempts=job.attempts,
                     export_id=export_id)


@router.post("/clips/{clip_id}/render", response_model=RenderOut, status_code=202)
def render_clip(clip_id: uuid.UUID, body: RenderCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    clip = owned_clip(db, clip_id, user)
    active = db.scalar(
        select(RenderJob).where(
            RenderJob.clip_id == clip.id, RenderJob.aspect == body.aspect,
            RenderJob.resolution == body.resolution, RenderJob.status.in_(["queued", "rendering"]),
        )
    )
    if active:  # evita renders duplicados por doble clic
        return _render_out(db, active)

    job = RenderJob(clip_id=clip.id, aspect=body.aspect, resolution=body.resolution)
    db.add(job)
    db.commit()
    try:
        queue.enqueue_render(job.id)
    except Exception:
        job.status = "error"
        job.error = "La cola no está disponible"
        db.commit()
        raise HTTPException(503, "La cola no está disponible")
    return _render_out(db, job)


@router.get("/renders/{render_id}", response_model=RenderOut)
def get_render(render_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _render_out(db, owned_render(db, render_id, user))


@router.get("/exports/{export_id}/download", response_model=DownloadOut)
def download_export(export_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    export = owned_export(db, export_id, user)
    if export.expires_at < datetime.now(timezone.utc):
        raise HTTPException(410, "El export expiró. Generá el render de nuevo.")
    filename = f"reel_{export.id.hex[:8]}.mp4"
    return DownloadOut(url=storage.presign_download(export.s3_key, expires=900, filename=filename),
                       expires_in=900, filename=filename)
