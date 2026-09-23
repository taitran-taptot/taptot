import { apiFetch } from "./http";

export type ChallengeCheckout = {
  transaction_id: number;
  external_id: string;
  amount_vnd: number;
  pay_url: string;
  provider: string;
  stub: boolean;
};

export type ChallengePayStatus = {
  external_id: string;
  status: string;
  amount_vnd: number;
  stub: boolean;
  entitlement_token?: string | null;
  consumed?: boolean;
};

const guest = { auth: true as const, requireAuth: false };

export const challengePayApi = {
  checkout: () =>
    apiFetch<ChallengeCheckout>("/payments/challenge-checkout", { method: "POST" }, guest),
  status: (externalId: string) =>
    apiFetch<ChallengePayStatus>(`/payments/challenge/${encodeURIComponent(externalId)}`),
  simulate: (externalId: string) =>
    apiFetch<ChallengePayStatus>(
      `/payments/challenge/${encodeURIComponent(externalId)}/simulate`,
      { method: "POST" },
      guest,
    ),
};

export const CHALLENGE_PAY_ENTITLEMENT_KEY = "taptot_challenge_pay_entitlement";
export const CHALLENGE_GATE_CONTINUE_KEY = "taptot_challenge_gate_continue";

function sessionStore(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function loadChallengeEntitlement(): string {
  return sessionStore()?.getItem(CHALLENGE_PAY_ENTITLEMENT_KEY) || "";
}

export function saveChallengeEntitlement(token: string): void {
  const s = sessionStore();
  if (!s) return;
  if (token) s.setItem(CHALLENGE_PAY_ENTITLEMENT_KEY, token);
  else s.removeItem(CHALLENGE_PAY_ENTITLEMENT_KEY);
}

export function clearChallengeEntitlement(): void {
  sessionStore()?.removeItem(CHALLENGE_PAY_ENTITLEMENT_KEY);
}

export function markChallengeGateContinue(): void {
  sessionStore()?.setItem(CHALLENGE_GATE_CONTINUE_KEY, "1");
}

export function consumeChallengeGateContinue(): boolean {
  const s = sessionStore();
  if (!s) return false;
  const hit = s.getItem(CHALLENGE_GATE_CONTINUE_KEY) === "1";
  if (hit) s.removeItem(CHALLENGE_GATE_CONTINUE_KEY);
  return hit;
}
