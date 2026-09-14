"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  plansApi,
  type PlanDetail,
  type PlanExercise,
  type ExportFormat,
  type PlanExportOptions,
} from "@/lib/plansApi";
import { viNum } from "@/lib/labels";
import {
  friendlyPlanTitle,
  localizePlanDayTitle,
  parseSessionsPerWeek,
  splitRoleLabel,
} from "@/lib/planLabels";
import ExportCustomizeModal from "./ExportCustomizeModal";
import { usePlanKnowledge } from "./PlanKnowledgeToggle";
import { dayInsightFor, mealWhyFor } from "@/lib/planInsights";
import { groupPlanDaysByWeek, foundationWeekCoachBlurb } from "@/lib/planWeeks";
import { getAccessToken } from "@/lib/auth";
import { planAccountEditLoginPath, planAccountEditPath } from "@/lib/planEdit";
import PlanViewShell from "./plan-view/PlanViewShell";
import type { PlanViewTab } from "./plan-view/types";
import PlanWeekSessionNav from "./plan-view/PlanWeekSessionNav";
import PlanSessionPanel from "./plan-view/PlanSessionPanel";
import PlanMealsPanel from "./plan-view/PlanMealsPanel";
import PlanOverviewPanel from "./plan-view/PlanOverviewPanel";
import PlanExerciseDetailSheet from "./plan-view/PlanExerciseDetailSheet";

const ADVICE_MARKER = "Lời khuyên từ AI:";
const SAVE_PLAN_HREF = `/dang-nhap?next=${encodeURIComponent("/tai-khoan?saved=1")}`;

function formatExpireDate(iso: string | null | undefined): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

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

