"use client";

import { useState } from "react";
import { viNum } from "@/lib/labels";
import type { CookedMacros, YieldPortion } from "@/lib/types";

export const COOKED_NUTRITION_NOTE =
  "Số liệu tính từ khối lượng nguyên liệu sống. Nước thêm vào hoặc nước bốc hơi làm thành phẩm nặng hơn hoặc nhẹ hơn, nên kcal trên 100g sau khi nấu khác định lượng, nhưng tổng calo và macro cả mẻ giữ nguyên.";

function MacroLines({ data }: { data: CookedMacros }) {
  return (
    <div className="mt-2 space-y-1 text-sm">
      <div className="flex justify-between">
        <span className="text-slate-500">Calo</span>
        <span className="font-semibold">{viNum(data.calories)} kcal</span>
      </div>
      <div className="flex justify-between">
        <span className="text-slate-500">Đạm</span>
        <span className="font-semibold">{viNum(data.protein_g)}g</span>
      </div>
      <div className="flex justify-between">
        <span className="text-slate-500">Tinh bột</span>
        <span className="font-semibold">{viNum(data.carbs_g)}g</span>
      </div>
      <div className="flex justify-between">
        <span className="text-slate-500">Chất béo</span>
        <span className="font-semibold">{viNum(data.fat_g)}g</span>
      </div>
      {data.fiber_g != null ? (
        <div className="flex justify-between">
          <span className="text-slate-500">Chất xơ</span>
          <span className="font-semibold">{viNum(data.fiber_g)}g</span>
        </div>
      ) : null}
    </div>
  );
}

export default function CookedNutritionPanel({
  batch,
  serving,
  per100,
  portions,
  yieldNote,
  sourceTitle,
  sourceUrl,
  note = COOKED_NUTRITION_NOTE,
}: {
  batch: CookedMacros | null;
  serving: CookedMacros | null;
  per100: CookedMacros | null;
  portions?: YieldPortion[];
  yieldNote?: string | null;
  sourceTitle?: string | null;
  sourceUrl?: string | null;
  note?: string | null;
}) {
  const [k, setK] = useState(1);
  const slices = portions || [];
  const active = slices.find((row) => row.k === k) || slices[0] || null;

  return (
    <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
      <h2 className="text-lg font-bold">Dinh dưỡng thành phẩm</h2>
      {note ? <p className="mt-2 text-sm leading-relaxed text-slate-600">{note}</p> : null}
      {yieldNote ? <p className="mt-2 text-sm text-slate-600">{yieldNote}</p> : null}
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {batch ? (
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Cả mẻ</p>
            <MacroLines data={batch} />
          </div>
        ) : null}
        {serving ? (
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              1 suất{serving.grams ? ` · ${viNum(serving.grams)}g` : ""}
            </p>
            <MacroLines data={serving} />
          </div>
        ) : null}
        {per100 ? (
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">100g đã nấu</p>
            <MacroLines data={per100} />
          </div>
        ) : null}
      </div>
      {slices.length > 1 ? (
        <div className="mt-4">
          <p className="text-sm font-semibold text-slate-700">Ăn một phần mẻ</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {slices.map((row) => (
              <button
                key={row.label}
                type="button"
                onClick={() => setK(row.k)}
                className={`rounded-full px-3 py-1.5 text-sm font-bold ${
                  active?.k === row.k ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700"
                }`}
              >
                {row.label}
              </button>
            ))}
          </div>
          {active ? (
            <p className="mt-2 text-sm text-slate-700">
              {active.label} mẻ · {viNum(active.grams)}g · {viNum(active.calories)} kcal · Đạm{" "}
              {viNum(active.protein_g)}g · Tinh bột {viNum(active.carbs_g)}g · Béo {viNum(active.fat_g)}g
            </p>
          ) : null}
        </div>
      ) : null}
      {sourceTitle ? (
        <p className="mt-4 text-xs leading-relaxed text-slate-500">
          Nguồn: {sourceTitle}
          {sourceUrl ? (
            <>
              {" "}
              <a href={sourceUrl} className="font-semibold text-brand-700 hover:underline" target="_blank" rel="noreferrer">
                Xem nguồn
              </a>
            </>
          ) : null}
        </p>
      ) : null}
    </section>
  );
}
