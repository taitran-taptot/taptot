"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import Modal from "./Modal";
import ExportCustomizeModal from "./ExportCustomizeModal";
import {
  PLAN_SECTION_ORDER,
  SECTION_LABEL,
  SOURCE_LABEL,
  plansApi,
  type PlanDetail,
  type PlanQuota,
  type PlanSummary,
  type ExportFormat,
  type PlanExportOptions,
} from "@/lib/plansApi";
import { claimGuestPlansAfterAuth } from "@/lib/authApi";
import { formatSetsReps, splitRoleLabel } from "@/lib/planLabels";
import { dayInsightFor, exerciseWhyFor, mealWhyFor } from "@/lib/planInsights";
import PlanKnowledgeToggle, { usePlanKnowledge } from "./PlanKnowledgeToggle";
import PlanInsightsPanel from "./PlanInsightsPanel";
import PlanMealRow from "./plan-view/PlanMealRow";
import PlanMealAccordion, {
  MEAL_GROUP_ORDER,
  firstFilledMealType,
  mealGroupTitle,
  mealSlotKcal,
} from "./plan-view/PlanMealAccordion";
import {
  buildShareMessage,
  copyText,
  planShareUrl,
  sharePlanNative,
} from "@/lib/sharePlan";
import { planAccountEditPath } from "@/lib/planEdit";

