import type { PlanDetail } from "@/lib/plansApi";

/** True when plan was generated via familiarization (nhập môn) curriculum. */
export function isFamiliarizationPlan(
  plan: Pick<PlanDetail, "insights"> | null | undefined,
): boolean {
  const insights = plan?.insights;
  if (!insights) return false;
  if (insights.generation_mode === "familiarization") return true;
  if (insights.familiarization_path) return true;
  if (String(insights.generator || "").includes("familiarization")) return true;
  return false;
}
