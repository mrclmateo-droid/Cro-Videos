"use client";
import { ArrowLeft, Check, Minus, Plus, Save, Sparkles, Wand2, ZoomIn, Film, Type } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { PreviewPlayer } from "@/components/PreviewPlayer";
import { RenderPanel } from "@/components/RenderPanel";
import { MAX_CLIP, MIN_CLIP, Timeline } from "@/components/Timeline";
import { Badge, Button, Card, ErrorBanner, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { flattenWords, wordsForRange } from "@/lib/captions";
import { cn, clamp, errMsg, fmtTime, round2 } from "@/lib/format";
import type { Caption, CaptionStyle, Clip, Preset, Transcript, Video, Word } from "@/lib/types";

const FONTS = ["Liberation Sans", "DejaVu Sans"]; // las fuentes instaladas en el worker de render
const sig = (s: CaptionStyle) => JSON.stringify(Object.keys(s).sort().map((k) => [k, (s as Record<string, unknown>)[k]]));

function Nudge({ label, value, onNudge }: { label: string; value: number; onNudge: (d: number) => void }) {
  const btn = "grid h-8 min-w-[34px] place-items-center rounded-lg bg-white/10 px-1.5 text-[11px] transition hover:bg-white/20 active:scale-95";
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-zinc-400">{label}</span>
        <span className="text-sm font-medium tabular-nums">{fmtTime(value, 2)}</span>
      </div>
      <div className="grid grid-cols-4 gap-1.5">
        <button className={btn} onClick={() => onNudge(-1)}>−1 s</button>
        <button className={btn} onClick={() => onNudge(-0.1)}>−0.1</button>
        <button className={btn} onClick={() => onNudge(0.1)}>+0.1</button>
        <button className={btn} onClick={() => onNudge(1)}>+1 s</button>
      </div>
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button onClick={() => onChange(!checked)} className="flex w-full items-center justify-between rounded-xl bg-white/5 px-3 py-2 text-sm transition hover:bg-white/10">
      {label}
      <span className={cn("relative h-5 w-9 rounded-full transition", checked ? "bg-violet-500" : "bg-white/20")}>
        <span className={cn("absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all", checked ? "left-[18px]" : "left-0.5")} />
      </span>
    </button>
  );
}

function ColorField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="flex flex-col items-center gap-1.5 text-[11px] text-zinc-400">
      <input type="color" value={value} onChange={(e) => onChange(e.target.value)} className="h-9 w-full rounded-lg" />
      {label}
    </label>
  );
}