function MealAccordionList({
  meals,
  showWhy,
  dayInsight,
}: {
  meals: PlanDetail["days"][number]["meals"];
  showWhy: boolean;
  dayInsight: ReturnType<typeof dayInsightFor>;
}) {
  const openMeal = firstFilledMealType(meals);
  return (
    <div>
      {MEAL_GROUP_ORDER.map((mt) => {
        const slotMeals = meals.filter((m) => m.meal_type === mt);
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
                  why={
                    showWhy
                      ? mealWhyFor(dayInsight, m.food_id, m.meal_type) || m.notes_vi
                      : undefined
                  }
                  className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950"
                />
              ))}
            </ul>
          </PlanMealAccordion>
        );
      })}
    </div>
  );
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function MyPlansPanel() {
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [detail, setDetail] = useState<PlanDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [exportFormat, setExportFormat] = useState<"xlsx" | "pdf" | "word" | null>(null);
  const [quota, setQuota] = useState<PlanQuota | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [savedToast, setSavedToast] = useState(false);
  const [highlightId, setHighlightId] = useState<number | null>(null);
  const { showKnowledge, setKnowledge } = usePlanKnowledge(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      await claimGuestPlansAfterAuth();
      const [list, q] = await Promise.all([plansApi.list(), plansApi.quota()]);
      setPlans(list);
      setQuota(q);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const qs = new URLSearchParams(window.location.search);
    if (qs.get("saved") !== "1") return;
    const url = new URL(window.location.href);
    url.searchParams.delete("saved");
    window.history.replaceState({}, "", url.pathname + url.search + url.hash);
    setSavedToast(true);
  }, []);

  useEffect(() => {
    if (!savedToast || plans.length === 0) return;
    setHighlightId(plans[0].id);
  }, [savedToast, plans]);

  async function openPlan(id: number) {
    setDetailLoading(true);
    setErr("");
    try {
      setDetail(await plansApi.get(id));
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setDetailLoading(false);
    }
  }

  async function runExport(format: ExportFormat, options: PlanExportOptions) {
    if (!detail) return;
    await plansApi.export(detail.id, format, options);
  }

  async function doDelete() {
    if (!detail) return;
    if (!window.confirm("Xóa lịch tập này? Hành động không hoàn tác.")) return;
    try {
      await plansApi.remove(detail.id);
      setDetail(null);
      await load();
    } catch (ex) {
      setErr((ex as Error).message);
    }
  }

  function closeDetail() {
    setDetail(null);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Lịch tập của tôi</h1>
        <p className="mt-1 text-sm text-slate-500">
          Bấm vào khối để xem / chỉnh sửa bài tập (set/rep) và thực đơn. Calo mục tiêu không đổi.
        </p>
        <p className="mt-2 text-xs font-medium text-slate-500">
          Đang có {quota?.used ?? plans.length} lịch trong tài khoản
          {quota?.unlimited ? " (không giới hạn lưu trữ)." : "."}
        </p>
      </div>

      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

      {loading ? (
        <p className="text-sm text-slate-400">Đang tải lịch…</p>
      ) : plans.length === 0 ? (
        <div className="rounded-2xl bg-white p-8 text-center shadow-soft">
          <p className="font-semibold text-slate-600">Chưa có lịch nào</p>
          <p className="mt-1 text-sm text-slate-400">Chọn mục tiêu — TAPTOT xếp lịch giúp bạn. Không cần biết thuật ngữ tập luyện.</p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <Link
              href="/tai-khoan/tao-lich-tap/taptot"
              className="rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
            >
              Tạo lịch của tôi
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {plans.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => void openPlan(p.id)}
              className={`rounded-2xl bg-white p-5 text-left shadow-soft transition hover:ring-2 hover:ring-brand-200 ${
                highlightId === p.id ? "ring-2 ring-brand-500" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <h2 className="line-clamp-2 text-base font-bold text-slate-800">{p.title_vi}</h2>
                <span className="badge badge-easy shrink-0">{SOURCE_LABEL[p.source] || p.source}</span>
              </div>
              {p.description_vi && (
                <p className="clamp-2 mt-2 text-sm text-slate-500">{p.description_vi}</p>
              )}
              <div className="mt-4 flex flex-wrap gap-3 text-xs font-semibold text-slate-500">
                <span>{p.day_count} ngày</span>
                <span>·</span>
                <span>{p.exercise_count} bài</span>
                <span>·</span>
                <span>{p.meal_count} món</span>
                {p.target_calories ? (
                  <>
                    <span>·</span>
                    <span className="text-brand-600">{p.target_calories} kcal</span>
                  </>
                ) : null}
              </div>
              <p className="mt-3 text-[11px] text-slate-400">Tạo {formatDate(p.created_at)}</p>
            </button>
          ))}
        </div>
      )}

      {detailLoading && <p className="text-center text-sm text-slate-400">Đang mở chi tiết…</p>}

      <Modal open={savedToast} onClose={() => setSavedToast(false)}>
        <div className="space-y-3 p-5 text-center">
          <p className="text-lg font-extrabold text-slate-800">Đã lưu lịch tập vừa tạo.</p>
          <p className="text-sm text-slate-500">
            Lịch nằm trong danh sách bên dưới — không còn bị xóa sau 100 ngày.
          </p>
          <button
            type="button"
            onClick={() => setSavedToast(false)}
            className="rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
          >
            Đóng
          </button>
        </div>
      </Modal>

      <Modal open={!!detail} onClose={closeDetail} size="wide">
        {detail && (
          <div className="space-y-4 p-4 sm:p-5">
            <div className="flex items-start justify-between gap-3">
              <h2 className="text-xl font-extrabold tracking-tight">{detail.title_vi}</h2>
              <button
                type="button"
                onClick={closeDetail}
                className="rounded-lg px-2 py-1 text-sm font-semibold text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                Đóng
              </button>
            </div>

            <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
                {detail.description_vi && !detail.insights && (
                  <p className="text-sm text-slate-600">{detail.description_vi}</p>
                )}
                {detail.source === "ai" && detail.insights && (
                  <div className="space-y-3">
                    <PlanKnowledgeToggle checked={showKnowledge} onChange={setKnowledge} />
                    {showKnowledge && <PlanInsightsPanel insights={detail.insights} />}
                  </div>
                )}
                <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-500">
                  <span className="badge badge-easy">{SOURCE_LABEL[detail.source] || detail.source}</span>
                  <span>{detail.day_count} ngày</span>
                  {detail.target_calories ? <span>{detail.target_calories} kcal/ngày</span> : null}
                  {detail.target_protein_g != null ? (
                    <span>P {Math.round(detail.target_protein_g)}g</span>
                  ) : null}
                  {detail.target_carbs_g != null ? (
                    <span>C {Math.round(detail.target_carbs_g)}g</span>
                  ) : null}
                  {detail.target_fat_g != null ? (
                    <span>F {Math.round(detail.target_fat_g)}g</span>
                  ) : null}
                  {detail.is_template ? <span className="badge badge-mid">Mẫu</span> : null}
                  <Link
                    href={planAccountEditPath(detail.id)}
                    className="ml-auto rounded-xl bg-brand-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-brand-600"
                  >
                    Chỉnh sửa
                  </Link>
                  {!detail.is_template && (
                    <button
                      type="button"
                      onClick={() => {
                        void (async () => {
                          try {
                            await plansApi.saveAsTemplate(detail.id);
                            setErr("");
                            await load();
                          } catch (ex) {
                            setErr((ex as Error).message);
                          }
                        })();
                      }}
                      className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-bold hover:border-brand-400 hover:text-brand-600"
                    >
                      Lưu làm mẫu lịch
                    </button>
                  )}
                  {detail.ai_generation_id && detail.source === "ai" && (
                    <button
                      type="button"
                      disabled={restoring}
                      onClick={() => {
                        void (async () => {
                          const ok = window.confirm(
                            "Khôi phục sẽ xóa mọi chỉnh sửa bài tập và thực đơn. Tiếp tục?",
                          );
                          if (!ok) return;
                          setRestoring(true);
                          try {
                            const next = await plansApi.restoreAi(detail.id);
                            setDetail(next);
                            setErr("");
                            await load();
                          } catch (ex) {
                            setErr((ex as Error).message);
                          } finally {
                            setRestoring(false);
                          }
                        })();
                      }}
                      className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-900 hover:bg-amber-100 disabled:opacity-50"
                    >
                      {restoring ? "Đang khôi phục…" : "Khôi phục bản TAPTOT gốc"}
                    </button>
                  )}
                </div>

                {detail.days.map((day) => {
                  const dayInsight =
                    detail.source === "ai" && detail.insights
                      ? dayInsightFor(detail.insights, day.day_number)
                      : undefined;
                  const showDayKnowledge = detail.source === "ai" && showKnowledge && !!detail.insights;

                  return (
                  <div key={day.id} className="rounded-xl bg-slate-50 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold">{day.title_vi || `Ngày ${day.day_number}`}</h3>
                      {splitRoleLabel(day.split_role) && (
                        <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-500 ring-1 ring-slate-200">
                          {splitRoleLabel(day.split_role)}
                        </span>
                      )}
                    </div>

                    {PLAN_SECTION_ORDER.map((sec) => {
                      const items = day.exercises.filter((e) => e.section === sec);
                      if (!items.length) return null;
                      return (
                        <div key={sec} className="mt-3">
                          <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-slate-500">
                            {SECTION_LABEL[sec]}
                          </p>
                          <ul className="space-y-1.5">
                            {items.map((ex) => {
                              const why = showDayKnowledge
                                ? exerciseWhyFor(dayInsight, ex.exercise_id) || ex.notes_vi
                                : undefined;
                              return (
                              <li
                                key={ex.id}
                                className="rounded-lg bg-white px-3 py-2 text-sm"
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <span className="min-w-0">
                                    <span className="block font-medium leading-snug [overflow-wrap:anywhere]">{ex.name_vi}</span>
                                    {ex.name_en && ex.name_en !== ex.name_vi && (
                                      <span className="block truncate text-xs text-slate-400">
                                        {ex.name_en}
                                      </span>
                                    )}
                                    <span className="mt-1 inline-block rounded-lg bg-brand-50 px-2 py-0.5 text-xs font-bold text-brand-700">
                                      {formatSetsReps(ex.sets, ex.reps)}
                                    </span>
                                  </span>
                                </div>
                                {why && (
                                  <p className="mt-1 text-xs leading-snug text-sky-800/90">{why}</p>
                                )}
                              </li>
                              );
                            })}
                          </ul>
                        </div>
                      );
                    })}

                    {day.meals.length > 0 && (
                      <div className="mt-3">
                        <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-slate-500">
                          Thực đơn
                        </p>
                        <MealAccordionList
                          meals={day.meals}
                          showWhy={showDayKnowledge}
                          dayInsight={dayInsight}
                        />
                      </div>
                    )}
                  </div>
                  );
                })}

                <div className="rounded-xl border border-slate-100 bg-white p-3">
                  <p className="mb-2 text-sm font-semibold text-slate-600">Gửi lịch cho bạn / HLV</p>
                  {detail.share_token ? (
                    <div className="space-y-2">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                        <Link
                          href={`/lich/${detail.share_token}`}
                          className="min-w-0 flex-1 truncate text-sm font-medium text-brand-600 hover:underline"
                        >
                          {typeof window !== "undefined"
                            ? `${window.location.origin}/lich/${detail.share_token}`
                            : `/lich/${detail.share_token}`}
                        </Link>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            const url = planShareUrl(detail.share_token!);
                            const msg = buildShareMessage(detail, url);
                            void copyText(msg);
                          }}
                          className="rounded-xl bg-brand-500 px-3 py-2 text-sm font-bold text-white hover:bg-brand-600"
                        >
                          Sao chép tin nhắn
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            const url = planShareUrl(detail.share_token!);
                            const msg = buildShareMessage(detail, url);
                            void sharePlanNative({
                              title: detail.title_vi,
                              text: msg,
                              url,
                            });
                          }}
                          className="rounded-xl border border-brand-200 bg-brand-50 px-3 py-2 text-sm font-bold text-brand-700"
                        >
                          Gửi…
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            const url = planShareUrl(detail.share_token!);
                            void copyText(url);
                          }}
                          className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold hover:border-brand-400 hover:text-brand-600"
                        >
                          Sao chép link
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">Chưa có link công khai.</p>
                  )}
                </div>

                <div className="rounded-xl border border-slate-100 bg-white p-3">
                  <p className="mb-2 text-sm font-semibold text-slate-600">Xuất file</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setExportFormat("xlsx")}
                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold hover:border-brand-400 hover:text-brand-600"
                    >
                      Excel
                    </button>
                    <button
                      type="button"
                      onClick={() => setExportFormat("word")}
                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold hover:border-brand-400 hover:text-brand-600"
                    >
                      Word
                    </button>
                    <button
                      type="button"
                      onClick={() => setExportFormat("pdf")}
                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold hover:border-brand-400 hover:text-brand-600"
                    >
                      PDF
                    </button>
                  </div>
                </div>

                <ExportCustomizeModal
                  open={!!exportFormat}
                  format={exportFormat}
                  defaultStartDate={detail.start_date}
                  onClose={() => setExportFormat(null)}
                  onExport={runExport}
                />

                <button
                  type="button"
                  onClick={() => void doDelete()}
                  className="w-full rounded-xl border border-rose-200 py-2.5 text-sm font-semibold text-rose-600 transition hover:bg-rose-50"
                >
                  Xóa lịch tập này
                </button>
              </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
