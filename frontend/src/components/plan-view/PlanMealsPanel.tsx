"use client";

import { useState } from "react";
import { MEAL_GROUP_ORDER, type PlanDay, type PlanInsights, type PlanMealType } from "@/lib/plansApi";
import {
  dayNumbersForFlexibleScope,
  inferredFlexibleScope,
  mealsForSlot,
  mealsFromDays,
  type FlexibleMealScope,
} from "@/lib/mealFlexible";
import type { WeekGroup } from "@/lib/planWeeks";
import { viNum } from "@/lib/labels";
import MacroBar from "../MacroBar";
import PlanMealRow from "./PlanMealRow";
import PlanMealAccordion, { mealSlotKcal } from "./PlanMealAccordion";

const SLOT_TITLE: Record<Exclude<PlanMealType, "flex">, string> = {
  breakfast: "Sáng",
  lunch: "Trưa",
  dinner: "Tối",
  snack: "Bữa phụ 1",
  snack_2: "Bữa phụ 2",
};

const MACRO_LEGEND = [
  { key: "protein_g" as const, label: "Đạm", dot: "bg-brand-500" },
  { key: "carbs_g" as const, label: "Tinh bột", dot: "bg-accent-500" },
  { key: "fat_g" as const, label: "Chất béo", dot: "bg-rose-400" },
];

function slotNote(day: PlanDay, mt: string, kcalOffTarget: boolean): string {
  const rawNote = mt.startsWith("snack") ? undefined : day.meal_notes?.[mt];
  let cleanNote = rawNote?.trim() || "";
  if (cleanNote) {
    cleanNote = cleanNote
      .replace(/Macro món còn lệch mục tiêu[^.]*\.\s*/gi, "")
      .replace(/\s{2,}/g, " ")
      .trim();
    if (kcalOffTarget && /^lệch mục tiêu/i.test(cleanNote)) cleanNote = "";
  }
  return cleanNote;
}

const EAT_HEADING: Record<FlexibleMealScope, string> = {
  day: "Ăn ngày này",
  week: "Ăn tuần này",
  month: "Ăn tháng này",
  plan: "Ăn cả lịch",
};

