/** Only allow same-origin relative paths (block open redirects). */
export function safeNext(raw: string | null | undefined, fallback = "/tai-khoan"): string {
  if (!raw) return fallback;
  const next = raw.trim();
  if (!next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return fallback;
  if (next.includes("://") || next.includes("\\") || next.includes("%5c") || next.includes("%5C")) {
    return fallback;
  }
  return next;
}
