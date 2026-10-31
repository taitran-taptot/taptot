"use client";

import Link from "next/link";
import type { PlanDetail } from "@/lib/plansApi";
import { viNum } from "@/lib/labels";
import { softenPlanCopy } from "@/lib/planLabels";
import { knowledgeHref, refsForChallengePhases } from "@/lib/phaseKnowledge";
import {
  FAMILIARIZATION_MISSION_VI,
  familiarizationNutritionVi,
  familiarizationWeightGoalCopyVi,
} from "@/lib/familiarizationOverviewCopy";
import { isFamiliarizationPlan } from "@/lib/isFamiliarizationPlan";
import { OVERVIEW_COACH_NOTES } from "@/lib/overviewCoachNotes";
import {
  averagePlanMealNutrition,
  ceilKcalTo50,
  roundMacrosToKcal,
} from "@/lib/mealDisplay";

export type PlanWeekSummary = {
  minutes: number;
  minutesLabel?: string;
  sessions: number;
  splits: string[];
  weekCount: number;
  durationDays?: number;
};

export default function PlanOverviewPanel({
  plan,
  weekSummary,
  onExport,
  exporting = false,
  exportError,
}: {
  plan: PlanDetail;
  weekSummary?: PlanWeekSummary | null;
  onExport?: () => void | Promise<void>;
  exporting?: boolean;
  exportError?: string;
}) {
  const curriculum = plan.insights?.curriculum as
    | {
        mesocycles?: Array<{
          month: number;
          label_vi?: string;
          blurb_vi?: string;
          deload_week?: number;
          weeks?: number[];
          rationale_vi?: string;
          knowledge_refs?: Array<{ slug: string; label: string }>;
        }>;
        deload_weeks?: number[];
      }
    | undefined;
  const isCurriculum =
    Boolean(plan.insights?.challenge_100_days)
    || Boolean(plan.challenge_100_days)
    || Boolean(curriculum?.mesocycles?.length);
  /** Lịch 1 tháng: tổng quan gọn — lịch tập, dinh dưỡng, xuất file. */
  const compactMonthOverview = !isCurriculum;

  const foodAvg = averagePlanMealNutrition(plan.days);
  const overviewKcal =
    foodAvg != null && foodAvg.kcal > 0
      ? ceilKcalTo50(foodAvg.kcal)
      : plan.target_calories != null
        ? ceilKcalTo50(plan.target_calories)
        : null;
  const overviewMacros = (() => {
    const raw =
      foodAvg != null && (foodAvg.protein_g > 0 || foodAvg.carbs_g > 0 || foodAvg.fat_g > 0)
        ? foodAvg
        : plan.target_protein_g != null || plan.target_carbs_g != null || plan.target_fat_g != null
          ? {
              protein_g: plan.target_protein_g ?? 0,
              carbs_g: plan.target_carbs_g ?? 0,
              fat_g: plan.target_fat_g ?? 0,
            }
          : null;
    if (!raw || overviewKcal == null) return null;
    return roundMacrosToKcal(overviewKcal, raw);
  })();
  const hasWorkouts = plan.days.some((d) => d.exercises.length > 0);
  const hasNutrition =
    overviewKcal != null
    || overviewMacros != null
    || plan.target_calories != null
    || plan.target_protein_g != null
    || plan.target_carbs_g != null
    || plan.target_fat_g != null;
  const overviewCopy = plan.insights?.overview;
  const isFamiliarization = isFamiliarizationPlan(plan);
  const missionVi = isFamiliarization
    ? FAMILIARIZATION_MISSION_VI
    : overviewCopy?.mission_vi?.trim();
  const outcomeVi = isFamiliarization
    ? ""
    : overviewCopy?.outcome_vi?.trim();
  const nutritionVi = isFamiliarization
    ? familiarizationNutritionVi(plan.insights?.weight_goal)
    : overviewCopy?.nutrition_vi?.trim();
  const isAiPlan = plan.source === "ai" || Boolean(plan.ai_generation_id);
  const showFixedCoachNotes = isAiPlan && !isFamiliarization;
  const coachNote = isFamiliarization || showFixedCoachNotes
    ? ""
    : (overviewCopy?.summary_vi || "").trim();
  const weightGoalCopy = plan.insights?.weight_goal
    ? isFamiliarization
      ? familiarizationWeightGoalCopyVi(plan.insights.weight_goal)
      : plan.insights.weight_goal.copy_vi
    : null;
  const staffKnowledge = (plan.insights?.staff_knowledge || []).filter((k) => k.slug);
  const client = plan.insights?.client;
  const genderLabel =
    client?.gender === "male" ? "Nam" : client?.gender === "female" ? "Nữ" : null;
  const hasClient =
    client &&
    (client.height_cm || client.weight_kg || genderLabel || (client.notes || "").trim());

  return (
    <div className="space-y-4">
      {weekSummary && hasWorkouts && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-3 text-sm font-bold text-slate-700">Lịch tập</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-lg font-bold text-slate-900">{weekSummary.sessions}</p>
              <p className="mt-1 text-[11px] font-medium text-slate-500">buổi/tuần</p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-lg font-bold text-slate-900">
                {weekSummary.minutesLabel ?? `${weekSummary.minutes}′`}
              </p>
              <p className="mt-1 text-[11px] font-medium text-slate-500">phút/buổi</p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-lg font-bold text-slate-900">
                {weekSummary.durationDays ?? weekSummary.weekCount}
              </p>
              <p className="mt-1 text-[11px] font-medium text-slate-500">
                {weekSummary.durationDays ? "ngày" : "tuần"}
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-xs font-bold leading-snug text-slate-900">
                {weekSummary.splits.join(" · ") || "—"}
              </p>
              <p className="mt-1 text-[11px] font-medium text-slate-500">nhóm buổi</p>
            </div>
          </div>
        </div>
      )}

      {hasNutrition && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-1 text-sm font-bold text-slate-700">Mục tiêu ăn</p>

          {overviewKcal != null && (
            <div className="rounded-xl bg-brand-50 px-4 py-3 ring-1 ring-brand-100">
              <p className="text-2xl font-bold text-brand-900">
                Trung bình {viNum(overviewKcal)} calo /ngày
              </p>
              <p className="mt-1 text-xs text-brand-800/80">
                Chi tiết hãy xem trong mục Lịch ăn
              </p>
            </div>
          )}

          {overviewMacros && (
            <div className="mt-3 grid grid-cols-3 gap-2">
              <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                <p className="text-lg font-bold text-slate-900">
                  {viNum(overviewMacros.protein_g)}g
                </p>
                <p className="mt-0.5 text-[11px] font-medium text-slate-500">Đạm</p>
              </div>
              <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                <p className="text-lg font-bold text-slate-900">
                  {viNum(overviewMacros.carbs_g)}g
                </p>
                <p className="mt-0.5 text-[11px] font-medium text-slate-500">Tinh bột</p>
              </div>
              <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                <p className="text-lg font-bold text-slate-900">
                  {viNum(overviewMacros.fat_g)}g
                </p>
                <p className="mt-0.5 text-[11px] font-medium text-slate-500">Béo</p>
              </div>
            </div>
          )}
        </div>
      )}

      {hasClient && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-2 text-sm font-bold text-slate-700">Hồ sơ khách</p>
          <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
            {client.height_cm != null && (
              <div className="rounded-xl bg-slate-50 px-3 py-2">
                <dt className="text-[11px] text-slate-400">Chiều cao</dt>
                <dd className="font-semibold text-slate-800">{client.height_cm} cm</dd>
              </div>
            )}
            {client.weight_kg != null && (
              <div className="rounded-xl bg-slate-50 px-3 py-2">
                <dt className="text-[11px] text-slate-400">Cân nặng</dt>
                <dd className="font-semibold text-slate-800">{client.weight_kg} kg</dd>
              </div>
            )}
            {genderLabel && (
              <div className="rounded-xl bg-slate-50 px-3 py-2">
                <dt className="text-[11px] text-slate-400">Giới tính</dt>
                <dd className="font-semibold text-slate-800">{genderLabel}</dd>
              </div>
            )}
          </dl>
          {client.notes?.trim() ? (
            <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{client.notes.trim()}</p>
          ) : null}
        </div>
      )}

      {showFixedCoachNotes ? (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-2 text-sm font-bold text-slate-700">Những điều cần lưu ý</p>
          <ul className="space-y-2.5 text-sm leading-relaxed text-slate-700">
            {OVERVIEW_COACH_NOTES.map((note) => (
              <li key={note.title}>
                <span className="font-semibold text-slate-800">{note.title}:</span> {note.body}
              </li>
            ))}
          </ul>
        </div>
      ) : coachNote ? (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-2 text-sm font-bold text-slate-700">Những điều cần lưu ý</p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{coachNote}</p>
        </div>
      ) : null}

      {staffKnowledge.length > 0 && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-2 text-sm font-bold text-slate-700">Kiến thức nên đọc</p>
          <ul className="space-y-1.5">
            {staffKnowledge.map((k) => (
              <li key={k.slug}>
                <Link
                  href={knowledgeHref(k.slug)}
                  className="text-sm font-semibold text-brand-700 hover:underline"
                >
                  {k.title_vi || k.slug}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(missionVi || outcomeVi || (compactMonthOverview && nutritionVi)) && (
        <div className="space-y-3">
          {missionVi && (
            <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
              <p className="mb-1 text-sm font-bold text-slate-700">Bạn đang làm gì</p>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {softenPlanCopy(missionVi)}
              </p>
            </div>
          )}
          {outcomeVi && (
            <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
              <p className="mb-1 text-sm font-bold text-slate-700">Tập xong sẽ được gì</p>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {softenPlanCopy(outcomeVi)}
              </p>
            </div>
          )}
          {compactMonthOverview && nutritionVi && (
            <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
              <p className="mb-1 text-sm font-bold text-slate-700">Dinh dưỡng & hồi phục</p>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {softenPlanCopy(nutritionVi)}
              </p>
            </div>
          )}
        </div>
      )}

      {plan.insights?.weight_goal && weightGoalCopy && !isFamiliarization ? (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-1 text-sm font-bold text-slate-700">Gợi ý cân nặng 2 tháng</p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
            {softenPlanCopy(weightGoalCopy)}
          </p>
          {plan.insights.weight_goal.daily_kcal != null ? (
            <p className="mt-3 text-2xl font-bold text-brand-900">
              ~{viNum(ceilKcalTo50(plan.insights.weight_goal.daily_kcal))}{" "}
              <span className="text-base font-bold text-brand-800">calo/ngày</span>
            </p>
          ) : null}
        </div>
      ) : null}

      {isCurriculum && curriculum?.mesocycles && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-3 text-sm font-bold text-slate-700">Ba pha của thử thách</p>
          <ul className="space-y-2">
            {curriculum.mesocycles.map((m) => {
              const longText = m.rationale_vi?.trim();
              const weeks = (m.weeks || []).filter((w) => Number.isFinite(w));
              const weekRange =
                weeks.length > 0
                  ? `${weeks[0]}-${weeks[weeks.length - 1]}`
                  : m.month === 2
                    ? "5-8"
                    : m.month === 3
                      ? "9-14"
                      : "1-4";
              const inputs = plan.insights?.inputs;
              const fallbackPhases = refsForChallengePhases(
                plan.insights?.effective_level ?? inputs?.experience_level,
                { goal: inputs?.goal, activity: inputs?.activity, location: inputs?.location },
              );
              const storedRefs = (m.knowledge_refs || []).filter((r) => r.slug);
              const resolvedRefs =
                storedRefs.length > 0
                  ? storedRefs
                  : fallbackPhases[(m.month || 1) - 1] || [];
              const softenLines = (text: string) =>
                text
                  .split("\n")
                  .map((line) => softenPlanCopy(line))
                  .join("\n");
              return (
                <li
                  key={m.month}
                  className="rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-2.5"
                >
                  <p className="text-sm font-semibold text-slate-800">
                    Pha {m.month} · Tuần {weekRange}
                    {m.label_vi ? ` — ${m.label_vi}` : ""}
                  </p>
                  {m.blurb_vi && (
                    <p className="mt-0.5 text-sm leading-snug text-slate-600">
                      {softenLines(m.blurb_vi)}
                    </p>
                  )}
                  {longText ? (
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-600">
                      {softenLines(longText)}
                    </p>
                  ) : null}
                  {resolvedRefs.length > 0 && (
                    <ul className="mt-2 space-y-1 border-t border-slate-100 pt-2">
                      <li className="text-[11px] font-semibold text-slate-500">
                        Đọc trong pha này
                      </li>
                      {resolvedRefs.map((ref) => (
                        <li key={ref.slug}>
                          <a
                            href={knowledgeHref(ref.slug)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs font-medium text-sky-700 underline decoration-sky-200 underline-offset-2 hover:text-sky-900"
                          >
                            {ref.label}
                          </a>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {!compactMonthOverview && onExport && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-3 text-sm font-bold text-slate-700">Xuất lịch tập</p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void onExport()}
              disabled={exporting}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold transition hover:border-brand-400 hover:text-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {exporting ? "Đang xuất…" : "Xuất PDF"}
            </button>
            {exporting ? (
              <span
                className="inline-block h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-brand-200 border-t-brand-500"
                aria-hidden
              />
            ) : null}
          </div>
          {exportError ? (
            <p className="mt-2 text-sm text-rose-600">{exportError}</p>
          ) : null}
        </div>
      )}
    </div>
  );
}
