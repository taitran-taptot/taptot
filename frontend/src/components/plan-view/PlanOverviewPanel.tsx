"use client";

import { useState } from "react";
import type { PlanDetail } from "@/lib/plansApi";
import { viNum } from "@/lib/labels";
import { softenPlanCopy } from "@/lib/planLabels";
import { knowledgeHref, refsForPhase } from "@/lib/phaseKnowledge";

export type PlanWeekSummary = {
  minutes: number;
  sessions: number;
  splits: string[];
  weekCount: number;
  durationDays?: number;
};

function formatBlockWeeks(weeks: number[]): string {
  if (!weeks.length) return "";
  if (weeks.length === 1) return `Tuần ${weeks[0]}`;
  return `Tuần ${weeks[0]}–${weeks[weeks.length - 1]}`;
}

export default function PlanOverviewPanel({
  plan,
  weekSummary,
  firstDayLabel,
  onExport,
}: {
  plan: PlanDetail;
  weekSummary?: PlanWeekSummary | null;
  firstDayLabel?: string | null;
  onExport?: () => void;
}) {
  const nutritionBlocks = plan.insights?.nutrition_blocks ?? [];
  const curriculum = plan.insights?.curriculum as
    | {
        mesocycles?: Array<{
          month: number;
          label_vi?: string;
          blurb_vi?: string;
          deload_week?: number;
          weeks?: number[];
          rationale_vi?: string;
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
  const [expandedPhases, setExpandedPhases] = useState<Set<number>>(new Set());

  const hasFlexibleCal =
    plan.target_calories != null && plan.days.some((d) => d.target_calories != null);
  const restDay = plan.insights?.rest_day_nutrition;
  const hasWorkouts = plan.days.some((d) => d.exercises.length > 0);
  const hasNutrition =
    plan.target_calories != null
    || plan.target_protein_g != null
    || plan.target_carbs_g != null
    || plan.target_fat_g != null;
  const overviewCopy = plan.insights?.overview;
  const missionVi = overviewCopy?.mission_vi?.trim();
  const outcomeVi = overviewCopy?.outcome_vi?.trim();
  const nutritionVi = overviewCopy?.nutrition_vi?.trim();

  function togglePhase(month: number) {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(month)) next.delete(month);
      else next.add(month);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      {(missionVi || outcomeVi || (compactMonthOverview && nutritionVi)) && (
        <div className="space-y-3">
          {missionVi && (
            <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
              <p className="mb-1 text-sm font-bold text-slate-700">Bạn đang làm gì</p>
              <p className="text-sm leading-relaxed text-slate-700">
                {softenPlanCopy(missionVi)}
              </p>
            </div>
          )}
          {outcomeVi && (
            <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
              <p className="mb-1 text-sm font-bold text-slate-700">Tập xong sẽ được gì</p>
              <p className="text-sm leading-relaxed text-slate-700">
                {softenPlanCopy(outcomeVi)}
              </p>
            </div>
          )}
          {compactMonthOverview && nutritionVi && (
            <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
              <p className="mb-1 text-sm font-bold text-slate-700">Dinh dưỡng & hồi phục</p>
              <p className="text-sm leading-relaxed text-slate-700">
                {softenPlanCopy(nutritionVi)}
              </p>
            </div>
          )}
        </div>
      )}

      {weekSummary && hasWorkouts && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-3 text-sm font-bold text-slate-700">Lịch tập</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-lg font-bold text-slate-900">{weekSummary.sessions}</p>
              <p className="mt-1 text-[11px] font-medium text-slate-500">buổi/tuần</p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-lg font-bold text-slate-900">{weekSummary.minutes}′</p>
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
          {firstDayLabel && (
            <p className="mt-3 text-sm text-slate-600">
              Buổi đầu: <span className="font-semibold text-slate-800">{firstDayLabel}</span>
            </p>
          )}
        </div>
      )}

      {plan.insights?.weight_goal?.copy_vi ? (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-1 text-sm font-bold text-slate-700">Gợi ý cân nặng 2 tháng</p>
          <p className="text-sm leading-relaxed text-slate-700">
            {softenPlanCopy(plan.insights.weight_goal.copy_vi)}
          </p>
          {plan.insights.weight_goal.daily_kcal != null ? (
            <p className="mt-3 text-2xl font-bold text-brand-900">
              ~{viNum(plan.insights.weight_goal.daily_kcal)}{" "}
              <span className="text-base font-bold text-brand-800">kcal/ngày</span>
            </p>
          ) : null}
        </div>
      ) : null}

      {hasNutrition && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-1 text-sm font-bold text-slate-700">Mục tiêu ăn</p>
          <p className="mb-3 text-xs text-slate-500">
            Con số để bám khi ăn mỗi ngày — xem chi tiết ở tab Ăn uống.
          </p>

          {plan.target_calories != null && (
            <div className="rounded-xl bg-brand-50 px-4 py-3 ring-1 ring-brand-100">
              <p className="text-2xl font-bold text-brand-900">
                ~{viNum(plan.target_calories)}{" "}
                <span className="text-base font-bold text-brand-800">kcal/ngày</span>
              </p>
              <p className="mt-1 text-xs text-brand-800/80">
                Trung bình cả tuần
                {hasFlexibleCal ? " · ngày tập ăn nhiều hơn, ngày nghỉ ít hơn" : ""}
              </p>
            </div>
          )}

          {(plan.target_protein_g != null
            || plan.target_carbs_g != null
            || plan.target_fat_g != null) && (
            <div className="mt-3 grid grid-cols-3 gap-2">
              {plan.target_protein_g != null && (
                <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                  <p className="text-lg font-bold text-slate-900">
                    {viNum(plan.target_protein_g)}g
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-slate-500">Đạm</p>
                </div>
              )}
              {plan.target_carbs_g != null && (
                <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                  <p className="text-lg font-bold text-slate-900">
                    {viNum(plan.target_carbs_g)}g
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-slate-500">Tinh bột</p>
                </div>
              )}
              {plan.target_fat_g != null && (
                <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                  <p className="text-lg font-bold text-slate-900">
                    {viNum(plan.target_fat_g)}g
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-slate-500">Béo</p>
                </div>
              )}
            </div>
          )}

          {nutritionBlocks.length > 1 && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-3">
              <p className="text-xs font-bold text-slate-700">Calo đổi dần theo giai đoạn</p>
              <p className="mt-0.5 text-[11px] text-slate-500">
                Nếu cân tăng/giảm đúng hướng, mức ăn sẽ chỉnh nhẹ theo từng khối tuần.
              </p>
              <ul className="mt-2 space-y-1.5">
                {nutritionBlocks.map((b) => (
                  <li
                    key={b.block_index}
                    className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 text-sm text-slate-700"
                  >
                    <span className="font-medium text-slate-600">{formatBlockWeeks(b.weeks)}</span>
                    <span className="font-semibold text-slate-900">
                      ~{viNum(b.avg_target_calories)} kcal/ngày
                      {b.projected_weight_kg != null && (
                        <span className="ml-1.5 font-normal text-slate-500">
                          · cân ~{viNum(b.projected_weight_kg)} kg
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {restDay?.target_calories != null && hasFlexibleCal && (
            <p className="mt-3 text-xs text-slate-500">
              Ngày nghỉ ước khoảng ~{viNum(restDay.target_calories)} kcal — thấp hơn ngày tập.
            </p>
          )}
        </div>
      )}

      {isCurriculum && curriculum?.mesocycles && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-1 text-sm font-bold text-slate-700">Ba pha của thử thách</p>
          <p className="mb-3 text-xs text-slate-500">
            14 tuần · tuần nhẹ 4, 8 và 14 · lịch đổi theo từng pha
          </p>
          <ul className="space-y-2">
            {curriculum.mesocycles.map((m) => {
              const longText = m.rationale_vi?.trim();
              const longEnough = Boolean(longText && longText.length > 180);
              const open = !longEnough || expandedPhases.has(m.month);
              const knowledgeRefs = refsForPhase(
                plan.insights?.effective_level ?? plan.insights?.inputs?.experience_level,
                m.month,
              );
              return (
                <li
                  key={m.month}
                  className="rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-2.5"
                >
                  <p className="text-sm font-semibold text-slate-800">
                    Pha {m.month}
                    {m.label_vi ? ` — ${m.label_vi}` : ""}
                    {m.deload_week != null && (
                      <span className="ml-1.5 text-xs font-medium text-slate-500">
                        · tuần {m.deload_week} tập nhẹ
                      </span>
                    )}
                  </p>
                  {m.blurb_vi && (
                    <p className="mt-0.5 text-xs leading-snug text-slate-600">
                      {softenPlanCopy(m.blurb_vi)}
                    </p>
                  )}
                  {longText && (
                    <div className="mt-1.5">
                      {open ? (
                        <p className="text-xs leading-relaxed text-slate-600">
                          {softenPlanCopy(longText)}
                        </p>
                      ) : null}
                      {longEnough && (
                        <button
                          type="button"
                          onClick={() => togglePhase(m.month)}
                          className="mt-1 text-[11px] font-semibold text-brand-700 hover:underline"
                        >
                          {open ? "Thu gọn" : "Xem thêm"}
                        </button>
                      )}
                    </div>
                  )}
                  {knowledgeRefs.length > 0 && (
                    <ul className="mt-2 space-y-1 border-t border-slate-100 pt-2">
                      <li className="text-[11px] font-semibold text-slate-500">Đọc trong pha này</li>
                      {knowledgeRefs.map((ref) => (
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
          <button
            type="button"
            onClick={() => onExport()}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold transition hover:border-brand-400 hover:text-brand-600"
          >
            Xuất PDF
          </button>
        </div>
      )}
    </div>
  );
}
