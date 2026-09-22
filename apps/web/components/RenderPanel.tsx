"use client";
import { CheckCircle2, Download } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button, ErrorBanner, ProgressBar } from "./ui";
import { api } from "@/lib/api";
import { cn, errMsg } from "@/lib/format";
import type { Aspect, Render, Resolution } from "@/lib/types";

const ASPECTS: { id: Aspect; label: string; hint: string }[] = [
  { id: "9:16", label: "9:16", hint: "Reels · TikTok · Shorts" },
  { id: "1:1", label: "1:1", hint: "Feed" },
  { id: "16:9", label: "16:9", hint: "YouTube" },
];

export function RenderPanel({ clipId, ensureSaved, autoStart }: { clipId: string; ensureSaved: () => Promise<boolean>; autoStart: boolean }) {
  const [aspect, setAspect] = useState<Aspect>("9:16");
  const [resolution, setResolution] = useState<Resolution>("1080p");
  const [render, setRender] = useState<Render | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const started = useRef(false);

  const inProgress = render && (render.status === "queued" || render.status === "rendering");

  async function start(a: Aspect = aspect, r: Resolution = resolution) {
    setError(null);
    setStarting(true);
    try {
      if (!(await ensureSaved())) throw new Error("No se pudieron guardar los cambios antes de renderizar");
      setRender(await api.createRender(clipId, { aspect: a, resolution: r }));
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setStarting(false);
    }
  }

  useEffect(() => {
    if (autoStart && !started.current) {
      started.current = true;
      void start("9:16", "1080p");
    }
  }, [autoStart]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!render || !inProgress) return;
    const id = setInterval(async () => {
      try { setRender(await api.getRender(render.id)); } catch (e) { setError(errMsg(e)); }
    }, 1500);
    return () => clearInterval(id);
  }, [render?.id, inProgress]); // eslint-disable-line react-hooks/exhaustive-deps

  async function download() {
    if (!render?.export_id) return;
    setDownloading(true);
    try {
      const d = await api.getDownload(render.export_id);
      window.location.href = d.url;
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <p className="text-xs text-zinc-400">Formato</p>
        <div className="grid grid-cols-3 gap-2">
          {ASPECTS.map((a) => (
            <button key={a.id} onClick={() => setAspect(a.id)} disabled={!!inProgress}
              className={cn("rounded-xl border px-2 py-2 text-center transition disabled:opacity-50",
                aspect === a.id ? "border-violet-400 bg-violet-500/20" : "border-white/10 bg-white/5 hover:bg-white/10")}>
              <span className="block text-sm font-medium">{a.label}</span>
              <span className="block text-[10px] text-zinc-400">{a.hint}</span>
            </button>
          ))}
        </div>
        <p className="pt-1 text-xs text-zinc-400">Resolución</p>
        <div className="grid grid-cols-2 gap-2">
          {(["720p", "1080p"] as Resolution[]).map((r) => (
            <button key={r} onClick={() => setResolution(r)} disabled={!!inProgress}
              className={cn("rounded-xl border px-2 py-2 text-sm transition disabled:opacity-50",
                resolution === r ? "border-violet-400 bg-violet-500/20" : "border-white/10 bg-white/5 hover:bg-white/10")}>
              {r}
            </button>
          ))}
        </div>
      </div>

      {render && inProgress && (
        <div className="space-y-2">
          <ProgressBar value={render.status === "queued" ? undefined : render.progress} indeterminate={render.status === "queued"} />
          <p className="text-xs text-zinc-400">
            {render.status === "queued" ? "En cola…" : `Renderizando… ${Math.floor(render.progress)}%`}
          </p>
        </div>
      )}

      {render?.status === "completed" && (
        <div className="space-y-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3">
          <p className="flex items-center gap-2 text-sm text-emerald-300"><CheckCircle2 className="h-4 w-4" /> Reel listo</p>
          <Button variant="primary" className="w-full" onClick={download} loading={downloading}>
            <Download className="h-4 w-4" /> Descargar MP4
          </Button>
        </div>
      )}

      {render?.status === "error" && <ErrorBanner message={render.error ?? "El render falló"} onRetry={() => void start()} />}
      {error && <ErrorBanner message={error} />}

      {!inProgress && (
        <Button variant="primary" className="w-full" onClick={() => start()} loading={starting}>
          {render?.status === "completed" ? "Renderizar de nuevo" : "Generar Reel"}
        </Button>
      )}
    </div>
  );
}
