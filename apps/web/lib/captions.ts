import type { Segment, Word } from "./types";

// Misma lógica que el backend (workers/ffmpeg/subtitles.py) para que el preview coincida con el render.
const SENTENCE_END = /[.?!…]["”’)]*$/;

export const flattenWords = (segments: Segment[]): Word[] => segments.flatMap((s) => s.words);

/** Palabras dentro de [start, end], con tiempos relativos al inicio del clip. */
export function wordsForRange(all: Word[], start: number, end: number): Word[] {
  const out: Word[] = [];
  for (const w of all) {
    if (w.s >= start - 0.05 && w.e <= end + 0.05) {
      out.push({ w: w.w, s: Math.max(w.s, start) - start, e: Math.min(w.e, end) - start });
    }
  }
  return out;
}

export function groupLines(words: Word[], maxWords: number, gap = 0.6): Word[][] {
  const lines: Word[][] = [];
  let cur: Word[] = [];
  for (const w of words) {
    if (cur.length && (cur.length >= maxWords || w.s - cur[cur.length - 1].e >= gap)) {
      lines.push(cur);
      cur = [];
    }
    cur.push(w);
    if (SENTENCE_END.test(w.w)) {
      lines.push(cur);
      cur = [];
    }
  }
  if (cur.length) lines.push(cur);
  return lines;
}

export function activeLine(lines: Word[][], t: number): { line: Word[]; wordIndex: number } | null {
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i];
    if (line[0].s <= t) {
      const nextStart = lines[i + 1]?.[0].s ?? Infinity;
      const endT = Math.min(line[line.length - 1].e + 0.05, nextStart);
      if (t >= endT) return null;
      let wordIndex = 0;
      for (let k = 0; k < line.length; k++) if (line[k].s <= t) wordIndex = k;
      return { line, wordIndex };
    }
  }
  return null;
}
