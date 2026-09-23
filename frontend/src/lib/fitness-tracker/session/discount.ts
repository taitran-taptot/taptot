export const PUSHUP_DISCOUNT_KEY = "taptot_pushup_discount";
export const PUSHUP_IDLE_MS = 10_000;
export const PUSHUP_PREP_SEC = 15;
export const PUSHUP_ROUND_MS = 60_000;

export type PushupDiscountPercent = 5 | 7 | 10 | 15;

export type PushupDiscount = {
  percent: PushupDiscountPercent;
  reps: number;
  at: number;
  ticket?: string;
};

function isPushupDiscountPercent(value: unknown): value is PushupDiscountPercent {
  return value === 5 || value === 7 || value === 10 || value === 15;
}

/** 0–20 → 5%, 21–50 → 10%, >50 → 15%. 7% still accepted on older tickets. */
export function discountPercentForReps(reps: number): 5 | 10 | 15 {
  if (reps > 50) return 15;
  if (reps >= 21) return 10;
  return 5;
}

export function pushupIdleExpired(lastActivityAt: number, now: number, windowMs = PUSHUP_IDLE_MS): boolean {
  return now - lastActivityAt >= windowMs;
}

export function pushupRoundExpired(startedAt: number, now: number, roundMs = PUSHUP_ROUND_MS): boolean {
  return now - startedAt >= roundMs;
}

function store(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function b64urlJson(segment: string): unknown {
  const pad = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padded = pad + "=".repeat((4 - (pad.length % 4)) % 4);
  return JSON.parse(atob(padded));
}

export function parsePushupTicket(ticket: string): PushupDiscount | null {
  const parts = ticket.split(".");
  if (parts.length < 2) return null;
  try {
    const payload = b64urlJson(parts[1]) as { type?: string; reps?: number; percent?: number };
    if (payload?.type && payload.type !== "pushup_ticket") return null;
    const reps = Math.max(0, Math.round(Number(payload.reps)));
    const percent = isPushupDiscountPercent(payload.percent)
      ? payload.percent
      : discountPercentForReps(reps);
    if (!Number.isFinite(reps)) return null;
    return { percent, reps, at: Date.now(), ticket };
  } catch {
    return null;
  }
}

export function savePushupTicket(ticket: string): PushupDiscount | null {
  const parsed = parsePushupTicket(ticket);
  if (!parsed) return null;
  store()?.setItem(PUSHUP_DISCOUNT_KEY, ticket);
  return parsed;
}

export function savePushupDiscount(reps: number): PushupDiscount {
  const record: PushupDiscount = {
    percent: discountPercentForReps(Math.max(0, Math.round(reps))),
    reps: Math.max(0, Math.round(reps)),
    at: Date.now(),
  };
  store()?.setItem(PUSHUP_DISCOUNT_KEY, JSON.stringify(record));
  return record;
}

export function loadPushupDiscount(): PushupDiscount | null {
  const raw = store()?.getItem(PUSHUP_DISCOUNT_KEY);
  if (!raw) return null;
  if (raw.split(".").length >= 3) return parsePushupTicket(raw);
  try {
    const parsed = JSON.parse(raw) as PushupDiscount;
    if (!parsed || !isPushupDiscountPercent(parsed.percent)) return null;
    return parsed;
  } catch {
    return null;
  }
}
