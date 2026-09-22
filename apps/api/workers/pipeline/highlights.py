"""Detección de highlights: ventanas de transcripción -> LLM -> refinamiento de bordes -> ranking."""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field

CATEGORIES = ["educational", "entertainment", "storytelling", "opinion", "emotional"]
SCORE_KEYS = ["hook", "clarity", "relevance", "emotion", "informational_value",
              "standalone", "pacing", "retention", "closing"]
# Pesos para el indicador global (suman 1.0). Son heurísticos, no una predicción de viralidad.
WEIGHTS = {"hook": 0.20, "clarity": 0.10, "relevance": 0.10, "emotion": 0.10, "informational_value": 0.10,
           "standalone": 0.15, "pacing": 0.05, "retention": 0.10, "closing": 0.10}

_SENTENCE_END = (".", "?", "!", "…", "。")


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Seg:
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)


@dataclass
class Candidate:
    start: float
    end: float
    title: str
    reason: str
    category: str | None
    scores: dict[str, float]
    overall: float


@dataclass
class Config:
    min_s: float = 15.0
    max_s: float = 90.0
    window_s: float = 900.0
    overlap_s: float = 60.0
    per_window: int = 6


SYSTEM = """Sos un editor de video experto en contenido corto vertical (Reels, TikTok, YouTube Shorts).
Recibís un fragmento de la transcripción de un video largo. Cada línea tiene el formato [inicio-fin] texto, en segundos.
Tu tarea: proponer los momentos con más potencial para funcionar como un clip independiente.

Buscá: hooks fuertes, frases sorprendentes, historias, opiniones contundentes, momentos emocionales, preguntas
interesantes con su respuesta, consejos concretos, datos llamativos, humor, contraste o conflicto, revelaciones y
conclusiones importantes. Analizá el contexto completo, no palabras clave sueltas.

Reglas estrictas:
- Usá únicamente tiempos que aparezcan en la transcripción. No inventes tiempos.
- Cada clip dura entre {min_s:g} y {max_s:g} segundos.
- Debe entenderse sin ver el resto del video, empezar en una idea nueva y terminar cuando la idea se cierra.
- Nunca cortes una frase por la mitad.
- No inventes contenido: el título y el motivo deben basarse solo en lo que se dice.
- Puntuá cada criterio de 0 a 10 con honestidad. Son heurísticas para ayudar a elegir, no predicciones de viralidad.
- Si no hay momentos buenos, devolvé una lista vacía.
- Escribí título y motivo en el idioma de la transcripción."""

SCHEMA = {
    "type": "object",
    "properties": {
        "highlights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "title": {"type": "string"},
                    "reason": {"type": "string", "description": "Por qué este momento funciona como clip"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "scores": {
                        "type": "object",
                        "properties": {k: {"type": "number", "minimum": 0, "maximum": 10} for k in SCORE_KEYS},
                        "required": SCORE_KEYS,
                    },
                },
                "required": ["start", "end", "title", "reason", "category", "scores"],
            },
        }
    },
    "required": ["highlights"],
}


def build_windows(segs: list[Seg], window_s: float, overlap_s: float) -> list[list[Seg]]:
    if not segs:
        return []
    t0, t_end = segs[0].start, segs[-1].end
    windows: list[list[Seg]] = []
    start = t0
    while start < t_end:
        chunk = [s for s in segs if s.end > start and s.start < start + window_s]
        if chunk:
            windows.append(chunk)
        if start + window_s >= t_end:
            break
        start += window_s - overlap_s
    return windows


def format_window(segs: list[Seg]) -> str:
    return "\n".join(f"[{s.start:.1f}-{s.end:.1f}] {s.text}" for s in segs)


def _flat_words(segs: list[Seg]) -> list[Word]:
    out: list[Word] = []
    for s in segs:
        out.extend(s.words if s.words else [Word(s.text, s.start, s.end)])
    return out


