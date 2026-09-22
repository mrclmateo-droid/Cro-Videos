"use client";
import { useMemo, useRef, useState } from "react";
import { groupLines } from "@/lib/captions";
import { clamp, fmtTime } from "@/lib/format";
import type { Word } from "@/lib/types";

export const MIN_CLIP = 3;
export const MAX_CLIP = 180;

type Props = {
  duration: number; // duración total del video
  start: number;
  end: number;
  current: number; // playhead (tiempo absoluto)
  words: Word[]; // relativas al clip
  maxWords: number;
  baseStart: number; // rango inicial del clip: define la ventana visible
  baseEnd: number;
  onChange: (start: number, end: number) => void;
  onCommit: (which: "start" | "end") => void;
};

/** Timeline con ventana de ±60 s alrededor del clip. Tracks: video (con manijas) y subtítulos. */
export function Timeline({ duration, start, end, current, words, maxWords, baseStart, baseEnd, onChange, onCommit }: Props) {
  const track = useRef<HTMLDivElement>(null);
  const drag = useRef<"start" | "end" | null>(null);
  const [active, setActive] = useState<"start" | "end" | null>(null);

  const winStart = Math.max(0, Math.min(baseStart - 60, start - 2));
  const winEnd = Math.min(duration, Math.max(baseEnd + 60, end + 2));
  const span = Math.max(1, winEnd - winStart);
  const pct = (t: number) => ((t - winStart) / span) * 100;

  const lines = useMemo(() => groupLines(words, maxWords), [words, maxWords]);

  function timeAt(clientX: number) {
    const r = track.current!.getBoundingClientRect();
    return winStart + clamp((clientX - r.left) / r.width, 0, 1) * span;
  }

  const down = (which: "start" | "end") => (e: React.PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = which;
    setActive(which);
  };

  const move = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    const t = timeAt(e.clientX);
    if (drag.current === "start") {
      const s = clamp(t, Math.max(winStart, end - MAX_CLIP), end - MIN_CLIP);
      onChange(s, end);
    } else {
      const en = clamp(t, start + MIN_CLIP, Math.min(winEnd, start + MAX_CLIP));
      onChange(start, en);
    }
  };

  const up = () => {
    if (!drag.current) return;
    const which = drag.current;
    drag.current = null;
    setActive(null);
    onCommit(which);
  };

  const handle = (which: "start" | "end", at: number) => (
    <div
      onPointerDown={down(which)} onPointerMove={move} onPointerUp={up} onPointerCancel={up}
      className="absolute top-0 z-10 flex h-full w-6 -translate-x-1/2 cursor-ew-resize touch-none items-center justify-center"
      style={{ left: `${pct(at)}%` }}
      role="slider" aria-label={which === "start" ? "Inicio del clip" : "Fin del clip"}
    >
      <div className={`h-full w-1.5 rounded-full transition ${active === which ? "bg-white" : "bg-violet-300"}`} />
    </div>
  );

  return (
    <div className="space-y-2 select-none">
      <div className="flex justify-between text-[11px] tabular-nums text-zinc-500">
        <span>{fmtTime(winStart)}</span>
        <span className="text-zinc-300">Clip: {fmtTime(start, 1)} → {fmtTime(end, 1)} · {(end - start).toFixed(1)} s</span>
        <span>{fmtTime(winEnd)}</span>
      </div>

      <div className="grid grid-cols-[64px_1fr] items-center gap-x-2 gap-y-2">
        <span className="text-[11px] text-zinc-500">Video</span>
        <div ref={track} className="relative h-12 overflow-hidden rounded-lg bg-white/[.06]">
          <div className="absolute top-0 h-full rounded-md bg-violet-500/30 ring-1 ring-inset ring-violet-400/60"
               style={{ left: `${pct(start)}%`, width: `${pct(end) - pct(start)}%` }} />
          {handle("start", start)}
          {handle("end", end)}
          {current >= winStart && current <= winEnd && (
            <div className="pointer-events-none absolute top-0 h-full w-0.5 bg-white/90" style={{ left: `${pct(current)}%` }} />
          )}
        </div>

        <span className="text-[11px] text-zinc-500">Subtítulos</span>
        <div className="relative h-7 overflow-hidden rounded-lg bg-white/[.06]">
          {lines.map((line, i) => {
            const a = start + line[0].s;
            const b = start + line[line.length - 1].e;
            return (
              <div key={i} className="absolute top-1 h-5 overflow-hidden rounded bg-sky-400/25 px-1 text-[10px] leading-5 text-sky-100 ring-1 ring-inset ring-sky-300/30"
                   style={{ left: `${pct(a)}%`, width: `${Math.max(0.4, pct(b) - pct(a))}%` }}>
                {line.map((w) => w.w).join(" ")}
              </div>
            );
          })}
        </div>

        <span className="text-[11px] text-zinc-600">Zoom · Cortes · B-roll</span>
        <div className="flex h-7 items-center rounded-lg border border-dashed border-white/10 px-3 text-[11px] text-zinc-600">
          Próximamente
        </div>
      </div>
    </div>
  );
}
