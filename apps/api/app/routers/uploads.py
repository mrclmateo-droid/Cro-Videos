import math
import os
import uuid

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import storage
from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user, owned_project, owned_video
from ..models import Project, User, Video
from ..schemas import PartUrl, UploadComplete, UploadStart, UploadStartOut, VideoOut
from ..services import queue

router = APIRouter(tags=["uploads"])
settings = get_settings()

ALLOWED_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


def _validate(filename: str, size: int) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, f"Formato no soportado. Permitidos: {', '.join(sorted(ALLOWED_EXT))}")
    if size <= 0 or size > settings.max_upload_bytes:
        raise HTTPException(413, f"El archivo supera el máximo de {settings.max_upload_bytes // 1024**3} GB")
    return ext


def _start_pipeline(db: Session, project: Project) -> None:
    project.status = "transcribing"
    project.error = None
    db.commit()


@router.post("/projects/{project_id}/uploads", response_model=UploadStartOut, status_code=201)
def start_upload(project_id: uuid.UUID, body: UploadStart, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Inicia una subida multipart: devuelve una URL firmada por cada parte."""
    project = owned_project(db, project_id, user)
    ext = _validate(body.filename, body.size)
    video_id = uuid.uuid4()
    key = f"videos/{project.id}/{video_id}/source{ext}"
    part_size = settings.upload_part_size
    n_parts = math.ceil(body.size / part_size)
    upload_id = storage.create_multipart(key, body.content_type)

    db.add(Video(id=video_id, project_id=project.id, filename=body.filename, s3_key=key,
                 content_type=body.content_type, size=body.size, upload_id=upload_id,
                 upload_status="uploading"))
    project.status = "uploading"
    db.commit()

    parts = [PartUrl(part_number=i, url=storage.presign_part(key, upload_id, i)) for i in range(1, n_parts + 1)]
    return UploadStartOut(video_id=video_id, part_size=part_size, parts=parts)


@router.post("/uploads/{video_id}/complete", response_model=VideoOut)
def complete_upload(video_id: uuid.UUID, body: UploadComplete, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    video = owned_video(db, video_id, user)
    if video.upload_status == "uploaded":
        return video  # idempotente
    if video.upload_status != "uploading" or not video.upload_id:
        raise HTTPException(409, "La subida no está en curso")
    parts = [{"PartNumber": p.part_number, "ETag": p.etag} for p in sorted(body.parts, key=lambda p: p.part_number)]
    try:
        storage.complete_multipart(video.s3_key, video.upload_id, parts)
    except ClientError as e:
        raise HTTPException(400, f"No se pudo completar la subida: {e.response['Error'].get('Message', 'error')}")
    video.size = storage.object_size(video.s3_key) or video.size
    video.upload_status = "uploaded"
    video.upload_id = None
    project = db.get(Project, video.project_id)
    _start_pipeline(db, project)
    try:
        queue.enqueue_pipeline(video.id)
    except Exception:
        raise HTTPException(503, "Video subido, pero la cola no está disponible. Reintentá con POST /videos/{id}/reprocess")
    return video


@router.post("/uploads/{video_id}/abort", status_code=204)
def abort_upload(video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    video = owned_video(db, video_id, user)
    if video.upload_status != "uploading":
        raise HTTPException(409, "No hay una subida en curso")
    if video.upload_id:
        storage.abort_multipart(video.s3_key, video.upload_id)
    project = db.get(Project, video.project_id)
    project.status = "created"
    db.delete(video)
    db.commit()


@router.post("/projects/{project_id}/upload-direct", response_model=VideoOut, status_code=201)
def upload_direct(project_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Subida simple a través de la API. Pensada para probar desde Swagger (/docs) sin frontend.
    Para archivos grandes en producción usar el flujo multipart directo a S3."""
    project = owned_project(db, project_id, user)
    filename = file.filename or "video.mp4"
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    ext = _validate(filename, size)

    video_id = uuid.uuid4()
    key = f"videos/{project.id}/{video_id}/source{ext}"
    content_type = file.content_type or "video/mp4"
    storage.upload_fileobj(file.file, key, content_type)

    video = Video(id=video_id, project_id=project.id, filename=filename, s3_key=key,
                  content_type=content_type, size=size, upload_status="uploaded")
    db.add(video)
    _start_pipeline(db, project)
    try:
        queue.enqueue_pipeline(video.id)
    except Exception:
        raise HTTPException(503, "Video subido, pero la cola no está disponible. Reintentá con POST /videos/{id}/reprocess")
    return video