def _is_sentence_end(words: list[Word], i: int) -> bool:
    if i >= len(words) - 1:
        return True
    if words[i].text.rstrip("\"”’»)").endswith(_SENTENCE_END):
        return True
    return words[i + 1].start - words[i].end >= 0.8  # pausa larga = fin de idea


def refine(raw: dict, words: list[Word], starts: list[float], ends: list[float],
           duration: float, cfg: Config) -> Candidate | None:
    """Ajusta los tiempos del LLM a límites naturales: empieza al inicio de una frase, termina al final de otra."""
    try:
        rs, re_ = float(raw["start"]), float(raw["end"])
    except (KeyError, TypeError, ValueError):
        return None
    if not words or re_ <= rs:
        return None

    i = min(bisect.bisect_left(starts, rs - 0.4), len(words) - 1)
    while i > 0 and not _is_sentence_end(words, i - 1) and words[i].start > rs - 6.0:
        i -= 1

    j = max(bisect.bisect_right(ends, re_ + 0.4) - 1, i)
    while j < len(words) - 1 and not _is_sentence_end(words, j) and words[j].end < re_ + 8.0:
        j += 1
    if not _is_sentence_end(words, j):  # no se encontró cierre cerca: retroceder al fin de frase previo
        k = j
        while k > i and not _is_sentence_end(words, k):
            k -= 1
        if k > i:
            j = k

    if words[j].end - words[i].start > cfg.max_s:  # demasiado largo: cerrar en una frase anterior
        k = j
        while k > i and (not _is_sentence_end(words, k) or words[k].end - words[i].start > cfg.max_s):
            k -= 1
        if k <= i:
            return None
        j = k

    lo = words[i - 1].end if i > 0 else 0.0
    start = min(max(words[i].start - 0.15, lo), words[i].start)
    hi = words[j + 1].start if j + 1 < len(words) else duration
    end = max(min(words[j].end + 0.35, hi, duration), words[j].end)

    if end - start < cfg.min_s:
        return None

    raw_scores = raw.get("scores") or {}
    scores: dict[str, float] = {}
    for k in SCORE_KEYS:
        try:
            scores[k] = max(0.0, min(10.0, float(raw_scores.get(k, 0))))
        except (TypeError, ValueError):
            scores[k] = 0.0
    overall = round(sum(scores[k] * WEIGHTS[k] for k in SCORE_KEYS) * 10, 1)
    cat = raw.get("category")
    return Candidate(
        start=round(start, 3), end=round(end, 3),
        title=str(raw.get("title", "")).strip()[:300] or "Momento destacado",
        reason=str(raw.get("reason", "")).strip(),
        category=cat if cat in CATEGORIES else None,
        scores=scores, overall=overall,
    )


def dedupe(cands: list[Candidate]) -> list[Candidate]:
    kept: list[Candidate] = []
    for c in sorted(cands, key=lambda x: x.overall, reverse=True):
        dur = c.end - c.start
        clash = False
        for k in kept:
            inter = min(c.end, k.end) - max(c.start, k.start)
            if inter > 0.4 * min(dur, k.end - k.start):
                clash = True
                break
        if not clash:
            kept.append(c)
    return kept


def find_candidates(llm, segs: list[Seg], duration: float, cfg: Config) -> list[Candidate]:
    words = _flat_words(segs)
    starts = [w.start for w in words]
    ends = [w.end for w in words]
    system = SYSTEM.format(min_s=cfg.min_s, max_s=cfg.max_s)

    refined: list[Candidate] = []
    for window in build_windows(segs, cfg.window_s, cfg.overlap_s):
        user = (f"Proponé hasta {cfg.per_window} momentos de esta transcripción.\n\n{format_window(window)}")
        result = llm.complete_json(system=system, user=user, tool_name="submit_highlights", schema=SCHEMA)
        for raw in result.get("highlights", []):
            cand = refine(raw, words, starts, ends, duration, cfg)
            if cand:
                refined.append(cand)

    max_total = min(20, max(3, round(duration / 300)))
    return dedupe(refined)[:max_total]
