"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { plansApi, type PlanDay, type PlanDetail, type PlanSummary } from "@/lib/plansApi";
import { formatSetsReps, splitRoleLabel } from "@/lib/planLabels";
import { pickTodayDay, todaySessionMeta } from "@/lib/todayWorkout";
import PlanMealAccordion, {
  MEAL_GROUP_ORDER,
  firstFilledMealType,
  mealGroupTitle,
  mealSlotKcal,
} from "./plan-view/PlanMealAccordion";
import PlanMealRow from "./plan-view/PlanMealRow";
import ExerciseThumb from "./ExerciseThumb";

function sortPlansNewest(list: PlanSummary[]): PlanSummary[] {
  return [...list].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
}

function greeting(): string {
  const h = new Date().getHours();
  if (h < 11) return "Chào buổi sáng";
  if (h < 18) return "Chào buổi chiều";
  return "Chào buổi tối";
}

function TodayMeals({ day }: { day: PlanDay }) {
  if (!day.meals.length) return null;
  const openMeal = firstFilledMealType(day.meals);
  return (
    <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
      <h2 className="text-base font-extrabold tracking-tight">Ăn hôm nay</h2>
      <p className="mt-1 text-sm text-slate-500">Gợi ý theo lịch — không bắt buộc ghi nhật ký.</p>
      <div className="mt-3">
        {MEAL_GROUP_ORDER.map((mt) => {
          const slotMeals = day.meals.filter((m) => m.meal_type === mt);
          if (!slotMeals.length) return null;
          return (
            <PlanMealAccordion
              key={mt}
              title={mealGroupTitle(mt)}
              itemCount={slotMeals.length}
              kcal={mealSlotKcal(slotMeals)}
              defaultOpen={openMeal === mt}
            >
              <ul className="space-y-1.5">
                {slotMeals.map((m) => (
                  <PlanMealRow
                    key={m.id}
                    meal={m}
                    className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950"
                  />
                ))}
              </ul>
            </PlanMealAccordion>
          );
        })}
      </div>
    </div>
  );
}

export default function TodayHomePanel() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [detail, setDetail] = useState<PlanDetail | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const list = sortPlansNewest((await plansApi.list()).filter((p) => !p.is_template));
      setPlans(list);
      if (!list.length) {
        setDetail(null);
        return;
      }
      setDetail(await plansApi.get(list[0].id));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const today = useMemo(() => (detail ? pickTodayDay(detail) : null), [detail]);
  const meta = today ? todaySessionMeta(today) : null;
  const split = today ? splitRoleLabel(today.split_role) : null;
  const weekday = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  if (loading) {
    return <p className="text-sm text-slate-500">Đang tải buổi hôm nay…</p>;
  }

  if (plans.length === 0) {
    return (
      <div className="space-y-5">
        <div>
          <p className="text-sm font-semibold text-brand-700">{greeting()}</p>
          <h1 className="mt-1 text-2xl font-extrabold tracking-tight sm:text-3xl">
            Hôm nay tập gì?
          </h1>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-500">
            Chưa có lịch. Trả lời vài câu hỏi — TAPTOT xếp buổi tập vừa sức cho bạn.
          </p>
        </div>
        <div className="rounded-2xl bg-white p-6 text-center shadow-soft sm:p-10">
          <p className="text-base font-bold text-slate-800">Bắt đầu từ đây</p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
            Không cần biết bài tập. Chọn mục tiêu, nơi tập, thời gian — nhận lịch ngay.
          </p>
          <Link
            href="/tai-khoan/tao-lich-tap/taptot"
            className="mt-5 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-brand-500 px-6 text-base font-bold text-white shadow-soft hover:bg-brand-600 sm:w-auto"
          >
            Tạo lịch của tôi
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-semibold capitalize text-brand-700">{weekday}</p>
        <h1 className="mt-1 text-2xl font-extrabold tracking-tight sm:text-3xl">Hôm nay tập gì?</h1>
        <p className="mt-1 text-sm text-slate-500">{greeting()} — xem buổi và thực đơn gợi ý.</p>
      </div>

      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

      {today && meta ? (
        <div className="rounded-2xl bg-white p-5 shadow-soft sm:p-6">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Buổi hôm nay</p>
          <h2 className="mt-1 text-xl font-extrabold tracking-tight text-slate-900">{meta.title}</h2>
          {split && <p className="mt-1 text-sm font-semibold text-brand-700">{split}</p>}
          <p className="mt-2 text-sm text-slate-500">
            {meta.minutes} phút · {meta.exerciseCount} bài tập
            {meta.mealCount ? ` · ${meta.mealCount} món gợi ý` : ""}
          </p>

          <ul className="mt-4 space-y-2">
            {today.exercises.slice(0, 6).map((ex) => (
              <li key={ex.id} className="flex items-center gap-3 rounded-xl bg-slate-50 px-3 py-2">
                <ExerciseThumb
                  gif={ex.gif_url}
                  image={ex.image_url}
                  bodyPart={ex.body_part || ""}
                  className="h-11 w-11 shrink-0 rounded-lg"
                  emojiSize="text-xl"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-slate-900">{ex.name_vi}</p>
                  <p className="text-[11px] text-slate-500">
                    {formatSetsReps(ex.sets, ex.reps)}
                    {ex.body_part ? ` · ${ex.body_part}` : ""}
                  </p>
                </div>
              </li>
            ))}
            {today.exercises.length > 6 && (
              <li className="text-center text-xs font-semibold text-slate-400">
                +{today.exercises.length - 6} bài nữa trong lịch đầy đủ
              </li>
            )}
          </ul>

          <Link
            href="/tai-khoan/ke-hoach"
            className="mt-5 flex min-h-12 w-full items-center justify-center rounded-xl bg-brand-500 text-base font-bold text-white shadow-soft hover:bg-brand-600"
          >
            Xem lịch đầy đủ
          </Link>
        </div>
      ) : (
        <div className="rounded-2xl bg-white p-6 text-center shadow-soft">
          <p className="font-semibold text-slate-700">Hôm nay không có buổi tập trong lịch</p>
          <Link
            href="/tai-khoan/ke-hoach"
            className="mt-3 inline-block text-sm font-semibold text-brand-600"
          >
            Xem lịch của tôi
          </Link>
        </div>
      )}

      {today && <TodayMeals day={today} />}
    </div>
  );
}
