export const cn = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

export function fmtTime(sec: number, decimals = 0): string {
  if (!isFinite(sec) || sec < 0) sec = 0;
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const sStr = (decimals ? s.toFixed(decimals) : String(Math.floor(s))).padStart(decimals ? 3 + decimals : 2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${sStr}` : `${m}:${sStr}`;
}

export function fmtSize(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
  return `${Math.max(1, Math.round(bytes / 1024 ** 2))} MB`;
}

export const errMsg = (e: unknown): string => (e instanceof Error ? e.message : String(e));
export const round2 = (x: number) => Math.round(x * 100) / 100;
export const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x));
