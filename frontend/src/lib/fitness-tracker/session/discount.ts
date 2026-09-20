export const PUSHUP_DISCOUNT_KEY = "taptot_pushup_discount";

export type PushupDiscount = {
  percent: 5 | 7 | 10;
  reps: number;
  at: number;
};

/** 0–20 → 5%, 21–50 → 7%, >50 → 10%. */
export function discountPercentForReps(reps: number): 5 | 7 | 10 {
  if (reps > 50) return 10;
  if (reps >= 21) return 7;
  return 5;
}

function store(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
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
  try {
    const parsed = JSON.parse(raw) as PushupDiscount;
    if (!parsed || (parsed.percent !== 5 && parsed.percent !== 7 && parsed.percent !== 10)) return null;
    return parsed;
  } catch {
    return null;
  }
}
