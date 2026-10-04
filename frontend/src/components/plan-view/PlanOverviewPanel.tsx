"use client";

import { useState } from "react";
import Link from "next/link";
import type { PlanDetail } from "@/lib/plansApi";
import { viNum } from "@/lib/labels";
import { softenPlanCopy } from "@/lib/planLabels";
import { knowledgeHref, refsForPhase } from "@/lib/phaseKnowledge";
import {
  FAMILIARIZATION_MISSION_VI,
  familiarizationNutritionVi,
  familiarizationOutcomeVi,
  familiarizationWeightGoalCopyVi,
} from "@/lib/familiarizationOverviewCopy";
import { isFamiliarizationPlan } from "@/lib/isFamiliarizationPlan";

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

  const restDay = plan.insights?.rest_day_nutrition;
  const trainDayKcal = plan.days.find(
    (d) => d.exercises.length > 0 && d.target_calories != null,
  )?.target_calories ?? null;
  const restDayKcal = restDay?.target_calories ?? null;
  const roundCal = (n: number) => Math.round(n / 100) * 100;
  const floorMacro = (n: number) => Math.floor(n);
  const hasWorkouts = plan.days.some((d) => d.exercises.length > 0);
  const hasNutrition =
    plan.target_calories != null
    || plan.target_protein_g != null
    || plan.target_carbs_g != null
    || plan.target_fat_g != null;
  const overviewCopy = plan.insights?.overview;
  const isFamiliarization = isFamiliarizationPlan(plan);
  const missionVi = isFamiliarization
    ? FAMILIARIZATION_MISSION_VI
    : overviewCopy?.mission_vi?.trim();
  const outcomeVi = isFamiliarization
    ? familiarizationOutcomeVi(plan.insights?.client?.gender)
    : overviewCopy?.outcome_vi?.trim();
  const nutritionVi = isFamiliarization
    ? familiarizationNutritionVi(plan.insights?.weight_goal)
    : overviewCopy?.nutrition_vi?.trim();
  const staffSummary = isFamiliarization
    ? null
    : overviewCopy?.summary_vi?.trim();
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

      {staffSummary && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-1 text-sm font-bold text-slate-700">Lời HLV</p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{staffSummary}</p>
        </div>
      )}

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
              ~{viNum(plan.insights.weight_goal.daily_kcal)}{" "}
              <span className="text-base font-bold text-brand-800">kcal/ngày</span>
            </p>
          ) : null}
        </div>
      ) : null}

      {hasNutrition && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-1 text-sm font-bold text-slate-700">Mục tiêu ăn</p>

          {plan.target_calories != null && (
            <div className="rounded-xl bg-brand-50 px-4 py-3 ring-1 ring-brand-100">
              <p className="text-2xl font-bold text-brand-900">
                Trung bình ~{viNum(roundCal(plan.target_calories))} calo /ngày
              </p>
              {trainDayKcal != null && restDayKcal != null && (
                <p className="mt-1 text-xs text-brand-800/80">
                  Ngày tập ăn ~{viNum(roundCal(trainDayKcal))} calo, ngày nghỉ ăn ~
                  {viNum(roundCal(restDayKcal))} calo.
                </p>
              )}
              <p className="mt-1 text-xs text-brand-800/80">
                Chi tiết hãy xem trong tab Ăn uống
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
                    {viNum(floorMacro(plan.target_protein_g))}g
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-slate-500">Đạm</p>
                </div>
              )}
              {plan.target_carbs_g != null && (
                <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                  <p className="text-lg font-bold text-slate-900">
                    {viNum(floorMacro(plan.target_carbs_g))}g
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-slate-500">Tinh bột</p>
                </div>
              )}
              {plan.target_fat_g != null && (
                <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                  <p className="text-lg font-bold text-slate-900">
                    {viNum(floorMacro(plan.target_fat_g))}g
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-slate-500">Béo</p>
                </div>
              )}
            </div>
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
