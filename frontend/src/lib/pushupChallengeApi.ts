import { apiFetch } from "@/lib/http";

export type PushupChallengeFinishResult = {
  ticket: string;
  reps: number;
  percent: number;
  session_id: string;
};

export const pushupChallengeApi = {
  startSession: () =>
    apiFetch<{ session_id: string }>("/pushup-challenge/sessions", { method: "POST" }, { auth: false }),
  finishSession: (sessionId: string, reps: number) =>
    apiFetch<PushupChallengeFinishResult>(
      `/pushup-challenge/sessions/${encodeURIComponent(sessionId)}/finish`,
      { method: "POST", body: JSON.stringify({ reps }) },
      { auth: false },
    ),
  verifyTicket: (ticket: string) =>
    apiFetch<{ valid: boolean; reps?: number; percent?: number }>(
      "/pushup-challenge/tickets/verify",
      { method: "POST", body: JSON.stringify({ ticket }) },
      { auth: false },
    ),
};
