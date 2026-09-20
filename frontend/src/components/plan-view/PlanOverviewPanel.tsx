"use client";

import { useCallback, useMemo, useState } from "react";
import type { PlanDetail } from "@/lib/plansApi";
import { plansApi } from "@/lib/plansApi";
import { viNum } from "@/lib/labels";
import { softenPlanCopy } from "@/lib/planLabels";
import type { PlanViewTab } from "./types";
import PlanKnowledgeToggle from "../PlanKnowledgeToggle";
import PlanInsightsPanel from "../PlanInsightsPanel";

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
  isAiPlan,
  showKnowledge,
  onKnowledgeChange,
  weekSummary,
  firstDayLabel,
  onGoToTab,
  onExport,
  canNutritionCheckin,
  onPlanUpdated,
  showMealsTab = true,
}: {
  plan: PlanDetail;
  isAiPlan: boolean;
  showKnowledge: boolean;
  onKnowledgeChange: (v: boolean) => void;
  weekSummary?: PlanWeekSummary | null;
  firstDayLabel?: string | null;
  onGoToTab?: (tab: PlanViewTab) => void;
  onExport?: (format: "xlsx" | "pdf" | "word") => void;
  canNutritionCheckin?: boolean;
  onPlanUpdated?: (plan: PlanDetail) => void;
  showMealsTab?: boolean;
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
  const [weightInput, setWeightInput] = useState("");
  const [previewKcal, setPreviewKcal] = useState<number | null>(null);
  const [previewDelta, setPreviewDelta] = useState<number | null>(null);
  const [checkinStatus, setCheckinStatus] = useState("");
  const [checkinBusy, setCheckinBusy] = useState(false);

  const checkinDue = useMemo(() => {
    const due = plan.insights?.next_nutrition_checkin_due;
    if (!due) return false;
    try {
      return new Date(due) <= new Date();
    } catch {
      return false;
    }
  }, [plan.insights?.next_nutrition_checkin_due]);

  const runPreview = useCallback(async () => {
    const w = parseFloat(weightInput.replace(",", "."));
    if (!Number.isFinite(w) || w < 30 || w > 300) {
      setCheckinStatus("Nhập cân từ 30–300 kg.");
      return;
    }
    setCheckinBusy(true);
    setCheckinStatus("");
    try {
      const res = await plansApi.previewNutritionCheckin(plan.id, w);
      setPreviewKcal(res.preview.avg_target_calories);
      setPreviewDelta(res.preview.delta_from_current);
    } catch (e) {
      setPreviewKcal(null);
      setPreviewDelta(null);
      setCheckinStatus((e as Error).message || "Không xem trước được.");
    } finally {
      setCheckinBusy(false);
    }
  }, [plan.id, weightInput]);

  const submitCheckin = useCallback(async () => {
    const w = parseFloat(weightInput.replace(",", "."));
    if (!Number.isFinite(w) || w < 30 || w > 300) {
      setCheckinStatus("Nhập cân từ 30–300 kg.");
      return;
    }
    setCheckinBusy(true);
    setCheckinStatus("");
    try {
      const res = await plansApi.nutritionCheckin(plan.id, w);
      onPlanUpdated?.(res.plan);
      setPreviewKcal(res.preview.avg_target_calories);
      setPreviewDelta(res.preview.delta_from_current);
      setCheckinStatus("Đã cập nhật calo và thực đơn từ giai đoạn hiện tại.");
      setWeightInput("");
    } catch (e) {
      setCheckinStatus((e as Error).message || "Cập nhật thất bại.");
    } finally {
      setCheckinBusy(false);
    }
  }, [onPlanUpdated, plan.id, weightInput]);

  const hasFlexibleCal =
    plan.target_calories != null && plan.days.some((d) => d.target_calories != null);
  const restDay = plan.insights?.rest_day_nutrition;
  const hasMeals = plan.days.some((d) => d.meals.length > 0);
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
      {!compactMonthOverview && hasWorkouts && onGoToTab && (
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={() => onGoToTab("train")}
            className="min-h-11 flex-1 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
          >
            Hôm nay tập gì →
          </button>
          {hasMeals && showMealsTab && (
            <button
              type="button"
              onClick={() => onGoToTab("meals")}
              className="min-h-11 flex-1 rounded-xl border border-brand-200 bg-brand-50 px-4 py-2.5 text-sm font-bold text-brand-700 hover:bg-brand-100"
            >
              Xem thực đơn →
            </button>
          )}
        </div>
      )}

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
              <p className="text-lg font-extrabold text-slate-900">{weekSummary.sessions}</p>
              <p className="mt-1 text-[11px] font-medium text-slate-500">buổi/tuần</p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-lg font-extrabold text-slate-900">{weekSummary.minutes}′</p>
              <p className="mt-1 text-[11px] font-medium text-slate-500">phút/buổi</p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-lg font-extrabold text-slate-900">
                {weekSummary.durationDays ?? weekSummary.weekCount}
              </p>
              <p className="mt-1 text-[11px] font-medium text-slate-500">
                {weekSummary.durationDays ? "ngày" : "tuần"}
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-xs font-extrabold leading-snug text-slate-900">
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
            <p className="mt-3 text-2xl font-extrabold text-brand-900">
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
              <p className="text-2xl font-extrabold text-brand-900">
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
                  <p className="text-lg font-extrabold text-slate-900">
                    {viNum(plan.target_protein_g)}g
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-slate-500">Đạm</p>
                </div>
              )}
              {plan.target_carbs_g != null && (
                <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                  <p className="text-lg font-extrabold text-slate-900">
                    {viNum(plan.target_carbs_g)}g
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-slate-500">Tinh bột</p>
                </div>
              )}
              {plan.target_fat_g != null && (
                <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-center ring-1 ring-slate-100">
                  <p className="text-lg font-extrabold text-slate-900">
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
          <p className="mb-1 text-sm font-bold text-slate-700">Thử thách 100 ngày</p>
          <p className="mb-3 text-xs text-slate-500">
            14 tuần · tuần 4, 8 và 14 tập nhẹ hơn · lịch đổi theo từng giai đoạn
          </p>
          <ul className="space-y-2">
            {curriculum.mesocycles.map((m) => {
              const longText = m.rationale_vi?.trim();
              const open = expandedPhases.has(m.month);
              return (
                <li
                  key={m.month}
                  className="rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-2.5"
                >
                  <p className="text-sm font-semibold text-slate-800">
                    Giai đoạn {m.month}
                    {m.label_vi ? ` — ${m.label_vi}` : ""}
                    {m.deload_week != null && (
                      <span className="ml-1.5 text-xs font-medium text-slate-500">
                        · tuần {m.deload_week} tập nhẹ
                      </span>
                    )}
                  </p>
                  {m.blurb_vi && (
                    <p className="mt-0.5 text-xs leading-snug text-slate-500">
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
                      <button
                        type="button"
                        onClick={() => togglePhase(m.month)}
                        className="mt-1 text-[11px] font-semibold text-brand-700 hover:underline"
                      >
                        {open ? "Thu gọn" : "Xem thêm"}
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {!compactMonthOverview && canNutritionCheckin && nutritionBlocks.length > 0 && (
        <div
          className={`rounded-2xl border p-4 shadow-soft sm:p-5 ${
            checkinDue ? "border-amber-200 bg-amber-50/80" : "border-slate-200 bg-white"
          }`}
        >
          <p className="text-sm font-bold text-slate-800">
            {checkinDue ? "Đã 2 tuần — cập nhật cân để điều chỉnh calo" : "Cập nhật cân (mỗi 2 tuần)"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            TAPTOT tính lại calo và khẩu phần từ giai đoạn hiện tại trở đi, tối đa ±150 kcal mỗi lần.
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
            <label className="flex-1">
              <span className="mb-1 block text-xs font-medium text-slate-600">Cân nặng (kg)</span>
              <input
                type="text"
                inputMode="decimal"
                value={weightInput}
                onChange={(e) => {
                  setWeightInput(e.target.value);
                  setPreviewKcal(null);
                  setPreviewDelta(null);
                }}
                placeholder="vd. 78,5"
                className="field w-full text-sm"
              />
            </label>
            <button
              type="button"
              disabled={checkinBusy}
              onClick={() => void runPreview()}
              className="min-h-11 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold hover:border-brand-400 hover:text-brand-600 disabled:opacity-50"
            >
              Xem trước
            </button>
            <button
              type="button"
              disabled={checkinBusy}
              onClick={() => void submitCheckin()}
              className="min-h-11 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
            >
              Lưu cân
            </button>
          </div>
          {previewKcal != null && (
            <p className="mt-2 text-sm text-slate-700">
              Calo trung bình dự kiến:{" "}
              <span className="font-bold">~{viNum(previewKcal)} kcal/ngày</span>
              {previewDelta != null && previewDelta !== 0 && (
                <span className="text-slate-500">
                  {" "}
                  ({previewDelta > 0 ? "+" : ""}
                  {viNum(previewDelta)} so với giai đoạn hiện tại)
                </span>
              )}
            </p>
          )}
          {checkinStatus && (
            <p
              className={`mt-2 text-xs font-medium ${
                checkinStatus.startsWith("Đã") ? "text-emerald-600" : "text-rose-600"
              }`}
            >
              {checkinStatus}
            </p>
          )}
        </div>
      )}

      {!compactMonthOverview && isAiPlan && (
        <div className="space-y-3 rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <PlanKnowledgeToggle checked={showKnowledge} onChange={onKnowledgeChange} />
          {showKnowledge && plan.insights && (
            <PlanInsightsPanel insights={plan.insights} hideSummary hideAdvice />
          )}
        </div>
      )}

      {!compactMonthOverview && onExport && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <p className="mb-3 text-sm font-bold text-slate-700">Xuất lịch tập</p>
          <div className="flex flex-wrap gap-2">
            {(["xlsx", "pdf", "word"] as const).map((fmt) => (
              <button
                key={fmt}
                type="button"
                onClick={() => onExport(fmt)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold transition hover:border-brand-400 hover:text-brand-600"
              >
                {fmt === "xlsx" ? "Excel" : fmt === "pdf" ? "PDF để in" : "Word"}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
