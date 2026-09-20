"use client";

import { useRef } from "react";
import Link from "next/link";
import { PLAN_SECTION_ORDER, SECTION_LABEL, type PlanDay, type PlanExercise } from "@/lib/plansApi";
import {
  estimatePlanDayMinutes,
  localizePlanDayTitle,
  localizeWorkoutCopy,
  splitRoleLabel,
} from "@/lib/planLabels";
import { viNum } from "@/lib/labels";
import PlanExerciseList from "./PlanExerciseList";

export default function PlanSessionPanel({
  day,
  showKnowledge,
  whyByExerciseId,
  canSwap,
  onSelectExercise,
  onSwapClick,
  onGoMeals,
  foundation = false,
  fitnessTestHref,
}: {
  day: PlanDay;
  showKnowledge?: boolean;
  whyByExerciseId?: Record<number, string>;
  canSwap?: boolean;
  onSelectExercise: (ex: PlanExercise) => void;
  onSwapClick?: (ex: PlanExercise) => void;
  onGoMeals?: () => void;
  foundation?: boolean;
  fitnessTestHref?: string | null;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  const roleVi = splitRoleLabel(day.split_role);
  const exCount = day.exercises.length;
  const roleKey = day.split_role?.trim().toLowerCase() ?? "";
  const isRecoveryDay = exCount === 0 && roleKey === "recovery";
  const isTestDay = exCount === 0 && roleKey === "test";
  const testHref = fitnessTestHref || "/kiemtratheluc?goi=fitness_advanced";
  const usedMin = estimatePlanDayMinutes(day.exercises);
  const hasMeals = day.meals.length > 0;
  const title =
    (foundation
      ? localizeWorkoutCopy(localizePlanDayTitle(day.title_vi))
      : localizePlanDayTitle(day.title_vi)) || `Ngày ${day.day_number}`;

  function startSession() {
    listRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
      <div className="mb-4">
        <h2 className="text-base font-bold text-slate-900 [overflow-wrap:anywhere]">{title}</h2>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-600">
          {roleVi && (
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
              {roleVi}
            </span>
          )}
          {exCount > 0 && (
            <span className="font-bold text-slate-800">
              {exCount} bài{usedMin > 0 ? ` · ~${usedMin} phút` : ""}
            </span>
          )}
          {day.target_calories != null && day.target_calories > 0 && (
            <span className="text-xs font-medium text-emerald-700">
              Mục tiêu ăn ngày tập ~{viNum(day.target_calories)} kcal
            </span>
          )}
        </div>
        {exCount > 0 && (
          <button
            type="button"
            onClick={startSession}
            className="mt-3 w-full rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 sm:w-auto sm:px-5"
          >
            Bắt đầu buổi
          </button>
        )}
      </div>

      <div ref={listRef}>
        {exCount === 0 ? (
          <div className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900">
            {isTestDay ? (
              <>
                <p className="font-bold">Hôm nay tốt nghiệp: test chính thức 5 môn bằng camera.</p>
                {day.notes_vi ? (
                  <p className="mt-1 leading-relaxed text-emerald-800">
                    {foundation ? localizeWorkoutCopy(day.notes_vi) : day.notes_vi}
                  </p>
                ) : null}
                <Link
                  href={testHref}
                  className="mt-3 inline-flex w-full items-center justify-center rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 sm:w-auto sm:px-5"
                >
                  Bắt đầu test chính thức
                </Link>
              </>
            ) : (
              <>
                <p className="font-bold">
                  {isRecoveryDay ? "Hôm nay nghỉ để cơ thể thích nghi." : "Ngày này chưa có bài tập."}
                </p>
                {isRecoveryDay && day.notes_vi ? (
                  <p className="mt-1 leading-relaxed text-emerald-800">
                    {foundation ? localizeWorkoutCopy(day.notes_vi) : day.notes_vi}
                  </p>
                ) : null}
              </>
            )}
          </div>
        ) : (
          PLAN_SECTION_ORDER.map((sec) => {
            const items = day.exercises.filter((e) => e.section === sec);
            const note = day.section_notes?.[sec];
            if (!items.length && !note?.trim()) return null;
            return (
              <div key={sec} className="mb-4 last:mb-0">
                <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
                  {SECTION_LABEL[sec] || sec}
                </p>
                {items.length > 0 ? (
                  <PlanExerciseList
                    exercises={items}
                    section={sec}
                    showKnowledge={showKnowledge}
                    whyByExerciseId={whyByExerciseId}
                    canSwap={canSwap && sec !== "warmup" && sec !== "cooldown"}
                    foundation={foundation}
                    onSelect={onSelectExercise}
                    onSwapClick={onSwapClick}
                  />
                ) : null}
                {showKnowledge && note?.trim() && (
                  <p className="mt-2 rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800">
                    <span className="font-semibold">Lưu ý: </span>
                    {foundation ? localizeWorkoutCopy(note.trim()) : note.trim()}
                  </p>
                )}
              </div>
            );
          })
        )}
      </div>

      {hasMeals && onGoMeals && (
        <button
          type="button"
          onClick={onGoMeals}
          className="mt-4 w-full rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-brand-700 hover:border-brand-300 hover:bg-brand-50"
        >
          Xem thực đơn buổi này →
        </button>
      )}
    </div>
  );
}
