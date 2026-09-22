import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Transcript, TranscriptSegment


def words_for_range(db: Session, video_id: uuid.UUID, start: float, end: float) -> list[dict]:
    """Palabras de la transcripción dentro de [start, end], con tiempos relativos al inicio del clip."""
    rows = db.execute(
        select(TranscriptSegment.words)
        .join(Transcript, Transcript.id == TranscriptSegment.transcript_id)
        .where(Transcript.video_id == video_id, TranscriptSegment.end > start, TranscriptSegment.start < end)
        .order_by(TranscriptSegment.start)
    ).all()
    out: list[dict] = []
    for (words,) in rows:
        for w in words or []:
            if w["s"] >= start - 0.05 and w["e"] <= end + 0.05:
                out.append({
                    "w": w["w"],
                    "s": round(max(w["s"], start) - start, 3),
                    "e": round(min(w["e"], end) - start, 3),
                })
    return out
