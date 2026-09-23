"use client";

import { useState } from "react";
import { mediaUrl, viNum } from "@/lib/labels";
import {
  formatPlanMealPortionLine,
  formatPlanMealTitle,
  planMealHasMacros,
  type MealPortionInput,
} from "@/lib/mealDisplay";
import MacroBar from "../MacroBar";

function MealThumb({ imageUrl, name }: { imageUrl?: string | null; name: string }) {
  const src = mediaUrl(imageUrl);
  const [failed, setFailed] = useState(false);
  const showPhoto = Boolean(src) && !failed;
  return (
    <span className="relative h-14 w-14 shrink-0 overflow-hidden rounded-xl bg-gradient-to-br from-amber-100 to-orange-50">
      {src && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt=""
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover"
          onError={() => setFailed(true)}
        />
      ) : null}
      {!showPhoto && (
        <span className="absolute inset-0 grid place-items-center px-1 text-center text-[10px] font-bold leading-tight text-amber-800/80">
          {name.slice(0, 8)}
        </span>
      )}
    </span>
  );
}

export default function PlanMealRow({
  meal,
  why,
  showMacros,
  prefix,
  className = "rounded-xl bg-white px-3 py-2.5 ring-1 ring-slate-100",
}: {
  meal: MealPortionInput & {
    calories?: number | null;
    protein_g?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
    image_url?: string | null;
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
      <div className="flex items-start gap-3">
        <MealThumb imageUrl={meal.image_url} name={title} />
        <div className="min-w-0 flex-1">
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
              <span className="shrink-0 text-sm font-semibold text-slate-600">
                {viNum(meal.calories)} kcal
              </span>
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
        </div>
      </div>
    </li>
  );
}
