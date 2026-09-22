"use client";
import { Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { activeLine, groupLines } from "@/lib/captions";
import { fmtTime } from "@/lib/format";
import type { CaptionStyle, Word } from "@/lib/types";

type Props = {
  src: string | null;
  start: number;
  end: number;
  words: Word[]; // tiempos relativos al inicio del clip
  style: CaptionStyle;
  seek: { t: number; n: number } | null; // pide mover el playhead (tiempo absoluto del video)
  onTime?: (absoluteTime: number) => void;
};

/** Preview 9:16 (recorte centrado, igual que el render del MVP) con subtítulos superpuestos. */
export function PreviewPlayer({ src, start, end, words, style, seek, onTime }: Props) {
  const ref = useRef<HTMLVideoElement>(null);
  const onTimeRef = useRef(onTime);
  onTimeRef.current = onTime;
  const [t, setT] = useState(0); // tiempo relativo al clip
  const [playing, setPlaying] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const v = ref.current;
    if (v && ready) v.currentTime = start;
  }, [ready]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const v = ref.current;
    if (v && ready && seek) v.currentTime = seek.t;
  }, [seek]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let raf = 0;
    let last = 0;
    const tick = (now: number) => {
      const v = ref.current;
      if (v) {
        if (!v.paused && v.currentTime >= end) v.currentTime = start; // loop del clip
        const rel = v.currentTime - start;
        setT((prev) => (Math.abs(prev - rel) < 0.01 ? prev : rel));
        if (now - last > 100) {
          last = now;
          onTimeRef.current?.(v.currentTime);
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [start, end]);

  const lines = useMemo(() => groupLines(words, style.max_words), [words, style.max_words]);
  const active = activeLine(lines, t);
  const dur = Math.max(0.1, end - start);

  function toggle() {
    const v = ref.current;
    if (!v) return;
    if (v.paused) {
      if (v.currentTime < start || v.currentTime >= end) v.currentTime = start;
      void v.play();
    } else {
      v.pause();
    }
  }

  return (
    <div className="mx-auto w-full max-w-[340px] space-y-3">
      <div className="relative aspect-[9/16] w-full overflow-hidden rounded-2xl bg-black shadow-2xl ring-1 ring-white/10"
           style={{ containerType: "inline-size" }}>
        {src ? (
          <video
            ref={ref} src={src} playsInline preload="metadata"
            className="h-full w-full object-cover"
            onLoadedMetadata={() => setReady(true)}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onClick={toggle}
          />
        ) : (
          <div className="grid h-full w-full place-items-center text-sm text-zinc-500">Cargando video…</div>
        )}

        {active && (
          <div
            className="pointer-events-none absolute inset-x-[8%] bottom-[26%] text-center leading-tight"
            style={{
              fontFamily: `"${style.font}", Arial, sans-serif`,
              fontWeight: style.bold ? 700 : 400,
              fontSize: `${style.font_size_pct}cqw`,
              textTransform: style.uppercase ? "uppercase" : "none",
              WebkitTextStroke: `${style.outline_width * 0.185}cqw ${style.outline_color}`,
              paintOrder: "stroke fill",
              textShadow: style.shadow ? `0 ${style.shadow * 0.1}cqw ${style.shadow * 0.25}cqw rgba(0,0,0,.6)` : undefined,
            }}
          >
            {active.line.map((w, i) => (
              <span key={i} style={{ color: style.highlight_active_word && i === active.wordIndex ? style.highlight_color : style.primary_color }}>
                {w.w}{i < active.line.length - 1 ? " " : ""}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button onClick={toggle} className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white/10 transition hover:bg-white/20 active:scale-95" aria-label={playing ? "Pausar" : "Reproducir"}>
          {playing ? <Pause className="h-4 w-4 fill-white" /> : <Play className="h-4 w-4 fill-white" />}
        </button>
        <button onClick={() => { if (ref.current) ref.current.currentTime = start; }} className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white/10 transition hover:bg-white/20 active:scale-95" aria-label="Reiniciar">
          <RotateCcw className="h-4 w-4" />
        </button>
        <input
          type="range" min={0} max={dur} step={0.05} value={Math.min(Math.max(t, 0), dur)}
          onChange={(e) => { if (ref.current) ref.current.currentTime = start + Number(e.target.value); }}
          className="min-w-0 flex-1"
        />
        <span className="w-[76px] shrink-0 text-right text-xs tabular-nums text-zinc-400">
          {fmtTime(Math.max(0, t), 1)} / {fmtTime(dur, 1)}
        </span>
      </div>
    </div>
  );
}
