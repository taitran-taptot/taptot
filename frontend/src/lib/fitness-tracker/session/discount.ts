export const PUSHUP_DISCOUNT_KEY = "taptot_pushup_discount";
export const PUSHUP_IDLE_MS = 10_000;
export const PUSHUP_PREP_SEC = 15;
export const PUSHUP_ROUND_MS = 60_000;
export const PLANK_FORM_BREAK_MS = 5_000;
export const PLANK_SUCCESS_PERCENT = 10;

export type EventKind = "pushup" | "plank";
export type PushupDiscountPercent = 5 | 7 | 10 | 15;

export type PushupDiscount = {
  percent: PushupDiscountPercent;
  reps: number;
  at: number;
  ticket?: string;
  kind?: EventKind;
};

function isPushupDiscountPercent(value: unknown): value is PushupDiscountPercent {
  return value === 5 || value === 7 || value === 10 || value === 15;
}

/** 0 cái → không giảm. 1–20 → 5%, 21–50 → 10%, >50 → 15%. 7% still accepted on older tickets. */
export function discountPercentForReps(reps: number): 0 | 5 | 10 | 15 {
  if (reps <= 0) return 0;
  if (reps > 50) return 15;
  if (reps >= 21) return 10;
  return 5;
}

export function priceAfterDiscount(amount: number, percent: number): number {
  if (percent < 1) return amount;
  return Math.max(0, amount - Math.floor((amount * percent) / 100));
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
    const percent = isPushupDiscountPercent(payload.percent)
      ? payload.percent
      : discountPercentForReps(reps);
    if (!Number.isFinite(reps) || !isPushupDiscountPercent(percent)) return null;
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
  if (!isPushupDiscountPercent(percent)) return null;
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
    if (!parsed || !isPushupDiscountPercent(parsed.percent)) return null;
    return { ...parsed, kind: parsed.kind === "plank" ? "plank" : "pushup" };
  } catch {
    return null;
  }
}
