import re
import subprocess


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falló: {proc.stderr.strip()[-400:]}")
    return proc


def extract_audio(source: str, out_path: str) -> None:
    """Audio mono 16 kHz en FLAC (formato ideal para Whisper, sin pérdida y liviano)."""
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", source,
          "-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac", out_path], timeout=4 * 3600)


_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def detect_silences(source: str, noise_db: float = -35.0, min_duration: float = 0.5) -> list[dict]:
    proc = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", source,
                 "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}", "-f", "null", "-"],
                timeout=3600)
    silences: list[dict] = []
    start: float | None = None
    for line in proc.stderr.splitlines():
        m = _START.search(line)
        if m:
            start = max(0.0, float(m.group(1)))
            continue
        m = _END.search(line)
        if m and start is not None:
            silences.append({"start": round(start, 3), "end": round(float(m.group(1)), 3)})
            start = None
    return silences
