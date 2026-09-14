/** Normalize reps that may be a count ("12"), timed ("30s"), or minutes ("10 phút"). */

export type RepsMode = "count" | "seconds" | "minutes";

export function parseReps(raw: string | number | null | undefined): {
  mode: RepsMode;
  value: number;
  display: string;
} {
  if (raw == null || raw === "") {
    return { mode: "count", value: 12, display: "12" };
  }
  const s = String(raw).trim().toLowerCase();
  const minutes = s.match(/^(\d+)\s*(p|phút|phut|min|mins|m)$/i);
  if (minutes) {
    const n = Math.max(1, Math.min(120, parseInt(minutes[1], 10) || 10));
    return { mode: "minutes", value: n, display: `${n} phút` };
  }
  const timed = s.match(/^(\d+)\s*(s|sec|secs|giây|giay)?$/i);
  if (timed && (timed[2] || s.endsWith("s") || /giây|giay/.test(s))) {
    if (timed[2] || /s|giây|giay/.test(s)) {
      const n = Math.max(1, Math.min(600, parseInt(timed[1], 10) || 30));
      return { mode: "seconds", value: n, display: `${n}s` };
    }
  }
  if (/^\d+\s*s$/.test(s) || /^\d+s$/.test(s)) {
    const n = Math.max(1, Math.min(600, parseInt(s, 10) || 30));
    return { mode: "seconds", value: n, display: `${n}s` };
  }
  const n = Math.max(1, Math.min(100, parseInt(s, 10) || Number(raw) || 12));
  return { mode: "count", value: n, display: String(n) };
}

export function formatReps(mode: RepsMode, value: number): string {
  const n = Math.max(1, Math.round(value));
  if (mode === "minutes") return `${n} phút`;
  if (mode === "seconds") return `${n}s`;
  return String(n);
}

export function bumpReps(raw: string, delta: number): string {
  const parsed = parseReps(raw);
  const cap = parsed.mode === "minutes" ? 90 : parsed.mode === "seconds" ? 600 : 100;
  const step = parsed.mode === "minutes" ? (delta > 0 ? 1 : -1) : delta;
  const next = Math.max(1, Math.min(cap, parsed.value + step));
  return formatReps(parsed.mode, next);
}
