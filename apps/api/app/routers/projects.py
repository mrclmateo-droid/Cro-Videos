import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, owned_project
from ..models import Highlight, Project, User, Video
from ..schemas import ProjectCreate, ProjectOut, ProjectStatusOut, VideoOut

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = Project(user_id=user.id, name=body.name.strip())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())).all()


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return owned_project(db, project_id, user)


@router.get("/projects/{project_id}/status", response_model=ProjectStatusOut)
def get_status(project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = owned_project(db, project_id, user)
    video = db.scalar(select(Video).where(Video.project_id == project.id).order_by(Video.created_at.desc()))
    count = 0
    if video:
        count = db.scalar(select(func.count()).select_from(Highlight).where(Highlight.video_id == video.id)) or 0
    return ProjectStatusOut(
        project=ProjectOut.model_validate(project),
        video=VideoOut.model_validate(video) if video else None,
        highlights_count=count,
    )
