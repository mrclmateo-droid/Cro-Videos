import json
import subprocess
from dataclasses import dataclass

from app.errors import PermanentError


@dataclass
class ProbeInfo:
    duration: float
    width: int
    height: int
    fps: float | None
    has_audio: bool


def _rotation(stream: dict) -> int:
    rot = stream.get("tags", {}).get("rotate")
    if rot is None:
        for sd in stream.get("side_data_list", []):
            if "rotation" in sd:
                rot = sd["rotation"]
    try:
        return int(float(rot)) % 360 if rot is not None else 0
    except (TypeError, ValueError):
        return 0


def _fps(value: str | None) -> float | None:
    try:
        num, den = (value or "").split("/")
        return round(float(num) / float(den), 3) if float(den) else None
    except ValueError:
        return None


def probe(source: str) -> ProbeInfo:
    """`source` puede ser un path o una URL HTTP (ffprobe lee solo lo necesario)."""
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", source],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe falló: {proc.stderr.strip()[-300:]}")
    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise PermanentError("El archivo no contiene una pista de video")
    width, height = int(video["width"]), int(video["height"])
    if _rotation(video) in (90, 270):  # videos de celular grabados en vertical
        width, height = height, width
    duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)
    if duration <= 0:
        raise PermanentError("No se pudo determinar la duración del video")
    return ProbeInfo(
        duration=duration, width=width, height=height,
        fps=_fps(video.get("avg_frame_rate")),
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
    )
