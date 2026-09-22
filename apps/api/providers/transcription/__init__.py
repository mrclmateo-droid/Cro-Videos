from functools import lru_cache

from app.config import get_settings

from .base import Segment, TranscriptionProvider, TranscriptionResult, Word

__all__ = ["get_transcription_provider", "Segment", "TranscriptionProvider", "TranscriptionResult", "Word"]


@lru_cache
def get_transcription_provider() -> TranscriptionProvider:
    """Punto único para cambiar de proveedor (p. ej. una API de speech-to-text externa)."""
    s = get_settings()
    from .whisper_local import FasterWhisperProvider

    return FasterWhisperProvider(s.whisper_model, s.whisper_device, s.whisper_compute_type)
