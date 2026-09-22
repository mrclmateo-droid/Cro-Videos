"use client";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { HighlightCard } from "./HighlightCard";
import { Button, Card, ErrorBanner, Skeleton } from "./ui";
import { api } from "@/lib/api";
import { cn, errMsg } from "@/lib/format";
import { CATEGORIES } from "@/lib/status";
import type { Highlight, Video } from "@/lib/types";

const DURATIONS = [
  { id: "all", label: "Todas", min: 0, max: Infinity },
  { id: "15-30", label: "15–30 s", min: 15, max: 30 },
  { id: "30-60", label: "30–60 s", min: 30, max: 60 },
  { id: "60-90", label: "60–90 s", min: 60, max: 90.01 },
];

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={cn("shrink-0 rounded-full border px-3 py-1.5 text-xs transition",
        active ? "border-violet-400 bg-violet-500/20 text-violet-200" : "border-white/10 bg-white/5 text-zinc-400 hover:text-zinc-200")}>
      {children}
    </button>
  );
}

export function Results({ video }: { video: Video }) {
  const router = useRouter();
  const [items, setItems] = useState<Highlight[] | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dur, setDur] = useState("all");
  const [cat, setCat] = useState("all");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.getHighlights(video.id).then(setItems).catch((e) => setError(errMsg(e)));
    api.getSourceUrl(video.id).then((r) => setSourceUrl(r.url)).catch(() => setSourceUrl(null));
  }, [video.id]);

  const filtered = useMemo(() => {
    const d = DURATIONS.find((x) => x.id === dur)!;
    return (items ?? []).filter((h) => h.duration >= d.min && h.duration < d.max && (cat === "all" || h.category === cat));
  }, [items, dur, cat]);

  async function manualClip() {
    setCreating(true);
    try {
      const end = Math.min(30, video.duration ?? 30);
      const clip = await api.createClip({ video_id: video.id, start: 0, end });
      router.push(`/clips/${clip.id}`);
    } catch (e) {
      setError(errMsg(e));
      setCreating(false);
    }
  }

  if (!items && !error) {
    return <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2].map((i) => <Card key={i}><Skeleton className="h-72 w-full" /></Card>)}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">
            {items && items.length > 0 ? `Encontramos ${items.length} momento${items.length === 1 ? "" : "s"} destacado${items.length === 1 ? "" : "s"}` : "No encontramos momentos destacados"}
          </h2>
          <p className="text-sm text-zinc-500">Ordenados por el indicador heurístico de potencial.</p>
        </div>
        <Button onClick={manualClip} loading={creating}><Plus className="h-4 w-4" /> Clip manual</Button>
      </div>

      {error && <ErrorBanner message={error} />}

      {items && items.length > 0 && (
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
          {DURATIONS.map((d) => <Chip key={d.id} active={dur === d.id} onClick={() => setDur(d.id)}>{d.label}</Chip>)}
          <span className="mx-1 w-px shrink-0 bg-white/10" />
          <Chip active={cat === "all"} onClick={() => setCat("all")}>Todos</Chip>
          {Object.entries(CATEGORIES).map(([k, label]) => <Chip key={k} active={cat === k} onClick={() => setCat(k)}>{label}</Chip>)}
        </div>
      )}

      {items && items.length > 0 && filtered.length === 0 && (
        <p className="py-8 text-center text-sm text-zinc-500">Ningún momento coincide con esos filtros.</p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((h) => <HighlightCard key={h.id} h={h} sourceUrl={sourceUrl} onError={setError} />)}
      </div>
    </div>
  );
}
