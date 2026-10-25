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
  finishSession: (sessionId: string, reps: number, kind: "pushup" | "plank" = "pushup") =>
    apiFetch<PushupChallengeFinishResult>(
      `/pushup-challenge/sessions/${encodeURIComponent(sessionId)}/finish`,
      { method: "POST", body: JSON.stringify({ reps, kind }) },
      { auth: false },
    ),
};
