export const PUSHUP_DISCOUNT_KEY = "taptot_pushup_discount";
export const PUSHUP_IDLE_MS = 10_000;
export const PUSHUP_PREP_SEC = 15;
export const PUSHUP_ROUND_MS = 60_000;
export const PLANK_FORM_BREAK_MS = 5_000;
export const PLANK_SUCCESS_PERCENT = 10;

export const PUSHUP_SCORE_CAP = 100;

export type EventKind = "pushup" | "plank";

export type PushupDiscount = {
  percent: number;
  reps: number;
  at: number;
  ticket?: string;
  kind?: EventKind;
};

/** 0.2% per rep, capped at 100 reps (20%). Signed legacy tickets may still be 5, 7, 10, or 15. */
export function discountPercentForReps(reps: number): number {
  const counted = Math.min(PUSHUP_SCORE_CAP, Math.max(0, Math.floor(reps)));
  return (counted * 2) / 10;
}

/** One decimal, Vietnamese comma: 0.2 → "0,2", 5 → "5". */
export function formatDiscountPercent(percent: number): string {
  const tenths = Math.round(Number(percent) * 10);
  if (!Number.isFinite(tenths)) return "0";
  const sign = tenths < 0 ? "-" : "";
  const abs = Math.abs(tenths);
  const whole = Math.floor(abs / 10);
  const frac = abs % 10;
  return frac === 0 ? `${sign}${whole}` : `${sign}${whole},${frac}`;
}

function acceptPercent(value: unknown): number | null {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0 || n > 20) return null;
  return Math.round(n * 10) / 10;
}

export function priceAfterDiscount(amount: number, percent: number): number {
  if (!(percent > 0)) return amount;
  const tenths = Math.round(percent * 10);
  return Math.max(0, amount - Math.floor((amount * tenths) / 1000));
}

/** True once invalid plank form has lasted the fail window. */
export function plankFormBreakDue(
  brokenSince: number | null,
  now: number,
  windowMs = PLANK_FORM_BREAK_MS,
): boolean {
  return brokenSince != null && now - brokenSince >= windowMs;
}

export function pushupIdleExpired(lastActivityAt: number, now: number, windowMs = PUSHUP_IDLE_MS): boolean {
  return now - lastActivityAt >= windowMs;
}

export function pushupRoundExpired(startedAt: number, now: number, roundMs = PUSHUP_ROUND_MS): boolean {
  return now - startedAt >= roundMs;
}

/** Start the 10s idle countdown only when more than 10s of the minute remains. */
export function pushupIdleCountdownDue(
  lastRepAt: number,
  now: number,
  roundStartedAt: number,
  idleMs = PUSHUP_IDLE_MS,
  roundMs = PUSHUP_ROUND_MS,
): boolean {
  const remaining = roundMs - (now - roundStartedAt);
  return now - lastRepAt >= idleMs && remaining > idleMs;
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
    const payload = b64urlJson(parts[1]) as {
      type?: string;
      reps?: number;
      percent?: number;
      exp?: number;
      kind?: string;
    };
    if (payload?.type && payload.type !== "pushup_ticket") return null;
    const exp = Number(payload.exp);
    if (Number.isFinite(exp) && exp > 0 && Date.now() / 1000 >= exp) return null;
    const reps = Math.max(0, Math.round(Number(payload.reps)));
    const percent = acceptPercent(payload.percent) ?? discountPercentForReps(reps);
    if (!Number.isFinite(reps) || !(percent > 0)) return null;
    const kind: EventKind = payload.kind === "plank" ? "plank" : "pushup";
    return { percent, reps, at: Date.now(), ticket, kind };
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

export function savePushupDiscount(reps: number): PushupDiscount | null {
  const percent = discountPercentForReps(Math.max(0, Math.round(reps)));
  if (!(percent > 0)) return null;
  const record: PushupDiscount = {
    percent,
    reps: Math.max(0, Math.round(reps)),
    at: Date.now(),
    kind: "pushup",
  };
  store()?.setItem(PUSHUP_DISCOUNT_KEY, JSON.stringify(record));
  return record;
}

export function savePlankDiscount(): PushupDiscount {
  const record: PushupDiscount = {
    percent: PLANK_SUCCESS_PERCENT,
    reps: 0,
    at: Date.now(),
    kind: "plank",
  };
  store()?.setItem(PUSHUP_DISCOUNT_KEY, JSON.stringify(record));
  return record;
}

export function clearPushupDiscount(): void {
  store()?.removeItem(PUSHUP_DISCOUNT_KEY);
}

export function loadPushupDiscount(): PushupDiscount | null {
  const raw = store()?.getItem(PUSHUP_DISCOUNT_KEY);
  if (!raw) return null;
  if (raw.split(".").length >= 3) {
    const parsed = parsePushupTicket(raw);
    if (!parsed) clearPushupDiscount();
    return parsed;
  }
  try {
    const parsed = JSON.parse(raw) as PushupDiscount;
    if (!parsed || acceptPercent(parsed.percent) == null) return null;
    parsed.percent = acceptPercent(parsed.percent) as number;
    return { ...parsed, kind: parsed.kind === "plank" ? "plank" : "pushup" };
  } catch {
    return null;
  }
}
