"use client";

import { useEffect, useMemo, useState } from "react";
import type { Activity, Gender, Goal } from "@/lib/types";
import {
  ACTIVITY_FIELD_LABEL,
  ACTIVITY_OPTS,
  CALCULATOR_GAIN_HINT,
  CALCULATOR_LOSS_HINT,
  GOAL_LABEL,
  GOAL_OPTS,
  bmiCategory,
  computeNutrition,
  defaultGainKgPerWeek,
  defaultLossKgPerWeek,
  formatKgVi,
  gainWeeklyKgOpts,
  lossWeeklyKgOpts,
  type LossWeeklyKgOpt,
  type NutritionResult,
} from "@/lib/nutrition";

function defaultKgForGoal(goal: Goal, weightKg: number) {
  if (goal === "gain_muscle") return defaultGainKgPerWeek(weightKg);
  return defaultLossKgPerWeek(weightKg);
}

export default function Calculator() {
  const [gender, setGender] = useState<Gender>("male");
  const [goal, setGoal] = useState<Goal>("lose_weight");
  const [activity, setActivity] = useState<Activity>("moderate");
  const [age, setAge] = useState("25");
  const [height, setHeight] = useState("170");
  const [weight, setWeight] = useState("65");
  const [kgPerWeek, setKgPerWeek] = useState(() => defaultLossKgPerWeek(65));
  const [result, setResult] = useState<NutritionResult | null>(null);
  const [appliedPace, setAppliedPace] = useState<LossWeeklyKgOpt | undefined>();

  const weightKg = Number.parseFloat(weight);
  const safeWeight = Number.isFinite(weightKg) && weightKg > 0 ? weightKg : 65;
  const lossOpts = useMemo(() => lossWeeklyKgOpts(safeWeight), [safeWeight]);
  const gainOpts = useMemo(() => gainWeeklyKgOpts(safeWeight), [safeWeight]);
  const paceOpts = goal === "gain_muscle" ? gainOpts : lossOpts;
  const showPace = goal === "lose_weight" || goal === "gain_muscle";
  const selectedPace =
    paceOpts.find((o) => o.value === kgPerWeek) ?? paceOpts.find((o) => o.recommended) ?? paceOpts[0];

  useEffect(() => {
    if (goal === "lose_weight") {
      const allowed = lossOpts.map((o) => o.value);
      if (!allowed.includes(kgPerWeek)) setKgPerWeek(defaultLossKgPerWeek(safeWeight));
      return;
    }
    if (goal === "gain_muscle") {
      const allowed = gainOpts.map((o) => o.value);
      if (!allowed.includes(kgPerWeek)) setKgPerWeek(defaultGainKgPerWeek(safeWeight));
    }
  }, [goal, gainOpts, kgPerWeek, lossOpts, safeWeight]);

  function calcNow(rate = kgPerWeek, paceOpt = selectedPace) {
    const w = parseFloat(weight);
    const h = parseFloat(height);
    const a = parseInt(age, 10);
    if (!(w > 0) || !(h > 0) || !(a >= 10)) return false;
    setResult(computeNutrition(gender, goal, activity, w, h, a, showPace ? rate : undefined));
    setAppliedPace(showPace ? paceOpt : undefined);
    return true;
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!calcNow()) {
      alert("Vui lòng nhập đúng tuổi, chiều cao và cân nặng.");
    }
  }

  return (
    <section>
      <div className="mb-5">
        <h1 className="type-display">Máy tính calo</h1>
        <p className="mt-1 text-sm text-slate-500">
          Biết cơ thể cần bao nhiêu calo mỗi ngày để giảm cân, giữ dáng hay tăng cân.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <form onSubmit={onSubmit} className="space-y-5 rounded-2xl bg-white p-5 shadow-soft lg:col-span-3">
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-600">Giới tính</label>
            <div className="grid grid-cols-2 gap-3">
              {(["male", "female"] as Gender[]).map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => setGender(g)}
                  className={`rounded-xl border py-2.5 font-semibold transition ${
                    gender === g
                      ? "border-brand-500 bg-brand-500 text-white shadow-soft"
                      : "border-slate-200 text-slate-500 hover:border-brand-300"
                  }`}
                >
                  {g === "male" ? "Nam" : "Nữ"}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-600">Tuổi</label>
              <input type="number" min={10} max={100} value={age} onChange={(e) => setAge(e.target.value)} className="field" />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-600">Chiều cao (cm)</label>
              <input type="number" min={120} max={220} value={height} onChange={(e) => setHeight(e.target.value)} className="field" />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-600">Cân nặng (kg)</label>
              <input type="number" min={30} max={250} step={0.1} value={weight} onChange={(e) => setWeight(e.target.value)} className="field" />
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-600">{ACTIVITY_FIELD_LABEL}</label>
            <select value={activity} onChange={(e) => setActivity(e.target.value as Activity)} className="field">
              {ACTIVITY_OPTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-600">Mục tiêu</label>
            <div className="grid grid-cols-3 gap-3">
              {GOAL_OPTS.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => {
                    setGoal(o.value);
                    setResult(null);
                    setAppliedPace(undefined);
                    if (o.value === "lose_weight" || o.value === "gain_muscle") {
                      setKgPerWeek(defaultKgForGoal(o.value, safeWeight));
                    }
                  }}
                  className={`flex flex-col items-center gap-1 rounded-xl border py-3 text-sm font-semibold transition ${
                    goal === o.value
                      ? "border-brand-500 bg-brand-50 text-brand-700"
                      : "border-slate-200 text-slate-500 hover:border-brand-300"
                  }`}
                >
                  <span className="text-xl">{o.icon}</span>
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {showPace && (
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-600">
                {goal === "lose_weight" ? "Mỗi tuần bạn muốn giảm" : "Mỗi tuần bạn muốn tăng"}
              </label>
              <div className="grid grid-cols-3 gap-2">
                {paceOpts.map((o) => (
                  <button
                    key={`${o.hint}-${o.value}`}
                    type="button"
                    onClick={() => {
                      setKgPerWeek(o.value);
                      if (result) calcNow(o.value, o);
                    }}
                    className={`rounded-xl border px-2 py-3 text-center transition ${
                      kgPerWeek === o.value
                        ? "border-brand-500 bg-brand-50 text-brand-800"
                        : "border-slate-200 text-slate-500"
                    }`}
                  >
                    <span className="block type-title">{o.label}</span>
                    <span className="mt-0.5 block text-[11px] font-semibold">{o.hint} / tuần</span>
                    <span className="mt-0.5 block text-[10px] font-medium text-slate-400">{o.pctLabel}</span>
                    {o.recommended ? (
                      <span className="mt-1 inline-block rounded-full bg-brand-100 px-1.5 py-px text-[10px] font-bold text-brand-700">
                        Gợi ý
                      </span>
                    ) : null}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-500">
                {goal === "lose_weight" ? CALCULATOR_LOSS_HINT : CALCULATOR_GAIN_HINT}
              </p>
            </div>
          )}

          <button
            type="submit"
            className="w-full rounded-xl bg-brand-500 py-3.5 text-base font-bold text-white shadow-soft transition hover:bg-brand-600"
          >
            Tính toán ngay
          </button>
          <p className="text-center text-xs text-slate-400">
            Kết quả chỉ mang tính tham khảo, dựa trên công thức Mifflin–St Jeor.
          </p>
        </form>

        <div className="lg:col-span-2">
          {!result ? (
            <div className="grid h-full place-items-center rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-400">
              <div>
                <div className="mb-3 text-5xl">📊</div>
                <p className="font-medium">Điền thông tin để xem kết quả</p>
                <p className="mt-1 text-sm">Chỉ số cân nặng và lượng calo mục tiêu mỗi ngày.</p>
              </div>
            </div>
          ) : (
            <ResultPanel result={result} goal={goal} selectedPace={showPace ? appliedPace : undefined} />
          )}
        </div>
      </div>
    </section>
  );
}

function ResultPanel({
  result,
  goal,
  selectedPace,
}: {
  result: NutritionResult;
  goal: Goal;
  selectedPace?: { value: number; hint: string; pctLabel: string };
}) {
  const cat = bmiCategory(result.bmi);
  const goalVi = GOAL_LABEL[goal];
  const diff = result.target - result.tdee;

  const pCal = result.protein_g * 4;
  const cCal = result.carbs_g * 4;
  const fCal = result.fat_g * 9;
  const tot = pCal + cCal + fCal || 1;
  const pct = (x: number) => Math.round((x / tot) * 100);

  const weeklyKgLabel = selectedPace ? formatKgVi(selectedPace.value) : null;
  const paceHint = selectedPace?.hint.toLowerCase() ?? "";
  const explain =
    goal === "lose_weight" && selectedPace
      ? `Bạn chọn giảm ${selectedPace.pctLabel} mỗi tuần (~${weeklyKgLabel}, mức ${paceHint}). Ăn khoảng ${result.target.toLocaleString("vi-VN")} kcal/ngày — thấp hơn mức duy trì ${Math.abs(diff)} kcal. Tốc độ này nằm trong khoảng an toàn 0,5–1% cân; nhanh hơn 1%/tuần dễ mất cơ và thiếu năng lượng.`
      : goal === "gain_muscle" && selectedPace
        ? `Bạn chọn tăng ${selectedPace.pctLabel} mỗi tuần (~${weeklyKgLabel}, mức ${paceHint}). Ăn khoảng ${result.target.toLocaleString("vi-VN")} kcal/ngày — cao hơn mức duy trì ${diff} kcal, ưu tiên đủ đạm và tập tạ. Tốc độ này nằm trong khoảng 0,25–0,75% cân; chậm hơn thì ít mỡ hơn.`
        : diff < 0
          ? `Để giảm cân, hãy ăn khoảng ${result.target.toLocaleString("vi-VN")} kcal/ngày — thấp hơn mức duy trì ${Math.abs(diff)} kcal.`
          : diff > 0
            ? `Để tăng cân, hãy ăn khoảng ${result.target.toLocaleString("vi-VN")} kcal/ngày — cao hơn mức duy trì ${diff} kcal, ưu tiên đủ đạm và tập tạ.`
            : `Để giữ dáng, hãy ăn khoảng ${result.target.toLocaleString("vi-VN")} kcal/ngày để giữ cân nặng ổn định.`;

  return (
    <div className="space-y-4">
      <div className={`flex items-center justify-between rounded-2xl p-4 ${cat.bg}`}>
        <div>
          <p className="text-xs text-slate-500">Chỉ số BMI</p>
          <p className={`mt-1 text-3xl leading-none font-bold ${cat.cls}`}>{result.bmi}</p>
        </div>
        <span className={`rounded-full bg-white px-3 py-1.5 text-sm font-semibold ${cat.cls}`}>{cat.vi}</span>
      </div>

      <div className="rounded-2xl bg-brand-500 p-5 text-center text-white shadow-soft">
        <p className="text-sm opacity-80">Calo mục tiêu để {goalVi}</p>
        <p className="mt-1 text-4xl font-bold">{result.target.toLocaleString("vi-VN")}</p>
        <p className="text-sm opacity-80">kcal / ngày</p>
        {selectedPace ? (
          <p className="mt-2 text-xs opacity-90">
            Tốc độ: {selectedPace.pctLabel}/tuần (~{weeklyKgLabel})
          </p>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl bg-white p-4 text-center shadow-soft">
          <p className="text-2xl font-bold">{result.bmr.toLocaleString("vi-VN")}</p>
          <p className="mt-0.5 text-[11px] text-slate-400">BMR — calo cơ thể đốt khi nghỉ</p>
        </div>
        <div className="rounded-2xl bg-white p-4 text-center shadow-soft">
          <p className="text-2xl font-bold">{result.tdee.toLocaleString("vi-VN")}</p>
          <p className="mt-0.5 text-[11px] text-slate-400">Calo duy trì cân nặng</p>
        </div>
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <p className="mb-3 font-bold">Gợi ý dinh dưỡng mỗi ngày</p>
        <div className="macro-track mb-3 h-3">
          <div style={{ width: `${pct(pCal)}%` }} className="bg-brand-500" />
          <div style={{ width: `${pct(cCal)}%` }} className="bg-amber-400" />
          <div style={{ width: `${pct(fCal)}%` }} className="bg-rose-400" />
        </div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-xl bg-slate-50 py-2.5">
            <p className="text-lg font-bold text-brand-600">{result.protein_g}g</p>
            <p className="text-[11px] text-slate-400">Đạm ({pct(pCal)}%)</p>
          </div>
          <div className="rounded-xl bg-slate-50 py-2.5">
            <p className="text-lg font-bold text-amber-600">{result.carbs_g}g</p>
            <p className="text-[11px] text-slate-400">Tinh bột ({pct(cCal)}%)</p>
          </div>
          <div className="rounded-xl bg-slate-50 py-2.5">
            <p className="text-lg font-bold text-rose-500">{result.fat_g}g</p>
            <p className="text-[11px] text-slate-400">Béo ({pct(fCal)}%)</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl bg-slate-50 p-4 text-sm leading-relaxed text-slate-600">{explain}</div>
      <p className="text-center text-xs text-slate-400">
        Sang tab <b>Thức ăn</b> để ước lượng calo thịt, rau, cơm bạn hay nấu.
      </p>
    </div>
  );
}
