"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  plansApi,
  PLAN_SECTION_ORDER,
  SECTION_LABEL,
  type PlanDetail,
  type PlanExercise,
} from "@/lib/plansApi";
import { viNum } from "@/lib/labels";
import {
  friendlyPlanTitle,
  isFitnessAdvancedPlan,
  localizePlanDayTitle,
  localizeWorkoutCopy,
  parseSessionsPerWeek,
  splitRoleShortLabel,
  estimatePlanDayMinutes,
} from "@/lib/planLabels";
import { usePlanKnowledge } from "./PlanKnowledgeToggle";
import { dayInsightFor, mealWhyFor } from "@/lib/planInsights";
import { groupPlanDaysByWeek, foundationWeekCoachBlurb, weekGroupForDay } from "@/lib/planWeeks";
import PlanViewShell from "./plan-view/PlanViewShell";
import type { PlanViewTab } from "./plan-view/types";
import { PLAN_VIEW_TABS } from "./plan-view/types";
import PlanWeekSessionNav from "./plan-view/PlanWeekSessionNav";
import PlanExerciseList from "./plan-view/PlanExerciseList";
import PlanMealsPanel from "./plan-view/PlanMealsPanel";
import PlanOverviewPanel from "./plan-view/PlanOverviewPanel";
import PlanExerciseDetailSheet from "./plan-view/PlanExerciseDetailSheet";
import BrandWordmark from "@/components/BrandWordmark";
import { FAMILIARIZATION_HERO_RECAP_VI } from "@/lib/familiarizationOverviewCopy";
import { isFamiliarizationPlan } from "@/lib/isFamiliarizationPlan";

const ADVICE_MARKER = "Lời khuyên từ AI:";

function splitPlanDescription(description: string | null | undefined): {
  summary: string | null;
  advice: string[];
} {
  if (!description?.trim()) return { summary: null, advice: [] };
  const idx = description.indexOf(ADVICE_MARKER);
  if (idx < 0) return { summary: description.trim(), advice: [] };
  const summary = description.slice(0, idx).trim() || null;
  const advice = description
    .slice(idx + ADVICE_MARKER.length)
    .split("\n")
    .map((line) => line.replace(/^[•\-*–—]\s*/, "").trim())
    .filter(Boolean)
    .slice(0, 5);
  return { summary, advice };
}

