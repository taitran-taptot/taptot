"use client";

import { useState, type ReactNode } from "react";
import { viNum } from "@/lib/labels";
import { MEAL_LABEL } from "@/lib/plansApi";

export const MEAL_GROUP_ORDER = ["breakfast", "lunch", "dinner", "snack"] as const;
export type MealGroupType = (typeof MEAL_GROUP_ORDER)[number];

export function mealSlotKcal(meals: { calories?: number | null }[]): number {
  return meals.reduce((sum, m) => sum + (m.calories || 0), 0);
}

export function firstFilledMealType(
  meals: { meal_type: string }[],
): MealGroupType | null {
  for (const mt of MEAL_GROUP_ORDER) {
    if (meals.some((m) => m.meal_type === mt)) return mt;
  }
  return null;
}

export function mealGroupTitle(mealType: string): string {
  return MEAL_LABEL[mealType] || mealType;
}

export default function PlanMealAccordion({
  title,
  itemCount,
  kcal,
  defaultOpen = false,
  children,
}: {
  title: string;
  itemCount: number;
  kcal?: number | null;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const kcalPart = kcal != null && kcal > 0 ? ` · ${viNum(kcal)} kcal` : "";
  return (
    <details
      className="group mb-2 rounded-xl ring-1 ring-slate-100 open:bg-slate-50/70 last:mb-0"
      open={open}
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2.5 text-sm font-semibold text-slate-700 marker:content-none [&::-webkit-details-marker]:hidden">
        <span className="flex min-w-0 items-center gap-2">
          <span
            aria-hidden
            className={`inline-block shrink-0 text-slate-400 transition-transform ${open ? "rotate-90" : ""}`}
          >
            ▸
          </span>
          <span className="min-w-0 truncate">{title}</span>
        </span>
        <span className="shrink-0 text-xs font-medium text-slate-500">
          {itemCount} món{kcalPart}
          <span className="ml-2 font-normal text-slate-400">
            {open ? "Thu gọn" : "Nhấn để xem món"}
          </span>
        </span>
      </summary>
      <div className="px-3 pb-3">{children}</div>
    </details>
  );
}
