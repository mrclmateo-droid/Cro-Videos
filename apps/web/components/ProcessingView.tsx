"use client";
import { Check, Loader2 } from "lucide-react";
import { Card, Skeleton } from "./ui";
import { cn, fmtSize, fmtTime } from "@/lib/format";
import type { Video } from "@/lib/types";

const STEPS = [
  { key: "uploading", label: "Subida" },
  { key: "transcribing", label: "Transcripción" },
  { key: "analyzing", label: "Análisis del audio" },
  { key: "finding_highlights", label: "Momentos destacados" },
];

export function ProcessingView({ status, video }: { status: string; video: Video | null }) {
  const current = Math.max(0, STEPS.findIndex((s) => s.key === status));
  return (
    <div className="space-y-4 animate-fade-up">
      <Card className="space-y-4">
        {video && (
          <div className="text-sm">
            <p className="truncate font-medium">{video.filename}</p>
            <p className="text-xs text-zinc-400">
              {fmtSize(video.size)}
              {video.duration ? ` · ${fmtTime(video.duration)}` : ""}
              {video.width ? ` · ${video.width}×${video.height}` : ""}
            </p>
          </div>
        )}
        <ol className="space-y-3">
          {STEPS.map((s, i) => (
            <li key={s.key} className="flex items-center gap-3 text-sm">
              <span className={cn(
                "grid h-6 w-6 place-items-center rounded-full text-xs",
                i < current ? "bg-emerald-500/20 text-emerald-300" : i === current ? "bg-violet-500/20 text-violet-300" : "bg-white/10 text-zinc-500",
              )}>
                {i < current ? <Check className="h-3.5 w-3.5" /> : i === current ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : i + 1}
              </span>
              <span className={cn(i > current && "text-zinc-500")}>{s.label}</span>
            </li>
          ))}
        </ol>
        <p className="text-xs text-zinc-500">Puede tardar varios minutos según la duración del video. Podés cerrar esta pantalla: el proceso sigue en el servidor.</p>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2">
        {[0, 1].map((i) => (
          <Card key={i} className="space-y-3">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-3 w-full" />
          </Card>
        ))}
      </div>
    </div>
  );
}
