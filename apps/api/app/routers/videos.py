import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_db
from ..deps import get_current_user, owned_video
from ..models import Highlight, Project, Transcript, TranscriptSegment, User
from ..schemas import HighlightOut, SegmentOut, SignedUrlOut, TranscriptOut, VideoOut
from ..services import queue

router = APIRouter(tags=["videos"])


@router.get("/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return owned_video(db, video_id, user)


@router.get("/videos/{video_id}/source-url", response_model=SignedUrlOut)
def source_url(video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """URL firmada para reproducir el video original en el editor."""
    video = owned_video(db, video_id, user)
    return SignedUrlOut(url=storage.presign_download(video.s3_key, expires=3600), expires_in=3600)


@router.get("/videos/{video_id}/transcript", response_model=TranscriptOut)
def get_transcript(video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    video = owned_video(db, video_id, user)
    tr = db.scalar(select(Transcript).where(Transcript.video_id == video.id))
    if tr is None or tr.status != "done":
        raise HTTPException(404, "La transcripción todavía no está lista")
    segs = db.scalars(
        select(TranscriptSegment).where(TranscriptSegment.transcript_id == tr.id).order_by(TranscriptSegment.idx)
    ).all()
    return TranscriptOut(video_id=video.id, language=tr.language, status=tr.status,
                         segments=[SegmentOut.model_validate(s) for s in segs])


@router.get("/videos/{video_id}/highlights", response_model=list[HighlightOut])
def get_highlights(
    video_id: uuid.UUID,
    category: str | None = None,
    min_duration: float | None = Query(default=None, ge=0),
    max_duration: float | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = owned_video(db, video_id, user)
    q = select(Highlight).where(Highlight.video_id == video.id)
    if category:
        q = q.where(Highlight.category == category)
    if min_duration is not None:
        q = q.where((Highlight.end - Highlight.start) >= min_duration)
    if max_duration is not None:
        q = q.where((Highlight.end - Highlight.start) <= max_duration)
    return db.scalars(q.order_by(Highlight.overall.desc())).all()


@router.post("/videos/{video_id}/reprocess", status_code=202)
def reprocess(video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Reintenta el pipeline. Cada etapa es idempotente: salta lo que ya está hecho."""
    video = owned_video(db, video_id, user)
    if video.upload_status != "uploaded":
        raise HTTPException(409, "El video todavía no terminó de subirse")
    project = db.get(Project, video.project_id)
    project.status = "transcribing"
    project.error = None
    db.commit()
    try:
        queue.enqueue_pipeline(video.id)
    except Exception:
        raise HTTPException(503, "La cola no está disponible")
    return {"status": "queued"}
