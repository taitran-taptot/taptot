/** Guest plan share tokens — claimed into account on login/register. */

import { migrateLocalKeys } from "./storageKeys";

export const GUEST_PLAN_TOKENS_KEY = "taptot_guest_plan_tokens";

migrateLocalKeys([
  ["tfit_guest_plan_tokens", GUEST_PLAN_TOKENS_KEY],
  ["vietfit_guest_plan_tokens", GUEST_PLAN_TOKENS_KEY],
]);
const MAX_STORED_GUEST_TOKENS = 50;

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export function getGuestPlanTokens(): string[] {
  const raw = storage()?.getItem(GUEST_PLAN_TOKENS_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((t): t is string => typeof t === "string" && t.length > 0);
  } catch {
    return [];
  }
}

export function saveGuestPlanTokens(tokens: string[]) {
  const s = storage();
  if (!s) return;
  const unique = [...new Set(tokens.filter(Boolean))];
  s.setItem(GUEST_PLAN_TOKENS_KEY, JSON.stringify(unique.slice(0, MAX_STORED_GUEST_TOKENS)));
}

export function addGuestPlanToken(token: string) {
  if (!token) return;
  const next = getGuestPlanTokens();
  if (!next.includes(token)) next.push(token);
  saveGuestPlanTokens(next);
}

export function clearGuestPlanTokens() {
  storage()?.removeItem(GUEST_PLAN_TOKENS_KEY);
}
