import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Clip, Export, Project, RenderJob, User, Video

settings = get_settings()


def get_current_user(db: Session = Depends(get_db)) -> User:
    """MVP: un único usuario local. Reemplazar por autenticación real (JWT/OAuth) antes de producción."""
    user = db.scalar(select(User).where(User.email == settings.default_user_email))
    if user is None:
        user = User(email=settings.default_user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def owned_project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    p = db.scalar(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    if p is None:
        raise HTTPException(404, "Proyecto no encontrado")
    return p


def owned_video(db: Session, video_id: uuid.UUID, user: User) -> Video:
    v = db.scalar(
        select(Video)
        .join(Project, Project.id == Video.project_id)
        .where(Video.id == video_id, Project.user_id == user.id)
    )
    if v is None:
        raise HTTPException(404, "Video no encontrado")
    return v


def owned_clip(db: Session, clip_id: uuid.UUID, user: User) -> Clip:
    c = db.scalar(
        select(Clip)
        .join(Project, Project.id == Clip.project_id)
        .where(Clip.id == clip_id, Project.user_id == user.id)
    )
    if c is None:
        raise HTTPException(404, "Clip no encontrado")
    return c


def owned_render(db: Session, render_id: uuid.UUID, user: User) -> RenderJob:
    r = db.scalar(
        select(RenderJob)
        .join(Clip, Clip.id == RenderJob.clip_id)
        .join(Project, Project.id == Clip.project_id)
        .where(RenderJob.id == render_id, Project.user_id == user.id)
    )
    if r is None:
        raise HTTPException(404, "Render no encontrado")
    return r


def owned_export(db: Session, export_id: uuid.UUID, user: User) -> Export:
    e = db.scalar(
        select(Export)
        .join(RenderJob, RenderJob.id == Export.render_job_id)
        .join(Clip, Clip.id == RenderJob.clip_id)
        .join(Project, Project.id == Clip.project_id)
        .where(Export.id == export_id, Project.user_id == user.id)
    )
    if e is None:
        raise HTTPException(404, "Export no encontrado")
    return e
