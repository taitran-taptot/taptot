"use client";

import { useMemo, useState } from "react";
import { nutrientsForGrams, toGrams, unitChoices, type UnitCode } from "@/lib/foodUnits";
import { viNum } from "@/lib/labels";
import type { Food } from "@/lib/types";

export default function FoodAmountConverter({ food }: { food: Food }) {
  const choices = useMemo(() => unitChoices(food), [food]);
  const [qty, setQty] = useState("100");
  const [unit, setUnit] = useState<UnitCode>("g");
  const activeUnit = choices.some((c) => c.id === unit) ? unit : "g";
  const amount = Number(String(qty).replace(",", "."));
  const grams = Number.isFinite(amount) ? toGrams(amount, activeUnit, food) : null;
  const nutrients = grams == null ? null : nutrientsForGrams(food, grams);

  return (
    <div className="mt-4 rounded-xl bg-white p-3 ring-1 ring-slate-100">
      <p className="text-sm font-bold text-slate-800">Đổi đơn vị</p>
      <div className="mt-3 flex gap-2">
        <input
          type="number"
          min={0}
          step="any"
          value={qty}
          onChange={(e) => setQty(e.target.value)}
          className="w-28 rounded-lg border border-slate-200 px-3 py-2 text-sm"
          aria-label="Số lượng"
        />
        <select
          value={activeUnit}
          onChange={(e) => setUnit(e.target.value as UnitCode)}
          className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
          aria-label="Đơn vị"
        >
          {choices.map((choice) => (
            <option key={choice.id} value={choice.id}>
              {choice.label}
            </option>
          ))}
        </select>
      </div>
      {grams == null || !nutrients ? (
        <p className="mt-2 text-sm text-slate-500">Chưa đổi được đơn vị này cho thực phẩm đang xem.</p>
      ) : (
        <p className="mt-2 text-sm text-slate-700">
          ≈ <span className="font-bold">{viNum(Math.round(grams * 10) / 10)} g</span>
          {" · "}
          <span className="font-bold text-brand-700">{viNum(Math.round(nutrients.calories))} kcal</span>
          {" · "}
          Đạm {viNum(Math.round(nutrients.protein_g * 10) / 10)}g · Tinh bột{" "}
          {viNum(Math.round(nutrients.carbs_g * 10) / 10)}g · Béo{" "}
          {viNum(Math.round(nutrients.fat_g * 10) / 10)}g
        </p>
      )}
    </div>
  );
}
