"use client";
import { Film, Link2, UploadCloud, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Button, Card, ErrorBanner, ProgressBar } from "./ui";
import { cn, errMsg, fmtSize, fmtTime } from "@/lib/format";
import { uploadVideo, type UploadHandle } from "@/lib/upload";
import type { Video } from "@/lib/types";

const MAX_BYTES = 5 * 1024 ** 3;
const EXT = [".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"];

type Meta = { duration?: number; width?: number; height?: number };
type State =
  | { kind: "idle" }
  | { kind: "uploading"; file: File; meta: Meta; pct: number }
  | { kind: "error"; file: File; meta: Meta; message: string };

function readMeta(file: File): Promise<Meta> {
  return new Promise((resolve) => {
    const v = document.createElement("video");
    const url = URL.createObjectURL(file);
    const done = (m: Meta) => { URL.revokeObjectURL(url); resolve(m); };
    v.preload = "metadata";
    v.onloadedmetadata = () => done({ duration: v.duration, width: v.videoWidth, height: v.videoHeight });
    v.onerror = () => done({});
    setTimeout(() => done({}), 4000);
    v.src = url;
  });
}

export function UploadZone({ projectId, onUploaded }: { projectId: string; onUploaded: (v: Video) => void }) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const handle = useRef<UploadHandle | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const start = useCallback(async (file: File, knownMeta?: Meta) => {
    const meta = knownMeta ?? (await readMeta(file));
    setState({ kind: "uploading", file, meta, pct: 0 });
    const h = uploadVideo(projectId, file, (pct) =>
      setState((s) => (s.kind === "uploading" ? { ...s, pct } : s)));
    handle.current = h;
    try {
      const video = await h.promise;
      onUploaded(video);
    } catch (e) {
      if ((e as Error).name === "AbortError") setState({ kind: "idle" });
      else setState({ kind: "error", file, meta, message: errMsg(e) });
    } finally {
      handle.current = null;
    }
  }, [projectId, onUploaded]);

  const pick = (file: File | undefined) => {
    if (!file) return;
    setLocalError(null);
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!EXT.includes(ext)) return setLocalError(`Formato no soportado. Usá: ${EXT.join(", ")}`);
    if (file.size > MAX_BYTES) return setLocalError("El archivo supera el máximo de 5 GB");
    void start(file);
  };

  if (state.kind !== "idle") {
    const { file, meta } = state;
    return (
      <Card className="animate-fade-up space-y-4">
        <div className="flex items-start gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-violet-500/15 text-violet-300"><Film className="h-5 w-5" /></div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium">{file.name}</p>
            <p className="text-xs text-zinc-400">
              {fmtSize(file.size)}
              {meta.duration ? ` · ${fmtTime(meta.duration)}` : ""}
              {meta.width ? ` · ${meta.width}×${meta.height}` : ""}
            </p>
          </div>
          {state.kind === "uploading" && (
            <Button size="sm" variant="ghost" onClick={() => handle.current?.cancel()} aria-label="Cancelar subida">
              <X className="h-4 w-4" /> Cancelar
            </Button>
          )}
        </div>
        {state.kind === "uploading" ? (
          <div className="space-y-2">
            <ProgressBar value={state.pct} />
            <p className="text-xs text-zinc-400">Subiendo… {Math.floor(state.pct)}%. No cierres esta pestaña.</p>
          </div>
        ) : (
          <div className="space-y-3">
            <ErrorBanner message={state.message} onRetry={() => void start(file, meta)} />
            <Button variant="ghost" size="sm" onClick={() => setState({ kind: "idle" })}>Elegir otro archivo</Button>
          </div>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files?.[0]); }}
        onClick={() => input.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-dashed p-10 text-center transition",
          dragging ? "border-violet-400 bg-violet-500/10" : "border-white/15 bg-white/[.03] hover:border-white/30",
        )}
      >
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-500 shadow-lg shadow-violet-900/40">
          <UploadCloud className="h-7 w-7 text-white" />
        </div>
        <div>
          <p className="text-base font-semibold">Subí un video largo</p>
          <p className="mt-1 text-sm text-zinc-400">Tocá para elegir un archivo o arrastralo acá · MP4, MOV, MKV, WebM · hasta 5 GB</p>
        </div>
        <input ref={input} type="file" accept="video/*,.mkv" className="hidden"
               onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }} />
      </div>
      {localError && <ErrorBanner message={localError} />}
      <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[.03] px-3 py-2 text-sm text-zinc-500">
        <Link2 className="h-4 w-4" /> Importar desde YouTube o Google Drive — próximamente
      </div>
    </div>
  );
}
