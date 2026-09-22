"use client";
import { ChevronRight, FolderOpen, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { Button, Card, ErrorBanner, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { errMsg } from "@/lib/format";
import { PROCESSING } from "@/lib/status";
import type { Project } from "@/lib/types";

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <Card className="p-4">
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      <p className="text-xs text-zinc-500">{label}</p>
    </Card>
  );
}

export default function Dashboard() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try {
      setProjects(await api.listProjects());
      setError(null);
    } catch (e) {
      setError(errMsg(e));
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const busy = projects?.some((p) => PROCESSING.includes(p.status) || p.status === "uploading");
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [busy, load]);

  async function create() {
    setCreating(true);
    try {
      const p = await api.createProject(name.trim() || "Proyecto sin título");
      router.push(`/projects/${p.id}`);
    } catch (e) {
      setError(errMsg(e));
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tus proyectos</h1>
          <p className="text-sm text-zinc-500">Subí un video largo y la IA te propone los mejores clips.</p>
        </div>
        <Button variant="primary" onClick={() => setShowForm((s) => !s)}><Plus className="h-4 w-4" /> Nuevo proyecto</Button>
      </div>

      {showForm && (
        <Card className="animate-fade-up flex flex-col gap-3 sm:flex-row">
          <input
            autoFocus value={name} onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") void create(); }}
            placeholder="Nombre del proyecto (ej. Podcast episodio 12)"
            className="h-10 flex-1 rounded-xl border border-white/10 bg-black/30 px-3 text-sm outline-none placeholder:text-zinc-600 focus:border-violet-400"
          />
          <Button variant="primary" onClick={create} loading={creating}>Crear y subir video</Button>
        </Card>
      )}

      {error && <ErrorBanner message={error} onRetry={load} />}

      {projects && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Proyectos" value={projects.length} />
          <Stat label="Listos" value={projects.filter((p) => p.status === "ready").length} />
          <Stat label="En proceso" value={projects.filter((p) => PROCESSING.includes(p.status) || p.status === "uploading").length} />
          <Stat label="Con error" value={projects.filter((p) => p.status === "error").length} />
        </div>
      )}

      {!projects && !error && (
        <div className="space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-[68px] w-full" />)}</div>
      )}

      {projects && projects.length === 0 && (
        <Card className="flex flex-col items-center gap-3 py-12 text-center">
          <FolderOpen className="h-10 w-10 text-zinc-600" />
          <p className="text-zinc-400">Todavía no tenés proyectos.</p>
          <Button variant="primary" onClick={() => setShowForm(true)}><Plus className="h-4 w-4" /> Crear el primero</Button>
        </Card>
      )}

      <div className="space-y-2">
        {projects?.map((p) => (
          <Link key={p.id} href={`/projects/${p.id}`}
            className="flex animate-fade-up items-center gap-3 rounded-2xl border border-white/10 bg-white/[.04] p-4 transition hover:border-white/25 hover:bg-white/[.07]">
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{p.name}</p>
              <p className="text-xs text-zinc-500">{new Date(p.created_at).toLocaleString()}</p>
              {p.status === "error" && p.error && <p className="mt-1 truncate text-xs text-red-300">{p.error}</p>}
            </div>
            <StatusBadge status={p.status} />
            <ChevronRight className="h-4 w-4 text-zinc-600" />
          </Link>
        ))}
      </div>
    </div>
  );
}
