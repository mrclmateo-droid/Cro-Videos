"use client";
import { ChevronDown, Clapperboard, Pencil, Play, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge, Button, Card, ProgressBar, Tooltip } from "./ui";
import { api } from "@/lib/api";
import { cn, errMsg, fmtTime } from "@/lib/format";
import { CATEGORIES, SCORE_LABELS } from "@/lib/status";
import type { Highlight } from "@/lib/types";

export function HighlightCard({ h, sourceUrl, onError }: { h: Highlight; sourceUrl: string | null; onError: (m: string) => void }) {
  const router = useRouter();
  const [playing, setPlaying] = useState(false);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<"edit" | "reel" | null>(null);

  async function go(mode: "edit" | "reel") {
    setBusy(mode);
    try {
      const clip = await api.createClip({ highlight_id: h.id });
      router.push(`/clips/${clip.id}${mode === "reel" ? "?autorender=1" : ""}`);
    } catch (e) {
      onError(errMsg(e));
      setBusy(null);
    }
  }

  const tone = h.overall >= 75 ? "green" : h.overall >= 55 ? "violet" : "gray";

  return (
    <Card className="flex animate-fade-up flex-col gap-3 p-3">
      <div className="relative mx-auto aspect-[9/16] max-h-[380px] w-full overflow-hidden rounded-xl bg-black">
        {playing && sourceUrl ? (
          <video
            src={`${sourceUrl}#t=${h.start},${h.end}`}
            className="h-full w-full object-cover"
            autoPlay playsInline controls
            onLoadedMetadata={(e) => { e.currentTarget.currentTime = h.start; }}
            onTimeUpdate={(e) => { if (e.currentTarget.currentTime >= h.end) e.currentTarget.pause(); }}
          />
        ) : (
          <button
            onClick={() => setPlaying(true)}
            disabled={!sourceUrl}
            className="group grid h-full w-full place-items-center bg-gradient-to-b from-zinc-800 to-zinc-950 disabled:opacity-50"
            aria-label="Ver preview"
          >
            <span className="grid h-14 w-14 place-items-center rounded-full bg-white/15 backdrop-blur transition group-hover:scale-110">
              <Play className="h-6 w-6 fill-white text-white" />
            </span>
            <span className="absolute bottom-3 rounded-full bg-black/50 px-3 py-1 text-xs">
              {fmtTime(h.start)} – {fmtTime(h.end)} · {Math.round(h.duration)} s
            </span>
          </button>
        )}
      </div>

      <div className="space-y-2 px-1">
        <div className="flex flex-wrap items-center gap-2">
          {h.category && <Badge tone="blue">{CATEGORIES[h.category] ?? h.category}</Badge>}
          <Tooltip text="Indicador heurístico basado en el análisis del contenido (gancho, claridad, emoción, etc.). Ayuda a elegir; no es una predicción de viralidad.">
            <Badge tone={tone}><Sparkles className="h-3 w-3" /> Potencial {Math.round(h.overall)}/100</Badge>
          </Tooltip>
        </div>
        <h3 className="font-semibold leading-snug">{h.title}</h3>
        <p className="text-sm text-zinc-400">{h.reason}</p>

        <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300">
          <ChevronDown className={cn("h-3.5 w-3.5 transition", open && "rotate-180")} /> Ver detalle del análisis
        </button>
        {open && (
          <div className="grid grid-cols-1 gap-x-4 gap-y-1.5 pt-1">
            {Object.entries(h.scores).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2 text-xs text-zinc-400">
                <span className="w-32 shrink-0">{SCORE_LABELS[k] ?? k}</span>
                <ProgressBar value={v * 10} className="h-1.5" />
                <span className="w-6 text-right tabular-nums">{Math.round(v)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-auto grid grid-cols-2 gap-2">
        <Button onClick={() => go("edit")} loading={busy === "edit"} disabled={busy !== null}><Pencil className="h-4 w-4" /> Editar</Button>
        <Button variant="primary" onClick={() => go("reel")} loading={busy === "reel"} disabled={busy !== null}>
          <Clapperboard className="h-4 w-4" /> Generar Reel
        </Button>
      </div>
    </Card>
  );
}
