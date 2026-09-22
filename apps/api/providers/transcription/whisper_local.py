from .base import Segment, TranscriptionResult, Word


class FasterWhisperProvider:
    """Transcripción local con faster-whisper. El modelo se carga una vez por proceso worker."""

    def __init__(self, model_size: str, device: str, compute_type: str):
        self.model_size, self.device, self.compute_type = model_size, device, compute_type
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    def transcribe(self, audio_path: str, language: str | None = None) -> TranscriptionResult:
        model = self._get_model()
        segments, info = model.transcribe(
            audio_path, language=language, word_timestamps=True, vad_filter=True, beam_size=5
        )
        out: list[Segment] = []
        for seg in segments:  # generador: acá ocurre el trabajo pesado
            words = [
                Word(text=w.word.strip(), start=float(w.start), end=float(w.end))
                for w in (seg.words or [])
                if w.word.strip()
            ]
            out.append(Segment(start=float(seg.start), end=float(seg.end), text=seg.text.strip(), words=words))
        return TranscriptionResult(language=info.language, segments=out)
