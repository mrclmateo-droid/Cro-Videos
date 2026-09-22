import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user, owned_clip, owned_video
from ..models import Caption, Clip, Highlight, Project, User, Video
from ..schemas import CaptionOut, CaptionRequest, ClipCreate, ClipOut, ClipUpdate
from ..services import captions as captions_svc
from ..services import presets

router = APIRouter(tags=["clips"])
settings = get_settings()


def _validate_range(video: Video, start: float, end: float) -> None:
    if video.duration is None:
        raise HTTPException(409, "El video todavía no fue analizado")
    if start < 0 or end > video.duration + 0.01 or end <= start:
        raise HTTPException(422, f"Rango inválido. El video dura {video.duration:.1f} s")
    d = end - start
    if d < settings.min_clip_seconds or d > settings.max_clip_seconds:
        raise HTTPException(
            422, f"El clip debe durar entre {settings.min_clip_seconds:g} y {settings.max_clip_seconds:g} segundos"
        )


def _check_preset(name: str) -> str:
    if name not in presets.PRESETS:
        raise HTTPException(422, f"Preset desconocido. Disponibles: {', '.join(presets.PRESETS)}")
    return name


@router.get("/presets")
def list_presets():
    return [{"id": k, "label": v["label"], "caption_style": presets.caption_style(k)} for k, v in presets.PRESETS.items()]


@router.post("/clips", response_model=ClipOut, status_code=201)
def create_clip(body: ClipCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Crea un clip desde un highlight o desde timestamps manuales, con subtítulos por defecto."""
    if body.highlight_id:
        hl = db.scalar(
            select(Highlight)
            .join(Video, Video.id == Highlight.video_id)
            .join(Project, Project.id == Video.project_id)
            .where(Highlight.id == body.highlight_id, Project.user_id == user.id)
        )
        if hl is None:
            raise HTTPException(404, "Highlight no encontrado")
        video = db.get(Video, hl.video_id)
        start = body.start if body.start is not None else hl.start
        end = body.end if body.end is not None else hl.end
    else:
        if body.video_id is None or body.start is None or body.end is None:
            raise HTTPException(422, "Indicá highlight_id, o bien video_id + start + end")
        video = owned_video(db, body.video_id, user)
        start, end = body.start, body.end

    _validate_range(video, start, end)
    preset = _check_preset(body.preset or presets.DEFAULT_PRESET)
    clip = Clip(project_id=video.project_id, video_id=video.id, highlight_id=body.highlight_id,
                start=start, end=end, preset=preset)
    db.add(clip)
    db.flush()
    db.add(Caption(clip_id=clip.id, style=presets.caption_style(preset),
                   words=captions_svc.words_for_range(db, video.id, start, end)))
    db.commit()
    return clip


@router.get("/clips/{clip_id}", response_model=ClipOut)
def get_clip(clip_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return owned_clip(db, clip_id, user)


@router.patch("/clips/{clip_id}", response_model=ClipOut)
def update_clip(clip_id: uuid.UUID, body: ClipUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    clip = owned_clip(db, clip_id, user)
    video = db.get(Video, clip.video_id)
    start = body.start if body.start is not None else clip.start
    end = body.end if body.end is not None else clip.end
    range_changed = (start, end) != (clip.start, clip.end)
    if range_changed:
        _validate_range(video, start, end)

    caption = db.scalar(select(Caption).where(Caption.clip_id == clip.id))
    if caption is None:
        caption = Caption(clip_id=clip.id, style=presets.caption_style(clip.preset), words=[])
        db.add(caption)
    if body.preset is not None and body.preset != clip.preset:
        clip.preset = _check_preset(body.preset)
        caption.style = presets.caption_style(clip.preset)
    if range_changed:
        clip.start, clip.end = start, end
        caption.words = captions_svc.words_for_range(db, video.id, start, end)
    db.commit()
    return clip


@router.get("/clips/{clip_id}/captions", response_model=CaptionOut)
def get_captions(clip_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    clip = owned_clip(db, clip_id, user)
    caption = db.scalar(select(Caption).where(Caption.clip_id == clip.id))
    if caption is None:
        raise HTTPException(404, "El clip no tiene subtítulos")
    return caption


@router.post("/clips/{clip_id}/captions", response_model=CaptionOut)
def generate_captions(clip_id: uuid.UUID, body: CaptionRequest, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """(Re)genera las palabras sincronizadas desde la transcripción y aplica cambios de estilo."""
    clip = owned_clip(db, clip_id, user)
    caption = db.scalar(select(Caption).where(Caption.clip_id == clip.id))
    if caption is None:
        caption = Caption(clip_id=clip.id, style=presets.caption_style(clip.preset), words=[])
        db.add(caption)
    if body.regenerate_words:
        caption.words = captions_svc.words_for_range(db, clip.video_id, clip.start, clip.end)
    if body.style:
        caption.style = {**caption.style, **body.style.model_dump(exclude_none=True)}
    db.commit()
    db.refresh(caption)
    return caption
