import { api, apiBase, ApiError } from "./api";
import type { UploadStartOut, Video } from "./types";

export type UploadHandle = { promise: Promise<Video>; cancel: () => void };

class NetworkError extends Error {}
/** El almacenamiento no es alcanzable desde el navegador (CORS/red): se usa la subida a través de la API. */
class FallbackError extends Error {}

const abortError = () => new DOMException("Cancelado", "AbortError");
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

type XhrResult = { status: number; etag: string | null; text: string };

function xhrSend(
  method: "PUT" | "POST", url: string, body: Blob | FormData,
  signal: AbortSignal, onProgress?: (loaded: number) => void,
): Promise<XhrResult> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(abortError());
    const xhr = new XMLHttpRequest();
    xhr.open(method, url);
    xhr.upload.onprogress = (e) => onProgress?.(e.loaded);
    xhr.onload = () => resolve({ status: xhr.status, etag: xhr.getResponseHeader("ETag"), text: xhr.responseText });
    xhr.onerror = () => reject(new NetworkError("Error de red"));
    xhr.onabort = () => reject(abortError());
    signal.addEventListener("abort", () => xhr.abort(), { once: true });
    xhr.send(body);
  });
}

async function multipartUpload(
  file: File, start: UploadStartOut, signal: AbortSignal, onProgress: (pct: number) => void,
): Promise<{ part_number: number; etag: string }[]> {
  const { part_size, parts } = start;
  const inner = new AbortController();
  signal.addEventListener("abort", () => inner.abort(), { once: true });

  const loaded: number[] = new Array(parts.length).fill(0);
  const report = () => onProgress(Math.min(99, (loaded.reduce((a, b) => a + b, 0) / file.size) * 100));
  const results: { part_number: number; etag: string }[] = new Array(parts.length);
  let next = 0;
  let succeeded = 0;

  async function worker() {
    for (;;) {
      const i = next++;
      if (i >= parts.length) return;
      const part = parts[i];
      const blob = file.slice(i * part_size, Math.min(file.size, (i + 1) * part_size));
      let attempt = 0;
      for (;;) {
        try {
          loaded[i] = 0;
          const r = await xhrSend("PUT", part.url, blob, inner.signal, (l) => { loaded[i] = l; report(); });
          if (r.status < 200 || r.status >= 300) throw new Error(`Parte ${part.part_number}: HTTP ${r.status}`);
          if (!r.etag) throw new FallbackError("El almacenamiento no expone el ETag");
          results[i] = { part_number: part.part_number, etag: r.etag };
          loaded[i] = blob.size;
          succeeded++;
          report();
          break;
        } catch (e) {
          if (e instanceof FallbackError || (e as Error).name === "AbortError") throw e;
          if (e instanceof NetworkError && succeeded === 0) throw new FallbackError("Almacenamiento inalcanzable");
          if (++attempt >= 3) throw e;
          await sleep(1000 * attempt); // reintento de la parte con espera creciente
        }
      }
    }
  }

  try {
    await Promise.all(Array.from({ length: Math.min(3, parts.length) }, worker));
  } catch (e) {
    inner.abort();
    throw e;
  }
  return results;
}

async function directUpload(
  projectId: string, file: File, signal: AbortSignal, onProgress: (pct: number) => void,
): Promise<Video> {
  const form = new FormData();
  form.append("file", file, file.name);
  let r: XhrResult;
  try {
    r = await xhrSend("POST", `${apiBase()}/projects/${projectId}/upload-direct`, form, signal,
      (l) => onProgress(Math.min(99, (l / file.size) * 100)));
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, "No se pudo conectar con la API para subir el video");
  }
  if (r.status < 200 || r.status >= 300) {
    let detail = `Error ${r.status}`;
    try { detail = JSON.parse(r.text).detail ?? detail; } catch { /* sin JSON */ }
    throw new ApiError(r.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return JSON.parse(r.text) as Video;
}

/** Subida multipart directa al storage con URLs firmadas. Si el navegador no puede llegar al storage,
 *  cae automáticamente a la subida a través de la API. */
export function uploadVideo(projectId: string, file: File, onProgress: (pct: number) => void): UploadHandle {
  const ctrl = new AbortController();
  const promise = (async () => {
    const start = await api.startUpload(projectId, {
      filename: file.name, size: file.size, content_type: file.type || "video/mp4",
    });
    try {
      const parts = await multipartUpload(file, start, ctrl.signal, onProgress);
      return await api.completeUpload(start.video_id, parts);
    } catch (e) {
      await api.abortUpload(start.video_id).catch(() => undefined); // limpia la subida a medias
      if (ctrl.signal.aborted) throw abortError();
      if (e instanceof FallbackError) {
        onProgress(0);
        return await directUpload(projectId, file, ctrl.signal, onProgress);
      }
      throw e;
    }
  })();
  return { promise, cancel: () => ctrl.abort() };
}
