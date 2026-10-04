"use client";

import { useEffect, useState } from "react";
import { viNum } from "@/lib/labels";
import {
  GRAMS_STEP,
  MIN_GRAMS,
  clampMealGrams,
  kcalFromGrams,
  parseGramsInput,
} from "@/lib/mealGrams";

function servingPortionHint(servingSize: string | null | undefined, servingGrams: number): string | null {
  const size = servingSize?.trim();
  if (!size) return null;
  if (/^\d+(?:[.,]\d+)?\s*g$/i.test(size)) return null;
  return `${size} ≈ ${viNum(Math.round(servingGrams))}g`;
}

export default function MealGramsInput({
  grams,
  servingGrams,
  servingSize,
  kcal100g,
  warn,
  onChange,
}: {
  grams: number;
  servingGrams: number;
  servingSize?: string | null;
  kcal100g: number;
  warn?: boolean;
  onChange: (grams: number) => void;
}) {
  const [text, setText] = useState(() => String(grams));
  useEffect(() => {
    setText(String(grams));
  }, [grams]);

  function commit(raw: string) {
    const parsed = parseGramsInput(raw);
    const next = clampMealGrams(parsed ?? grams);
    setText(String(next));
    onChange(next);
  }

  const typed = parseGramsInput(text);
  const liveGrams = typed != null && typed > 0 ? clampMealGrams(typed) : grams;
  const hint = servingPortionHint(servingSize, servingGrams);

  return (
    <div>
      <div
        className={`flex items-center justify-between rounded-lg px-2 py-1 ring-1 ${
          warn ? "bg-rose-50 ring-rose-200" : "bg-slate-50 ring-slate-200"
        }`}
      >
        <span className="text-[11px] font-semibold text-slate-500">Khối lượng</span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onChange(clampMealGrams(liveGrams - GRAMS_STEP))}
            disabled={liveGrams <= MIN_GRAMS}
            className="grid h-7 w-7 place-items-center rounded-md bg-white text-sm font-bold text-slate-600 ring-1 ring-slate-200 disabled:opacity-40"
            aria-label="Giảm khối lượng"
          >
            −
          </button>
          <div className="flex items-center gap-0.5">
            <input
              type="text"
              inputMode="decimal"
              value={text}
              onChange={(e) => {
                const raw = e.target.value;
                setText(raw);
                const parsed = parseGramsInput(raw);
                if (parsed != null && parsed > 0) onChange(clampMealGrams(parsed));
              }}
              onBlur={() => commit(text)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.currentTarget.blur();
                }
              }}
              className="w-14 bg-transparent py-0.5 text-center text-sm font-bold text-slate-800 outline-none"
              aria-label="Khối lượng gram"
            />
            <span className="text-[11px] font-semibold text-slate-500">g</span>
          </div>
          <button
            type="button"
            onClick={() => onChange(clampMealGrams(liveGrams + GRAMS_STEP))}
            className="grid h-7 w-7 place-items-center rounded-md bg-brand-500 text-sm font-bold text-white"
            aria-label="Tăng khối lượng"
          >
            +
          </button>
        </div>
      </div>
      <p className="mt-1 text-[11px] text-amber-800">
        {viNum(kcalFromGrams(kcal100g, liveGrams))} kcal
        {hint ? ` · ${hint}` : ` · ${viNum(Math.round(kcal100g))} kcal/100g`}
      </p>
    </div>
  );
}
