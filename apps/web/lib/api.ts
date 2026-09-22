import type {
  Caption, CaptionStyle, Clip, Highlight, Preset, Project, ProjectStatus, Render, Transcript,
  UploadStartOut, Video, Aspect, Resolution,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** En Codespaces deduce la URL de la API (puerto 8000) a partir de la del frontend (puerto 3000). */
export function apiBase(): string {
  const env = process.env.NEXT_PUBLIC_API_URL;
  if (env) return env.replace(/\/$/, "");
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    if (hostname.includes("-3000.")) return `${protocol}//${hostname.replace("-3000.", "-8000.")}`;
    return `${protocol}//${hostname}:8000`;
  }
  return "http://localhost:8000";
}

async function request<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...rest } = init;
  const headers: Record<string, string> = {};
  let body = rest.body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }
  let res: Response;
  try {
    res = await fetch(`${apiBase()}${path}`, { ...rest, headers, body });
  } catch {
    throw new ApiError(0, `No se pudo conectar con la API (${apiBase()}). ¿Está en marcha y con el puerto público?`);
  }
  if (!res.ok) {
    let detail = res.statusText || `Error ${res.status}`;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch { /* sin cuerpo JSON */ }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // proyectos
  listProjects: () => request<Project[]>("/projects"),
  createProject: (name: string) => request<Project>("/projects", { method: "POST", json: { name } }),
  getProjectStatus: (id: string) => request<ProjectStatus>(`/projects/${id}/status`),

  // subida
  startUpload: (projectId: string, body: { filename: string; size: number; content_type: string }) =>
    request<UploadStartOut>(`/projects/${projectId}/uploads`, { method: "POST", json: body }),
  completeUpload: (videoId: string, parts: { part_number: number; etag: string }[]) =>
    request<Video>(`/uploads/${videoId}/complete`, { method: "POST", json: { parts } }),
  abortUpload: (videoId: string) => request<void>(`/uploads/${videoId}/abort`, { method: "POST" }),

  // video
  getVideo: (id: string) => request<Video>(`/videos/${id}`),
  getSourceUrl: (id: string) => request<{ url: string; expires_in: number }>(`/videos/${id}/source-url`),
  getTranscript: (id: string) => request<Transcript>(`/videos/${id}/transcript`),
  getHighlights: (id: string) => request<Highlight[]>(`/videos/${id}/highlights`),
  reprocess: (id: string) => request<{ status: string }>(`/videos/${id}/reprocess`, { method: "POST" }),

  // clips
  listPresets: () => request<Preset[]>("/presets"),
  createClip: (body: { highlight_id?: string; video_id?: string; start?: number; end?: number; preset?: string }) =>
    request<Clip>("/clips", { method: "POST", json: body }),
  getClip: (id: string) => request<Clip>(`/clips/${id}`),
  patchClip: (id: string, body: { start?: number; end?: number; preset?: string }) =>
    request<Clip>(`/clips/${id}`, { method: "PATCH", json: body }),
  getCaptions: (clipId: string) => request<Caption>(`/clips/${clipId}/captions`),
  saveCaptions: (clipId: string, body: { style?: Partial<CaptionStyle>; regenerate_words?: boolean }) =>
    request<Caption>(`/clips/${clipId}/captions`, { method: "POST", json: body }),

  // render
  createRender: (clipId: string, body: { aspect: Aspect; resolution: Resolution }) =>
    request<Render>(`/clips/${clipId}/render`, { method: "POST", json: body }),
  getRender: (id: string) => request<Render>(`/renders/${id}`),
  getDownload: (exportId: string) =>
    request<{ url: string; expires_in: number; filename: string }>(`/exports/${exportId}/download`),
};
