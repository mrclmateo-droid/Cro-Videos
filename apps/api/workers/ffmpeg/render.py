import subprocess
import tempfile
from typing import Callable

from providers.reframe.base import CropPlan

SIZES = {
    ("9:16", "720p"): (720, 1280), ("9:16", "1080p"): (1080, 1920),
    ("1:1", "720p"): (720, 720), ("1:1", "1080p"): (1080, 1080),
    ("16:9", "720p"): (1280, 720), ("16:9", "1080p"): (1920, 1080),
}


def output_size(aspect: str, resolution: str) -> tuple[int, int]:
    return SIZES[(aspect, resolution)]


def _esc(path: str) -> str:
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_clip(*, source_url: str, out_path: str, ass_path: str | None, start: float, duration: float,
                crop: CropPlan, out_w: int, out_h: int, on_progress: Callable[[float], None]) -> None:
    """Corta, recorta, escala y quema subtítulos. Lee el original por HTTP con seek (no descarga todo el video)."""
    vf = f"crop={crop.w}:{crop.h}:{crop.x}:{crop.y},scale={out_w}:{out_h}:flags=lanczos,setsar=1"
    if ass_path:
        vf += f",ass='{_esc(ass_path)}'"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostats", "-progress", "pipe:1",
        "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", source_url,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out_path,
    ]
    with tempfile.TemporaryFile("w+") as err:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, text=True)
        for line in proc.stdout:  # type: ignore[union-attr]
            key, _, value = line.strip().partition("=")
            if key in ("out_time_us", "out_time_ms") and value.lstrip("-").isdigit():
                seconds = int(value) / 1_000_000
                on_progress(max(0.0, min(99.0, seconds / duration * 100)))
        code = proc.wait()
        if code != 0:
            err.seek(0)
            raise RuntimeError(f"ffmpeg falló al renderizar: {err.read().strip()[-400:]}")
