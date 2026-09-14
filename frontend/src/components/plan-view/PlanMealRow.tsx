"use client";

import { viNum } from "@/lib/labels";
import {
  formatPlanMealPortionLine,
  formatPlanMealTitle,
  planMealHasMacros,
  type MealPortionInput,
} from "@/lib/mealDisplay";
import MacroBar from "../MacroBar";

export default function PlanMealRow({
  meal,
  why,
  showMacros,
  prefix,
  className = "rounded-lg bg-slate-50 px-3 py-2 text-sm",
}: {
  meal: MealPortionInput & {
    calories?: number | null;
    protein_g?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
  };
  why?: string | null;
  showMacros?: boolean;
  prefix?: string;
  className?: string;
}) {
  const title = formatPlanMealTitle(meal.name_vi);
  const hasMacros = planMealHasMacros(meal);

  return (
    <li className={className}>
      <div className="flex flex-col gap-0.5 sm:flex-row sm:items-start sm:justify-between sm:gap-2">
        <div className="min-w-0">
          <p className="font-medium leading-snug text-slate-800 [overflow-wrap:anywhere]">
            {prefix ? (
              <>
                <span className="font-semibold text-slate-600">{prefix}: </span>
                {title}
              </>
            ) : (
              title
            )}
          </p>
          <p className="mt-0.5 text-xs font-medium text-slate-500">
            {formatPlanMealPortionLine(meal, { showDensity: showMacros })}
          </p>
        </div>
        {meal.calories != null && meal.calories > 0 && (
          <span className="shrink-0 font-semibold text-slate-600">{viNum(meal.calories)} kcal</span>
        )}
      </div>
      {showMacros && hasMacros && (
        <div className="mt-2">
          <MacroBar
            protein_g={meal.protein_g ?? 0}
            carbs_g={meal.carbs_g ?? 0}
            fat_g={meal.fat_g ?? 0}
          />
        </div>
      )}
      {why?.trim() && (
        <p className="mt-1.5 text-xs leading-snug text-sky-800/90">{why.trim()}</p>
      )}
    </li>
  );
}