export default function PlanMealsPanel({
  day,
  days,
  weekGroups = [],
  insights,
  showMealWhy,
  mealWhyForSlot,
}: {
  day: PlanDay | null;
  days?: PlanDay[];
  weekGroups?: WeekGroup[];
  insights?: PlanInsights | null;
  showMealWhy?: boolean;
  mealWhyForSlot?: (foodId: number, mealType: string) => string | undefined;
}) {
  const [showDetailMacros, setShowDetailMacros] = useState(false);

  const catalog = days?.length ? days : day ? [day] : [];
  const flexScope: FlexibleMealScope =
    day?.meals_flexible
      ? inferredFlexibleScope({
          days: catalog,
          weekGroups,
          currentDayNumber: day.day_number,
        })
      : "day";
  const poolNums = day
    ? day.meals_flexible
      ? dayNumbersForFlexibleScope({
          days: catalog,
          weekGroups,
          scope: flexScope,
          currentDayNumber: day.day_number,
        })
      : [day.day_number]
    : [];
  const pooled = day ? mealsFromDays(catalog, poolNums) : [];
  const displayMeals = day?.meals_flexible ? pooled.map((x) => x.meal) : day?.meals ?? [];

  const dayMealKcal = displayMeals.reduce((sum, m) => sum + (m.calories || 0), 0);
  const perDayTarget = day?.target_calories ?? null;
  const dayTargetKcal =
    perDayTarget != null && day?.meals_flexible ? perDayTarget * Math.max(1, poolNums.length) : perDayTarget;
  const kcalDriftPct =
    dayTargetKcal != null && dayTargetKcal > 0
      ? Math.abs(dayMealKcal - dayTargetKcal) / dayTargetKcal
      : null;
  const kcalOffTarget = kcalDriftPct != null && kcalDriftPct > 0.1;
  const dayProtein = displayMeals.reduce((sum, m) => sum + (m.protein_g ?? 0), 0);
  const dayCarbs = displayMeals.reduce((sum, m) => sum + (m.carbs_g ?? 0), 0);
  const dayFat = displayMeals.reduce((sum, m) => sum + (m.fat_g ?? 0), 0);
  const hasDayMacros = dayProtein > 0 || dayCarbs > 0 || dayFat > 0;

  return (
    <div className="space-y-4">
      {day && displayMeals.length > 0 ? (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <h2 className="text-base font-bold text-slate-800">
            {day.meals_flexible ? EAT_HEADING[flexScope] : "Ăn ngày này"}
          </h2>
          {dayMealKcal > 0 && (
            <p className="mt-1 text-sm font-semibold text-slate-700">
              Hôm nay ~{viNum(dayMealKcal)} kcal
              {dayTargetKcal != null && dayTargetKcal > 0
                ? ` · mục tiêu ${viNum(dayTargetKcal)}`
                : ""}
            </p>
          )}
          <p className="mb-3 mt-1 text-xs leading-relaxed text-slate-500">
            Khẩu phần gợi ý — nấu gần mức này là được, không cần cân từng gram.
          </p>

          {kcalOffTarget && (
            <p className="mb-3 inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-900 ring-1 ring-amber-100">
              <span className="font-bold">Lệch mục tiêu</span>
              — tổng món lệch hơn 10% so với calo ngày; có thể chỉnh khẩu phần hoặc bổ sung snack.
            </p>
          )}

          {hasDayMacros && (
            <div className="mb-4">
              <MacroBar protein_g={dayProtein} carbs_g={dayCarbs} fat_g={dayFat} />
              <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] font-medium text-slate-500">
                {MACRO_LEGEND.map((leg) => (
                  <span key={leg.key} className="inline-flex items-center gap-1">
                    <span className={`h-1.5 w-1.5 rounded-full ${leg.dot}`} />
                    {leg.label}{" "}
                    {viNum(
                      leg.key === "protein_g"
                        ? dayProtein
                        : leg.key === "carbs_g"
                          ? dayCarbs
                          : dayFat,
                    )}
                    g
                  </span>
                ))}
              </div>
            </div>
          )}

          <div>
            {day.meals_flexible ? (
              <PlanMealAccordion
                title="Linh hoạt — tự chia bữa"
                itemCount={displayMeals.length}
                kcal={dayMealKcal}
                defaultOpen
              >
                <p className="mb-2 text-xs leading-relaxed text-slate-500">
                  Tự chia thành các bữa
                  {flexScope === "week"
                    ? " trong tuần"
                    : flexScope === "month"
                      ? " trong tháng"
                      : flexScope === "plan"
                        ? " của cả lịch"
                        : " trong ngày"}
                  . HLV chỉ chọn tổng lượng thực phẩm.
                </p>
                <ul className="space-y-2">
                  {displayMeals.map((m, i) => (
                    <PlanMealRow
                      key={`${m.id}-${i}`}
                      meal={m}
                      why={
                        showMealWhy && mealWhyForSlot
                          ? mealWhyForSlot(m.food_id, m.meal_type) || m.notes_vi
                          : undefined
                      }
                      showMacros={showDetailMacros}
                    />
                  ))}
                </ul>
              </PlanMealAccordion>
            ) : (
              MEAL_GROUP_ORDER.map((mt) => {
                const slotMeals = mealsForSlot(day.meals, mt);
                const cleanNote = slotNote(day, mt, kcalOffTarget);
                if (!slotMeals.length && !cleanNote) return null;
                const kcal = mealSlotKcal(slotMeals);
                return (
                  <PlanMealAccordion
                    key={mt}
                    title={SLOT_TITLE[mt]}
                    itemCount={slotMeals.length}
                    kcal={kcal}
                    defaultOpen={mt === "breakfast"}
                  >
                    {slotMeals.length ? (
                      <ul className="space-y-2">
                        {slotMeals.map((m) => {
                          const why =
                            showMealWhy && mealWhyForSlot
                              ? mealWhyForSlot(m.food_id, m.meal_type) || m.notes_vi
                              : undefined;
                          return (
                            <PlanMealRow
                              key={m.id}
                              meal={m}
                              why={why}
                              showMacros={showDetailMacros}
                            />
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="rounded-lg bg-white px-3 py-2 text-sm text-slate-400">
                        Chưa có món cho bữa này.
                      </p>
                    )}
                    {cleanNote && (
                      <p className="mt-2 rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800">
                        <span className="font-semibold">Lưu ý: </span>
                        {cleanNote}
                      </p>
                    )}
                  </PlanMealAccordion>
                );
              })
            )}
          </div>

          <button
            type="button"
            onClick={() => setShowDetailMacros((v) => !v)}
            className="mt-3 text-xs font-semibold text-slate-500 hover:text-brand-600"
          >
            {showDetailMacros ? "Ẩn chi tiết calo/100g" : "Xem chi tiết calo/100g từng món"}
          </button>
        </div>
      ) : (
        <div className="rounded-2xl bg-white p-5 text-center shadow-soft">
          <p className="text-sm text-slate-400">Buổi này chưa có thực đơn.</p>
        </div>
      )}

      {insights?.rest_day_nutrition && (
        <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-base font-bold text-slate-800">Ngày nghỉ</h2>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
              ~{viNum(insights.rest_day_nutrition.target_calories)} kcal
            </span>
          </div>
          <div className="mb-3 flex flex-wrap gap-2 text-xs font-medium text-slate-500">
            <span>Đạm {viNum(insights.rest_day_nutrition.protein_g)}g</span>
            <span>·</span>
            <span>Tinh bột {viNum(insights.rest_day_nutrition.carbs_g)}g</span>
            <span>·</span>
            <span>Chất béo {viNum(insights.rest_day_nutrition.fat_g)}g</span>
          </div>
          {(() => {
            const restMeals = insights.rest_day_meals ?? [];
            return (
              <div>
                {MEAL_GROUP_ORDER.map((mt) => {
                  const slotMeals = restMeals.filter((m) => m.meal_type === mt);
                  if (!slotMeals.length) return null;
                  return (
                    <PlanMealAccordion
                      key={`rest-${mt}`}
                      title={SLOT_TITLE[mt]}
                      itemCount={slotMeals.length}
                      kcal={mealSlotKcal(slotMeals)}
                      defaultOpen={mt === "breakfast"}
                    >
                      <ul className="space-y-2">
                        {slotMeals.map((m, i) => (
                          <PlanMealRow
                            key={`${m.food_id}-${m.meal_type}-${i}`}
                            meal={m}
                            showMacros={showDetailMacros}
                          />
                        ))}
                      </ul>
                    </PlanMealAccordion>
                  );
                })}
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