function looksLikeEngineDump(text: string): boolean {
  return /Master\s*`|set\/tuần|LISS|volume tuần|pattern bắt buộc|Chu kỳ\s+\d+\s+tuần|thời lượng buổi giữ/i.test(
    text,
  );
}

export default function PlanShareView({ token: tokenProp }: { token?: string }) {
  const params = useParams();
  const token =
    tokenProp || (typeof params.token === "string" ? params.token : "");
  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportErr, setExportErr] = useState("");
  const [showFreshBanner, setShowFreshBanner] = useState(false);
  const [showTemNote, setShowTemNote] = useState(false);
  const [activeTab, setActiveTab] = useState<PlanViewTab>("overview");
  const [activeWeek, setActiveWeek] = useState(1);
  const [activeDayNumber, setActiveDayNumber] = useState(1);
  const [openRepeatWeeks, setOpenRepeatWeeks] = useState<Set<number>>(new Set());
  const [detailExercise, setDetailExercise] = useState<PlanExercise | null>(null);
  const { showKnowledge, setKnowledge } = usePlanKnowledge(false);

  const isAiPlan = plan?.source === "ai" && !!plan?.insights;

  useEffect(() => {
    const qs = new URLSearchParams(window.location.search);
    if (qs.get("moi") === "1") {
      setShowFreshBanner(true);
      setShowTemNote(qs.get("tem") === "1");
      const url = new URL(window.location.href);
      url.searchParams.delete("moi");
      url.searchParams.delete("tem");
      window.history.replaceState({}, "", url.pathname + url.search + url.hash);
    }
  }, []);

  useEffect(() => {
    if (!showFreshBanner) return;
    const t = window.setTimeout(() => setShowFreshBanner(false), 8000);
    return () => window.clearTimeout(t);
  }, [showFreshBanner]);

  useEffect(() => {
    if (!token) {
      setErr("Link không hợp lệ.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setErr("");
    plansApi
      .getByShareToken(token)
      .then((p) => {
        setPlan(p);
        const first = p.days[0]?.day_number ?? 1;
        setActiveDayNumber(first);
        const groups = groupPlanDaysByWeek(p.days);
        setActiveWeek(weekGroupForDay(groups, first)?.week ?? 1);
      })
      .catch((e) => setErr((e as Error).message || "Không tải được lịch tập."))
      .finally(() => setLoading(false));
  }, [token]);

  const weekGroups = useMemo(
    () => (plan ? groupPlanDaysByWeek(plan.days) : []),
    [plan],
  );

  const resolvedWeek =
    weekGroupForDay(weekGroups, activeDayNumber)?.week ?? activeWeek;

  const activeGroup = useMemo(
    () => weekGroups.find((g) => g.week === resolvedWeek) ?? weekGroups[0],
    [weekGroups, resolvedWeek],
  );

  const activeDay = useMemo(
    () => plan?.days.find((d) => d.day_number === activeDayNumber) ?? null,
    [plan, activeDayNumber],
  );

  const weekSummary = useMemo(() => {
    if (!plan) return null;
    const { summary } = splitPlanDescription(plan.description_vi);
    const trainingDays = plan.days.filter((d) => d.exercises.length > 0);
    const minutes = trainingDays.length
      ? Math.round(
          trainingDays.reduce((sum, d) => sum + estimatePlanDayMinutes(d.exercises), 0) /
            trainingDays.length,
        )
      : 0;
    const sessions =
      plan.insights?.sessions_per_week ??
      parseSessionsPerWeek(summary) ??
      (trainingDays.length || weekGroups[0]?.days.length || plan.days.length);
    const familiarizationPlan = isFamiliarizationPlan(plan);
    const splits = familiarizationPlan
      ? ["Toàn thân"]
      : Array.from(
          new Set(
            plan.days
              .filter((d) => d.exercises.length > 0)
              .map((d) => splitRoleShortLabel(d.split_role))
              .filter((s): s is string => Boolean(s)),
          ),
        );
    return {
      minutes,
      minutesLabel: familiarizationPlan ? "30-45′" : undefined,
      sessions,
      splits,
      weekCount: weekGroups.length,
      durationDays: plan.insights?.duration_days,
    };
  }, [plan, weekGroups]);

  async function runExport() {
    if (!token || exporting) return;
    setExporting(true);
    setExportErr("");
    try {
      await plansApi.exportShared(token, {});
    } catch (ex) {
      setExportErr((ex as Error).message || "Xuất file thất bại.");
    } finally {
      setExporting(false);
    }
  }

  if (loading) {
    return (
      <section className="mx-auto max-w-3xl px-4 py-10">
        <p className="text-center text-sm text-slate-400">Đang tải lịch tập…</p>
      </section>
    );
  }

  if (err || !plan) {
    const expired = (err || "").includes("hết hạn");
    return (
      <section className="mx-auto max-w-3xl px-4 py-10">
        <div className="rounded-2xl bg-white p-6 text-center shadow-soft">
          <p className="text-rose-500">{err || "Không tìm thấy lịch tập."}</p>
          {expired && (
            <Link
              href="/batdau?moi=1"
              className="mt-4 inline-flex rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
            >
              Tạo lịch mới
            </Link>
          )}
        </div>
      </section>
    );
  }

  const { summary } = splitPlanDescription(plan.description_vi);
  const inputRecap =
    plan.insights?.inputs?.recap_vi?.trim() ||
    (!looksLikeEngineDump(summary || "") ? summary : null);
  const isFamiliarization = isFamiliarizationPlan(plan);
  const homeFoundation = Boolean(
    isFamiliarization ||
      plan.insights?.challenge_kind === "home_foundation" ||
      plan.insights?.generation_mode === "free_home" ||
      (plan.insights?.inputs?.chips || []).some((c) => /xây nền thể lực/i.test(c)),
  );
  const displayTitle = friendlyPlanTitle(plan.title_vi, {
    challenge: Boolean(plan.challenge_100_days || plan.insights?.challenge_100_days),
    homeFoundation,
  });
  const foundationBlurb =
    homeFoundation && activeGroup
      ? foundationWeekCoachBlurb(activeGroup.week)
      : null;
  const inputChips = (plan.insights?.inputs?.chips || []).filter(Boolean);
  const heroChips = isFamiliarization
    ? []
    : inputChips.length > 0
      ? inputChips
      : weekSummary
        ? [
            `${weekSummary.sessions} buổi/tuần`,
            weekSummary.durationDays
              ? `${weekSummary.durationDays} ngày`
              : weekSummary.weekCount > 1
                ? `${weekSummary.weekCount} tuần`
                : "",
            weekSummary.minutesLabel
              ? `${weekSummary.minutesLabel.replace(/′$/, "")} phút/buổi`
              : weekSummary.minutes
                ? `${weekSummary.minutes} phút/buổi`
                : "",
            ...weekSummary.splits,
          ].filter(Boolean)
        : [];
  const heroRecap = isFamiliarization ? FAMILIARIZATION_HERO_RECAP_VI : inputRecap;
  const planTabs = isFamiliarization
    ? PLAN_VIEW_TABS.filter((tab) => tab.id !== "meals")
    : PLAN_VIEW_TABS;
  const viewTabSafe: PlanViewTab =
    isFamiliarization && activeTab === "meals" ? "overview" : activeTab;

  const calorieLine =
    isFamiliarization
      ? null
      : plan.target_calories != null
        ? `~${viNum(plan.target_calories)} kcal trung bình/ngày`
        : null;
  const hasFlexibleDayCalories =
    plan.target_calories != null &&
    plan.days.some(
      (d) =>
        d.target_calories != null &&
        Math.abs(d.target_calories - (plan.target_calories as number)) > 50,
    );
  const calorieHint =
    isFamiliarization || !hasFlexibleDayCalories
      ? null
      : "Ngày tập ăn nhiều hơn · ngày nghỉ ít hơn";

  const showRepeatBanner =
    activeGroup?.isRepeatOfWeek1 && !openRepeatWeeks.has(activeGroup.week);

  const dayInsight = isAiPlan && activeDay
    ? dayInsightFor(plan.insights, activeDay.day_number)
    : undefined;
  const showDayKnowledge = isAiPlan && showKnowledge;
  const whyByExerciseId: Record<number, string> = {};
  if (showDayKnowledge && dayInsight?.exercises) {
    for (const e of dayInsight.exercises) {
      whyByExerciseId[e.exercise_id] = e.why_vi;
    }
  }

  const detailWhy = detailExercise
    ? showDayKnowledge
      ? whyByExerciseId[detailExercise.exercise_id] ||
        detailExercise.notes_vi?.trim() ||
        undefined
      : undefined
    : undefined;

  const viewTab = viewTabSafe;
  const showSessionNav = viewTab !== "overview" && weekGroups.length > 0;
  const hideShareExport = isFitnessAdvancedPlan(plan);

  return (
    <>
      {showFreshBanner && (
        <div className="mx-auto max-w-3xl px-3 pt-4 sm:px-4 lg:max-w-5xl">
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-soft">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold text-emerald-900">
                  {homeFoundation ? "Lộ trình xây nền của bạn đã sẵn sàng" : "Lịch của bạn đã sẵn sàng"}
                </p>
                <p className="mt-0.5 text-sm text-emerald-800/80">
                  {homeFoundation
                    ? "8 tuần · tháng 1 làm quen đúng sức nền, tháng 2 tập chắc hơn. Mở tab Bài tập để xem lịch."
                    : "Mở tab Bài tập để xem lịch tập."}
                  {showTemNote ? " Mã trên tem đã dùng xong." : ""}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowFreshBanner(false)}
                className="shrink-0 rounded-lg px-2 py-1 text-xs font-semibold text-emerald-700/70 hover:bg-emerald-100"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      <PlanViewShell
        title={displayTitle}
        recap={heroRecap}
        chips={heroChips}
        calorieLine={calorieLine}
        calorieHint={calorieHint}
        activeTab={viewTab}
        onTabChange={setActiveTab}
        tabs={planTabs}
        naturalHeight
        nav={
          showSessionNav ? (
            <PlanWeekSessionNav
              weekGroups={weekGroups}
              activeWeek={resolvedWeek}
              activeDayNumber={activeDayNumber}
              homeFoundation={homeFoundation}
              plainWeekLabels={plan.source === "manual"}
              onWeekChange={(week, firstDay) => {
                setActiveWeek(week);
                setActiveDayNumber(firstDay);
              }}
              onDayChange={(dayNumber) => {
                setActiveDayNumber(dayNumber);
                const w = weekGroupForDay(weekGroups, dayNumber)?.week;
                if (w != null) setActiveWeek(w);
              }}
            />
          ) : undefined
        }
      >
        {viewTab === "train" && (
          <>
            {foundationBlurb && !showRepeatBanner ? (
              <div className="rounded-2xl border border-sky-100 bg-sky-50/90 p-4 shadow-soft sm:p-5">
                <p className="font-bold text-sky-950">{foundationBlurb.title}</p>
                <p className="mt-1 text-sm leading-relaxed text-slate-600">
                  {foundationBlurb.body}
                </p>
              </div>
            ) : null}
            {showRepeatBanner ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
                <p className="font-bold text-slate-800">
                  Tuần {activeGroup!.week}
                  {activeGroup!.phase != null ? ` · giai đoạn ${activeGroup!.phase}` : ""}: lặp lại
                  tuần mẫu
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  Cùng bài với tuần đầu giai đoạn này, cùng số hiệp và số lần. Khi thấy nhẹ hơn, hãy
                  tăng tạ một chút.
                </p>
                <button
                  type="button"
                  className="mt-3 text-sm font-semibold text-brand-700 hover:underline"
                  onClick={() => {
                    setOpenRepeatWeeks((prev) => {
                      const next = new Set(prev);
                      next.add(activeGroup!.week);
                      return next;
                    });
                  }}
                >
                  Xem chi tiết tuần này
                </button>
              </div>
            ) : activeDay ? (
              <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
                <h2 className="text-base font-bold text-slate-900 [overflow-wrap:anywhere]">
                  {(isFamiliarization
                    ? localizeWorkoutCopy(localizePlanDayTitle(activeDay.title_vi))
                    : localizePlanDayTitle(activeDay.title_vi)) || `Ngày ${activeDay.day_number}`}
                </h2>
                {activeDay.exercises.length === 0 ? (
                  <p className="mt-3 text-sm text-slate-500">Ngày này chưa có bài tập.</p>
                ) : (
                  <div className="mt-4">
                    {PLAN_SECTION_ORDER.map((sec) => {
                      const items = activeDay.exercises.filter((e) => e.section === sec);
                      if (!items.length) return null;
                      return (
                        <div key={sec} className="mb-4 last:mb-0">
                          <p className="type-kicker mb-2 text-slate-500">
                            {SECTION_LABEL[sec] || sec}
                          </p>
                          <PlanExerciseList
                            exercises={items}
                            section={sec}
                            showKnowledge={showDayKnowledge}
                            whyByExerciseId={whyByExerciseId}
                            foundation={isFamiliarization}
                            onSelect={setDetailExercise}
                          />
                        </div>
                      );
                    })}
                  </div>
                )}
                {!isFamiliarization && activeDay.meals.length > 0 ? (
                  <button
                    type="button"
                    onClick={() => setActiveTab("meals")}
                    className="mt-4 w-full rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-brand-700 hover:border-brand-300 hover:bg-brand-50"
                  >
                    Xem thực đơn ngày này →
                  </button>
                ) : null}
              </div>
            ) : (
              <p className="text-center text-sm text-slate-400">Không có bài tập.</p>
            )}
          </>
        )}

        {viewTab === "meals" && (
          <PlanMealsPanel
            day={activeDay}
            days={plan.days}
            weekGroups={weekGroups}
            insights={plan.insights}
            showMealWhy={showDayKnowledge}
            mealWhyForSlot={(foodId, mealType) =>
              dayInsight ? mealWhyFor(dayInsight, foodId, mealType) : undefined
            }
          />
        )}

        {viewTab === "overview" && (
          <PlanOverviewPanel
            plan={plan}
            weekSummary={weekSummary}
            onExport={hideShareExport ? undefined : runExport}
            exportError={exportErr}
            exporting={exporting}
          />
        )}

        {plan.days.every((d) => d.exercises.length === 0 && d.meals.length === 0) && (
          <div className="mt-4 rounded-2xl bg-white p-5 text-center shadow-soft">
            <p className="text-sm font-semibold text-slate-600">Lịch này chưa có nội dung</p>
            <Link
              href="/batdau?moi=1"
              className="mt-4 inline-flex min-h-11 items-center rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white hover:bg-brand-600"
            >
              Tạo lịch với <BrandWordmark />
            </Link>
          </div>
        )}
      </PlanViewShell>

      <PlanExerciseDetailSheet
        exercise={detailExercise}
        why={detailWhy}
        foundation={isFamiliarization}
        onClose={() => setDetailExercise(null)}
      />

    </>
  );
}
