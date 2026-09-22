"use client";
import { ArrowLeft, RotateCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ProcessingView } from "@/components/ProcessingView";
import { Results } from "@/components/Results";
import { StatusBadge } from "@/components/StatusBadge";
import { UploadZone } from "@/components/UploadZone";
import { Button, ErrorBanner, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { errMsg } from "@/lib/format";
import { PROCESSING } from "@/lib/status";
import type { ProjectStatus } from "@/lib/types";

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ProjectStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reupload, setReupload] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setData(await api.getProjectStatus(id));
      setError(null);
    } catch (e) {
      setError(errMsg(e));
    }
  }, [id]);

  useEffect(() => { void refresh(); }, [refresh]);

  const status = data?.project.status;
  useEffect(() => {
    if (!status || !PROCESSING.includes(status)) return;
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, [status, refresh]);

  const onUploaded = useCallback(() => { setReupload(false); void refresh(); }, [refresh]);

  async function retry() {
    if (!data?.video) return;
    setRetrying(true);
    try {
      await api.reprocess(data.video.id);
      await refresh();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setRetrying(false);
    }
  }

  const video = data?.video ?? null;
  const uploaded = video?.upload_status === "uploaded";
  const needsUpload = reupload || status === "created" || status === "uploading" || (status === "error" && !uploaded);

  return (
    <div className="space-y-5">
      <div>
        <Link href="/" className="mb-3 inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-300">
          <ArrowLeft className="h-4 w-4" /> Proyectos
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          {data ? <h1 className="text-2xl font-semibold tracking-tight">{data.project.name}</h1> : <Skeleton className="h-8 w-56" />}
          {status && <StatusBadge status={status} />}
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={refresh} />}
      {!data && !error && <Skeleton className="h-48 w-full" />}

      {data && needsUpload && (
        <>
          {status === "error" && data.project.error && !reupload && <ErrorBanner message={data.project.error} />}
          <UploadZone projectId={id} onUploaded={onUploaded} />
        </>
      )}

      {data && !needsUpload && status && PROCESSING.includes(status) && <ProcessingView status={status} video={video} />}

      {data && !needsUpload && status === "error" && uploaded && (
        <div className="space-y-3">
          <ErrorBanner message={data.project.error ?? "El procesamiento falló"} />
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" onClick={retry} loading={retrying}><RotateCw className="h-4 w-4" /> Reintentar procesamiento</Button>
            <Button onClick={() => setReupload(true)}>Subir otro video</Button>
          </div>
        </div>
      )}

      {data && !needsUpload && status === "ready" && video && <Results video={video} />}
    </div>
  );
}