export default function ClipEditor() {
  const { id } = useParams<{ id: string }>();
  const [clip, setClip] = useState<Clip | null>(null);
  const [video, setVideo] = useState<Video | null>(null);
  const [caption, setCaption] = useState<Caption | null>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(0);
  const [preset, setPreset] = useState("");
  const [style, setStyle] = useState<CaptionStyle | null>(null);
  const [base, setBase] = useState<{ s: number; e: number } | null>(null);

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [current, setCurrent] = useState(0);
  const [seek, setSeek] = useState<{ t: number; n: number } | null>(null);
  const [autoRender, setAutoRender] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("autorender") === "1") {
      setAutoRender(true);
      window.history.replaceState(null, "", window.location.pathname); // evita re-render al recargar
    }
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const c = await api.getClip(id);
        const [v, cap, ps] = await Promise.all([api.getVideo(c.video_id), api.getCaptions(id), api.listPresets()]);
        if (!alive) return;
        setClip(c); setVideo(v); setCaption(cap); setPresets(ps);
        setStart(c.start); setEnd(c.end); setPreset(c.preset); setStyle(cap.style); setBase({ s: c.start, e: c.end });
        api.getSourceUrl(c.video_id).then((r) => alive && setSourceUrl(r.url)).catch((e) => alive && setError(errMsg(e)));
        api.getTranscript(c.video_id).then((t) => alive && setTranscript(t)).catch(() => undefined);
      } catch (e) {
        if (alive) setError(errMsg(e));
      }
    })();
    return () => { alive = false; };
  }, [id]);

  const allWords = useMemo<Word[]>(() => (transcript ? flattenWords(transcript.segments) : []), [transcript]);
  const words = useMemo<Word[]>(
    () => (transcript ? wordsForRange(allWords, start, end) : caption?.words ?? []),
    [transcript, allWords, start, end, caption],
  );

  const dirty = !!clip && !!caption && !!style &&
    (start !== clip.start || end !== clip.end || preset !== clip.preset || sig(style) !== sig(caption.style));

  const save = useCallback(async (): Promise<boolean> => {
    if (!clip || !style) return false;
    setSaving(true);
    try {
      const updated = await api.patchClip(clip.id, { start, end, preset });
      const cap = await api.saveCaptions(clip.id, { style, regenerate_words: false });
      setClip(updated); setCaption(cap);
      setStart(updated.start); setEnd(updated.end); setPreset(updated.preset); setStyle(cap.style);
      setSaved(true);
      setTimeout(() => setSaved(false), 1800);
      return true;
    } catch (e) {
      setError(errMsg(e));
      return false;
    } finally {
      setSaving(false);
    }
  }, [clip, style, start, end, preset]);

  const ensureSaved = useCallback(async () => (dirty ? save() : true), [dirty, save]);

  const duration = video?.duration ?? end;
  const seekTo = (t: number) => setSeek({ t, n: Date.now() });

  function nudge(which: "start" | "end", d: number) {
    if (which === "start") {
      const s = round2(clamp(start + d, Math.max(0, end - MAX_CLIP), end - MIN_CLIP));
      setStart(s); seekTo(s);
    } else {
      const e = round2(clamp(end + d, start + MIN_CLIP, Math.min(duration, start + MAX_CLIP)));
      setEnd(e); seekTo(Math.max(start, e - 2));
    }
  }

  function commit(which: "start" | "end") {
    // Al soltar la manija, se ajusta al límite de palabra más cercano para no cortar palabras a la mitad.
    const nearest = (t: number, key: "s" | "e") =>
      allWords.reduce<Word | null>((b, w) => (!b || Math.abs(w[key] - t) < Math.abs(b[key] - t) ? w : b), null);
    if (which === "start") {
      let s = start;
      const w = nearest(start, "s");
      if (w && Math.abs(w.s - start) <= 1) {
        const c = round2(Math.max(0, w.s - 0.12));
        if (end - c >= MIN_CLIP) s = c;
      }
      setStart(s); seekTo(s);
    } else {
      let e = end;
      const w = nearest(end, "e");
      if (w && Math.abs(w.e - end) <= 1) {
        const c = round2(Math.min(duration, w.e + 0.25));
        if (c - start >= MIN_CLIP) e = c;
      }
      setEnd(e); seekTo(Math.max(start, e - 2));
    }
  }

  const upd = (patch: Partial<CaptionStyle>) => setStyle((s) => (s ? { ...s, ...patch } : s));
  const applyPreset = (p: Preset) => { setPreset(p.id); setStyle({ ...p.caption_style }); };

  if (error && !clip) {
    return (
      <div className="space-y-4">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-300"><ArrowLeft className="h-4 w-4" /> Proyectos</Link>
        <ErrorBanner message={error} />
      </div>
    );
  }

  if (!clip || !style || !base) {
    return (
      <div className="grid gap-4 lg:grid-cols-[260px_1fr_320px]">
        <Skeleton className="h-64" /><Skeleton className="mx-auto h-[560px] w-[320px]" /><Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-16">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href={`/projects/${clip.project_id}`} className="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-300">
          <ArrowLeft className="h-4 w-4" /> Volver a los momentos
        </Link>
        <div className="flex items-center gap-2">
          {dirty && <Badge tone="violet">Cambios sin guardar</Badge>}
          <Button variant="primary" onClick={() => void save()} loading={saving} disabled={!dirty}>
            {saved ? <Check className="h-4 w-4" /> : <Save className="h-4 w-4" />} {saved ? "Guardado" : "Guardar"}
          </Button>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)_320px]">
        {/* IZQUIERDA: herramientas */}
        <aside className="order-3 space-y-4 lg:order-1">
          <Card className="space-y-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold"><Film className="h-4 w-4 text-violet-300" /> Recorte</h2>
            <Nudge label="Inicio" value={start} onNudge={(d) => nudge("start", d)} />
            <Nudge label="Fin" value={end} onNudge={(d) => nudge("end", d)} />
            <p className="text-xs text-zinc-500">
              Duración: {(end - start).toFixed(1)} s. También podés arrastrar las manijas en la timeline; se ajustan solas al límite de palabra.
            </p>
          </Card>
          <Card className="space-y-2">
            <h2 className="text-sm font-semibold">Herramientas</h2>
            {[
              { icon: Wand2, label: "Smart Cut" },
              { icon: ZoomIn, label: "Auto Zoom" },
              { icon: Sparkles, label: "AI B-Roll" },
              { icon: Type, label: "Hook Generator" },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center justify-between rounded-xl bg-white/[.03] px-3 py-2 text-sm text-zinc-500">
                <span className="flex items-center gap-2"><Icon className="h-4 w-4" /> {label}</span>
                <span className="text-[10px] uppercase tracking-wide">Próximamente</span>
              </div>
            ))}
          </Card>
        </aside>

        {/* CENTRO: preview */}
        <main className="order-1 min-w-0 lg:order-2">
          <PreviewPlayer src={sourceUrl} start={start} end={end} words={words} style={style} seek={seek} onTime={setCurrent} />
          <p className="mt-3 text-center text-[11px] text-zinc-600">Preview 9:16 con recorte centrado. Los subtítulos respetan la zona segura de Reels, TikTok y Shorts.</p>
        </main>

        {/* DERECHA: estilos y exportación */}
        <aside className="order-4 space-y-4 lg:order-3">
          <Card className="space-y-4">
            <h2 className="text-sm font-semibold">Estilo</h2>
            <div className="flex flex-wrap gap-2">
              {presets.map((p) => (
                <button key={p.id} onClick={() => applyPreset(p)}
                  className={cn("rounded-full border px-3 py-1.5 text-xs transition",
                    preset === p.id ? "border-violet-400 bg-violet-500/20 text-violet-100" : "border-white/10 bg-white/5 text-zinc-400 hover:text-zinc-200")}>
                  {p.label}
                </button>
              ))}
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-zinc-400"><span>Tamaño</span><span>{style.font_size_pct.toFixed(1)}</span></div>
              <input type="range" min={3} max={12} step={0.5} value={style.font_size_pct} className="w-full"
                     onChange={(e) => upd({ font_size_pct: Number(e.target.value) })} />
            </div>

            <div className="space-y-1.5">
              <span className="text-xs text-zinc-400">Fuente</span>
              <select value={style.font} onChange={(e) => upd({ font: e.target.value })}
                      className="h-10 w-full rounded-xl border border-white/10 bg-zinc-900 px-3 text-sm">
                {FONTS.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <ColorField label="Texto" value={style.primary_color} onChange={(v) => upd({ primary_color: v })} />
              <ColorField label="Resaltado" value={style.highlight_color} onChange={(v) => upd({ highlight_color: v })} />
              <ColorField label="Contorno" value={style.outline_color} onChange={(v) => upd({ outline_color: v })} />
            </div>

            <div className="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2 text-sm">
              Palabras por línea
              <span className="flex items-center gap-2">
                <button className="grid h-7 w-7 place-items-center rounded-lg bg-white/10 hover:bg-white/20" onClick={() => upd({ max_words: clamp(style.max_words - 1, 1, 8) })} aria-label="Menos"><Minus className="h-3.5 w-3.5" /></button>
                <span className="w-4 text-center tabular-nums">{style.max_words}</span>
                <button className="grid h-7 w-7 place-items-center rounded-lg bg-white/10 hover:bg-white/20" onClick={() => upd({ max_words: clamp(style.max_words + 1, 1, 8) })} aria-label="Más"><Plus className="h-3.5 w-3.5" /></button>
              </span>
            </div>

            <Toggle label="Resaltar palabra activa" checked={style.highlight_active_word} onChange={(v) => upd({ highlight_active_word: v })} />
            <Toggle label="Mayúsculas" checked={style.uppercase} onChange={(v) => upd({ uppercase: v })} />
            <Toggle label="Negrita" checked={style.bold} onChange={(v) => upd({ bold: v })} />
          </Card>

          <Card className="space-y-3">
            <h2 className="text-sm font-semibold">Exportar</h2>
            <RenderPanel clipId={clip.id} ensureSaved={ensureSaved} autoStart={autoRender} />
          </Card>
        </aside>

        {/* ABAJO: timeline */}
        <Card className="order-2 lg:order-4 lg:col-span-3">
          <Timeline
            duration={duration} start={start} end={end} current={current} words={words} maxWords={style.max_words}
            baseStart={base.s} baseEnd={base.e}
            onChange={(s, e) => { setStart(round2(s)); setEnd(round2(e)); }}
            onCommit={commit}
          />
        </Card>
      </div>
    </div>
  );
}