function parseSessionMinutes(desc: string | null | undefined): number | null {
  if (!desc) return null;
  const m = desc.match(/(\d+)\s*(?:phút|phut|min)/i);
  return m ? Number(m[1]) : null;
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
  const router = useRouter();
  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [exportFormat, setExportFormat] = useState<"xlsx" | "pdf" | "word" | null>(null);
  const [showFreshBanner, setShowFreshBanner] = useState(false);
  const [showTemNote, setShowTemNote] = useState(false);
  const [activeTab, setActiveTab] = useState<PlanViewTab>("overview");
  const [activeWeek, setActiveWeek] = useState(1);
  const [activeDayNumber, setActiveDayNumber] = useState(1);
  const [openRepeatWeeks, setOpenRepeatWeeks] = useState<Set<number>>(new Set());
  const [detailExercise, setDetailExercise] = useState<PlanExercise | null>(null);
  const { showKnowledge, setKnowledge } = usePlanKnowledge(false);

  const isAiPlan = plan?.source === "ai" && !!plan?.insights;
  const canNutritionCheckin = Boolean(
    plan && !plan.is_guest && getAccessToken() && (plan.insights?.nutrition_blocks?.length ?? 0) > 0,
  );

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
        setActiveWeek(1);
      })
      .catch((e) => setErr((e as Error).message || "Không tải được lịch tập."))
      .finally(() => setLoading(false));
  }, [token]);

  const weekGroups = useMemo(
    () => (plan ? groupPlanDaysByWeek(plan.days) : []),
    [plan],
  );

  const activeGroup = useMemo(
    () => weekGroups.find((g) => g.week === activeWeek) ?? weekGroups[0],
    [weekGroups, activeWeek],
  );

  const activeDay = useMemo(
    () => plan?.days.find((d) => d.day_number === activeDayNumber) ?? null,
    [plan, activeDayNumber],
  );

  const weekSummary = useMemo(() => {
    if (!plan) return null;
    const { summary } = splitPlanDescription(plan.description_vi);
    const minutes = parseSessionMinutes(summary) ?? 45;
    const sessions =
      parseSessionsPerWeek(summary) ??
      weekGroups[0]?.days.length ??
      plan.days.length;
    const splits = Array.from(
      new Set(
        plan.days
          .map((d) => splitRoleLabel(d.split_role))
          .filter((s): s is string => Boolean(s)),
      ),
    );
    return { minutes, sessions, splits, weekCount: weekGroups.length };
  }, [plan, weekGroups]);

  const firstDayLabel = useMemo(() => {
    if (!plan) return null;
    const first = plan.days.find((d) => d.exercises.length > 0);
    return first ? localizePlanDayTitle(first.title_vi) || null : null;
  }, [plan]);

  function goSwap(ex: PlanExercise) {
    if (!plan) return;
    const q = { week: activeWeek, day: activeDayNumber, swap: ex.exercise_id };
    const href = getAccessToken()
      ? planAccountEditPath(plan.id, q)
      : planAccountEditLoginPath(plan.id, q);
    router.push(href);
  }

  async function runExport(format: ExportFormat, options: PlanExportOptions) {
    if (!token) return;
    await plansApi.exportShared(token, format, options);
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
              href="/tao-lich-tap/taptot"
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
  const homeFoundation = Boolean(
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
  const heroChips =
    inputChips.length > 0
      ? inputChips
      : weekSummary
        ? [
            `${weekSummary.sessions} buổi/tuần`,
            weekSummary.weekCount > 1 ? `${weekSummary.weekCount} tuần` : "",
            `${weekSummary.minutes} phút/buổi`,
            ...weekSummary.splits,
          ].filter(Boolean)
        : [];

  const calorieLine =
    plan.target_calories != null
      ? `~${viNum(plan.target_calories)} kcal trung bình/ngày`
      : null;
  const hasFlexibleDayCalories =
    plan.target_calories != null &&
    plan.days.some(
      (d) =>
        d.target_calories != null &&
        Math.abs(d.target_calories - (plan.target_calories as number)) > 50,
    );
  const calorieHint = hasFlexibleDayCalories
    ? "Ngày tập ăn nhiều hơn · ngày nghỉ ít hơn"
    : null;

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

  const showSessionNav = activeTab !== "overview" && weekGroups.length > 0;

  return (
    <>
      {showFreshBanner && (
        <div className="mx-auto max-w-3xl px-3 pt-4 sm:px-4 lg:max-w-5xl">
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-soft">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-extrabold text-emerald-900">
                  {homeFoundation ? "Lộ trình xây nền của bạn đã sẵn sàng" : "Lịch của bạn đã sẵn sàng"}
                </p>
                <p className="mt-0.5 text-sm text-emerald-800/80">
                  {homeFoundation
                    ? "8 tuần · tháng 1 làm quen đúng sức nền, tháng 2 tập chắc hơn. Mở tab Buổi tập để bắt đầu."
                    : "Chọn buổi tập ở tab Buổi tập để bắt đầu."}
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
        recap={inputRecap}
        chips={heroChips}
        calorieLine={calorieLine}
        calorieHint={calorieHint}
        belowHero={
          plan.is_guest ? (
            <div className="rounded-2xl border border-accent-100 bg-accent-50 p-4 shadow-soft sm:p-5">
              <p className="text-sm font-bold leading-snug text-slate-800">
                {homeFoundation
                  ? `Lịch xây nền giữ ${
                      plan.challenge_100_days || plan.insights?.challenge_100_days ? "110" : "100"
                    } ngày`
                  : `Lịch giữ ${
                      plan.challenge_100_days || plan.insights?.challenge_100_days ? "110" : "100"
                    } ngày`}
                {formatExpireDate(plan.expires_at)
                  ? ` (đến ${formatExpireDate(plan.expires_at)})`
                  : ""}
              </p>
              <p className="mt-1.5 text-sm text-slate-600">
                {homeFoundation
                  ? "Lưu vào tài khoản để giữ cả lộ trình 8 tuần — miễn phí, khoảng một phút."
                  : "Lưu vào tài khoản để giữ lâu hơn — miễn phí, khoảng một phút."}
              </p>
              <Link
                href={SAVE_PLAN_HREF}
                className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-accent-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-accent-600 sm:w-auto"
              >
                Lưu lịch tập
              </Link>
            </div>
          ) : null
        }
        activeTab={activeTab}
        onTabChange={setActiveTab}
        nav={
          showSessionNav ? (
            <PlanWeekSessionNav
              weekGroups={weekGroups}
              activeWeek={activeWeek}
              activeDayNumber={activeDayNumber}
              homeFoundation={homeFoundation}
              onWeekChange={(week, firstDay) => {
                setActiveWeek(week);
                setActiveDayNumber(firstDay);
              }}
              onDayChange={setActiveDayNumber}
            />
          ) : undefined
        }
      >
        {activeTab === "train" && (
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
              <PlanSessionPanel
                day={activeDay}
                showKnowledge={showDayKnowledge}
                whyByExerciseId={whyByExerciseId}
                canSwap
                onSelectExercise={setDetailExercise}
                onSwapClick={goSwap}
                onGoMeals={() => setActiveTab("meals")}
              />
            ) : (
              <p className="text-center text-sm text-slate-400">Không có buổi tập.</p>
            )}
          </>
        )}

        {activeTab === "meals" && (
          <PlanMealsPanel
            day={activeDay}
            insights={plan.insights}
            showMealWhy={showDayKnowledge}
            mealWhyForSlot={(foodId, mealType) =>
              dayInsight ? mealWhyFor(dayInsight, foodId, mealType) : undefined
            }
          />
        )}

        {activeTab === "overview" && (
          <PlanOverviewPanel
            plan={plan}
            isAiPlan={!!isAiPlan}
            showKnowledge={showKnowledge}
            onKnowledgeChange={setKnowledge}
            weekSummary={weekSummary}
            firstDayLabel={firstDayLabel}
            onGoToTab={setActiveTab}
            onExport={(fmt) => setExportFormat(fmt)}
            canNutritionCheckin={canNutritionCheckin}
            onPlanUpdated={setPlan}
          />
        )}

        {plan.days.every((d) => d.exercises.length === 0 && d.meals.length === 0) && (
          <div className="mt-4 rounded-2xl bg-white p-5 text-center shadow-soft">
            <p className="text-sm font-semibold text-slate-600">Lịch này chưa có nội dung</p>
            <Link
              href="/tao-lich-tap/taptot"
              className="mt-4 inline-flex min-h-11 items-center rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white hover:bg-brand-600"
            >
              Tạo lịch với TAPTOT
            </Link>
          </div>
        )}
      </PlanViewShell>

      <PlanExerciseDetailSheet
        exercise={detailExercise}
        why={detailWhy}
        canSwap
        onSwap={() => detailExercise && goSwap(detailExercise)}
        onClose={() => setDetailExercise(null)}
      />

      <ExportCustomizeModal
        open={!!exportFormat}
        format={exportFormat}
        defaultStartDate={plan.start_date}
        onClose={() => setExportFormat(null)}
        onExport={runExport}
      />
    </>
  );
}
