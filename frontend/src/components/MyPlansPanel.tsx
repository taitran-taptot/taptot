"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import Modal from "./Modal";
import {
  plansApi,
  type PlanQuota,
  type PlanSummary,
  type PlanClientProfile,
} from "@/lib/plansApi";
import { claimGuestPlansAfterAuth } from "@/lib/authApi";
import { planAccountEditPath } from "@/lib/planEdit";
import { durationOverMax, durationToDays, type PlanDurationUnit } from "@/lib/planDuration";
import { sanitizeShareSlugInput, shareSlugError } from "@/lib/shareSlug";

const PLAN_PAGE_SIZE = 10;

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

function monthKeyFromIso(iso: string): string | null {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function formatMonthLabel(key: string): string {
  const [y, m] = key.split("-");
  if (!y || !m) return key;
  return `${m}/${y}`;
}

function clientTitleTaken(plans: PlanSummary[], title: string, excludeId?: number): boolean {
  const normalized = title.trim().toLocaleLowerCase("vi");
  if (!normalized) return false;
  return plans.some(
    (p) =>
      p.id !== excludeId &&
      !p.is_template &&
      (p.title_vi || "").trim().toLocaleLowerCase("vi") === normalized,
  );
}

export default function MyPlansPanel() {
  const router = useRouter();
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [templates, setTemplates] = useState<PlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [quota, setQuota] = useState<PlanQuota | null>(null);
  const [savedToast, setSavedToast] = useState(false);
  const [highlightId, setHighlightId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("Lịch tập");
  const [durationUnit, setDurationUnit] = useState<PlanDurationUnit>("week");
  const [durationCount, setDurationCount] = useState(1);
  const [newSlug, setNewSlug] = useState("");
  const [clientHeight, setClientHeight] = useState("");
  const [clientWeight, setClientWeight] = useState("");
  const [clientGender, setClientGender] = useState<PlanClientProfile["gender"]>(null);
  const [clientNotes, setClientNotes] = useState("");
  const [creating, setCreating] = useState(false);
  const [templateToUse, setTemplateToUse] = useState<PlanSummary | null>(null);
  const [copyTitle, setCopyTitle] = useState("");
  const [copySlug, setCopySlug] = useState("");
  const [copyClientHeight, setCopyClientHeight] = useState("");
  const [copyClientWeight, setCopyClientWeight] = useState("");
  const [copyClientGender, setCopyClientGender] =
    useState<PlanClientProfile["gender"]>(null);
  const [copyClientNotes, setCopyClientNotes] = useState("");
  const [copyingTemplate, setCopyingTemplate] = useState(false);
  const [monthFilter, setMonthFilter] = useState("");
  const [planSort, setPlanSort] = useState<"newest" | "oldest">("newest");
  const [planPage, setPlanPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      await claimGuestPlansAfterAuth();
      const [list, templateList, q] = await Promise.all([
        plansApi.list(),
        plansApi.listTemplates(),
        plansApi.quota(),
      ]);
      setPlans(list);
      setTemplates(templateList);
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

  const monthOptions = useMemo(() => {
    const keys = new Set<string>();
    for (const p of plans) {
      const key = monthKeyFromIso(p.created_at);
      if (key) keys.add(key);
    }
    return [...keys].sort((a, b) => b.localeCompare(a));
  }, [plans]);

  const filteredSortedPlans = useMemo(() => {
    let rows = plans;
    if (monthFilter) {
      rows = rows.filter((p) => monthKeyFromIso(p.created_at) === monthFilter);
    }
    const sorted = [...rows].sort((a, b) => {
      const ta = new Date(a.created_at).getTime();
      const tb = new Date(b.created_at).getTime();
      return planSort === "newest" ? tb - ta : ta - tb;
    });
    return sorted;
  }, [plans, monthFilter, planSort]);

  const planPageCount = Math.max(1, Math.ceil(filteredSortedPlans.length / PLAN_PAGE_SIZE));

  useEffect(() => {
    setPlanPage((prev) => Math.min(prev, planPageCount));
  }, [planPageCount]);

  const pagedPlans = useMemo(() => {
    const start = (planPage - 1) * PLAN_PAGE_SIZE;
    return filteredSortedPlans.slice(start, start + PLAN_PAGE_SIZE);
  }, [filteredSortedPlans, planPage]);

  async function doDelete(id: number, e?: React.MouseEvent) {
    e?.stopPropagation();
    if (!window.confirm("Xóa lịch tập này? Hành động không hoàn tác.")) return;
    try {
      await plansApi.remove(id);
      await load();
    } catch (ex) {
      setErr((ex as Error).message);
    }
  }

  async function createBlank(e: React.FormEvent) {
    e.preventDefault();
    const slugErr = shareSlugError(newSlug);
    if (slugErr) {
      setErr(slugErr);
      return;
    }
    const days = durationToDays(durationUnit, durationCount);
    if (days > 100) {
      setErr("Tối đa 100 ngày.");
      return;
    }
    const blankTitle = newTitle.trim() || "Lịch tập";
    if (clientTitleTaken(plans, blankTitle)) {
      setErr("Tên lịch khách đã được dùng. Hãy chọn tên khác.");
      return;
    }
    const client: PlanClientProfile = {
      height_cm: clientHeight === "" ? null : Number(clientHeight),
      weight_kg: clientWeight === "" ? null : Number(clientWeight),
      gender: clientGender || null,
      notes: clientNotes.trim() || null,
    };
    const hasClient = Boolean(client.height_cm || client.weight_kg || client.gender || client.notes);
    setCreating(true);
    setErr("");
    try {
      const created = await plansApi.create({
        title_vi: blankTitle,
        source: "manual",
        duration_weeks: 1,
        duration_unit: durationUnit,
        duration_count: durationCount,
        day_count: days,
        share_slug: newSlug.trim() || undefined,
        client: hasClient ? client : undefined,
        days: [],
      });
      setCreateOpen(false);
      router.push(planAccountEditPath(created.id));
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setCreating(false);
    }
  }

  function openUseTemplate(template: PlanSummary) {
    setTemplateToUse(template);
    setCopyTitle(template.title_vi.replace(/^Mẫu\s*[—-]\s*/i, "") || "Lịch tập");
    setCopySlug("");
    setCopyClientHeight("");
    setCopyClientWeight("");
    setCopyClientGender(null);
    setCopyClientNotes("");
    setErr("");
  }

  async function createFromTemplate(e: React.FormEvent) {
    e.preventDefault();
    if (!templateToUse) return;
    if (!copyTitle.trim()) {
      setErr("Vui lòng nhập tên lịch.");
      return;
    }
    if (clientTitleTaken(plans, copyTitle)) {
      setErr("Tên lịch khách đã được dùng. Hãy chọn tên khác.");
      return;
    }
    const slugErr = shareSlugError(copySlug);
    if (slugErr) {
      setErr(slugErr);
      return;
    }
    const client: PlanClientProfile = {
      height_cm: copyClientHeight === "" ? null : Number(copyClientHeight),
      weight_kg: copyClientWeight === "" ? null : Number(copyClientWeight),
      gender: copyClientGender || null,
      notes: copyClientNotes.trim() || null,
    };
    const hasClient = Boolean(client.height_cm || client.weight_kg || client.gender || client.notes);
    setCopyingTemplate(true);
    setErr("");
    try {
      const created = await plansApi.copyTemplate(templateToUse.id, {
        title_vi: copyTitle.trim(),
        share_slug: copySlug.trim() || undefined,
        client: hasClient ? client : undefined,
      });
      setTemplateToUse(null);
      router.push(planAccountEditPath(created.id));
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setCopyingTemplate(false);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="type-display">Lịch tập</h1>
        <p className="mt-1 text-sm text-slate-500">
          Tạo lịch trống, tùy chỉnh bài tập / bữa ăn, rồi copy link chia sẻ{" "}
          <span className="font-semibold">/lich/…</span>.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600"
          >
            Tạo lịch trống
          </button>
          <p className="text-xs font-medium text-slate-500">
            Đang có {quota?.used ?? plans.length} lịch
            {quota?.unlimited ? " (không giới hạn)." : "."}
          </p>
        </div>
      </div>

      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-bold text-slate-800">Template của tôi</h2>
          <p className="mt-1 text-sm text-slate-500">
            Lưu một lịch đã soạn thành mẫu, sau đó dùng lại cho từng khách.
          </p>
        </div>
        {loading ? (
          <p className="text-sm text-slate-400">Đang tải template…</p>
        ) : templates.length === 0 ? (
          <div className="rounded-2xl bg-white p-6 text-center shadow-soft">
            <p className="font-semibold text-slate-600">Chưa có template</p>
            <p className="mt-1 text-sm text-slate-400">
              Mở một lịch khách và chọn “Lưu thành template”.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {templates.map((template) => (
              <article key={template.id} className="rounded-2xl bg-white p-5 shadow-soft">
                <Link href={planAccountEditPath(template.id)} className="block">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="line-clamp-2 font-bold text-slate-800">{template.title_vi}</h3>
                    <span className="badge badge-easy shrink-0">Mẫu</span>
                  </div>
                  <p className="mt-3 text-xs font-semibold text-slate-500">
                    {template.day_count} ngày · {template.exercise_count} bài · {template.meal_count}{" "}
                    món
                  </p>
                </Link>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-[11px] text-slate-400">
                    Cập nhật {formatDate(template.updated_at)}
                  </p>
                  <div className="flex gap-1">
                    <Link
                      href={planAccountEditPath(template.id)}
                      className="rounded-lg px-2 py-1 text-[11px] font-bold text-slate-600 hover:bg-slate-50"
                    >
                      Chỉnh sửa
                    </Link>
                    <button
                      type="button"
                      onClick={() => openUseTemplate(template)}
                      className="rounded-lg bg-brand-500 px-2 py-1 text-[11px] font-bold text-white hover:bg-brand-600"
                    >
                      Dùng mẫu
                    </button>
                    <button
                      type="button"
                      onClick={(e) => void doDelete(template.id, e)}
                      className="rounded-lg px-2 py-1 text-[11px] font-bold text-rose-600 hover:bg-rose-50"
                    >
                      Xóa
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3 border-t border-slate-200 pt-5">
        <div>
          <h2 className="text-lg font-bold text-slate-800">Lịch khách</h2>
          <p className="mt-1 text-sm text-slate-500">Danh sách lịch đã tạo cho khách.</p>
        </div>

        {loading ? (
          <p className="text-sm text-slate-400">Đang tải lịch…</p>
        ) : plans.length === 0 ? (
          <div className="rounded-2xl bg-white p-8 text-center shadow-soft">
            <p className="font-semibold text-slate-600">Chưa có lịch nào</p>
            <p className="mt-1 text-sm text-slate-400">
              Tạo lịch trống rồi thêm bài tập và món ăn theo ý bạn.
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <button
                type="button"
                onClick={() => setCreateOpen(true)}
                className="rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
              >
                Tạo lịch trống
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <label className="text-xs font-semibold text-slate-500">
                Tháng
                <select
                  value={monthFilter}
                  onChange={(e) => {
                    setMonthFilter(e.target.value);
                    setPlanPage(1);
                  }}
                  className="field ml-2 inline-block w-auto min-w-[8rem] py-1.5 text-sm"
                  aria-label="Lọc theo tháng tạo"
                >
                  <option value="">Tất cả tháng</option>
                  {monthOptions.map((key) => (
                    <option key={key} value={key}>
                      {formatMonthLabel(key)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs font-semibold text-slate-500">
                Sắp xếp
                <select
                  value={planSort}
                  onChange={(e) => {
                    setPlanSort(e.target.value as "newest" | "oldest");
                    setPlanPage(1);
                  }}
                  className="field ml-2 inline-block w-auto min-w-[8rem] py-1.5 text-sm"
                  aria-label="Sắp xếp theo ngày tạo"
                >
                  <option value="newest">Mới nhất</option>
                  <option value="oldest">Cũ nhất</option>
                </select>
              </label>
            </div>

            {filteredSortedPlans.length === 0 ? (
              <div className="rounded-2xl bg-white p-6 text-center shadow-soft">
                <p className="font-semibold text-slate-600">Không có lịch trong tháng này.</p>
                <button
                  type="button"
                  onClick={() => {
                    setMonthFilter("");
                    setPlanPage(1);
                  }}
                  className="mt-3 text-sm font-bold text-brand-700 hover:underline"
                >
                  Xem tất cả tháng
                </button>
              </div>
            ) : (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  {pagedPlans.map((p) => (
                    <article
                      key={p.id}
                      className={`rounded-2xl bg-white p-4 text-left shadow-soft transition hover:ring-2 hover:ring-brand-200 ${
                        highlightId === p.id ? "ring-2 ring-brand-500" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <Link href={planAccountEditPath(p.id)} className="min-w-0 flex-1">
                          <h2 className="line-clamp-2 text-base font-bold text-slate-800">
                            {p.title_vi}
                          </h2>
                          <p className="mt-1 text-[11px] text-slate-400">
                            Tạo {formatDate(p.created_at)}
                          </p>
                        </Link>
                        <button
                          type="button"
                          onClick={(e) => void doDelete(p.id, e)}
                          className="shrink-0 rounded-lg px-2 py-1 text-[11px] font-bold text-rose-600 hover:bg-rose-50"
                        >
                          Xóa
                        </button>
                      </div>
                    </article>
                  ))}
                </div>

                {planPageCount > 1 ? (
                  <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
                    <button
                      type="button"
                      disabled={planPage <= 1}
                      onClick={() => setPlanPage((p) => Math.max(1, p - 1))}
                      className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-600 disabled:opacity-40"
                    >
                      Trước
                    </button>
                    <p className="text-xs font-semibold text-slate-500">
                      Trang {planPage} / {planPageCount}
                    </p>
                    <button
                      type="button"
                      disabled={planPage >= planPageCount}
                      onClick={() => setPlanPage((p) => Math.min(planPageCount, p + 1))}
                      className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-600 disabled:opacity-40"
                    >
                      Sau
                    </button>
                  </div>
                ) : null}
              </>
            )}
          </>
        )}
      </section>

      <Modal open={savedToast} onClose={() => setSavedToast(false)}>
        <div className="space-y-3 p-5 text-center">
          <p className="text-lg font-bold text-slate-800">Đã lưu lịch tập vừa tạo.</p>
          <p className="text-sm text-slate-500">
            Lịch nằm trong danh sách bên dưới. Mọi lịch vẫn hết hạn sau 110 ngày.
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

      <Modal
        open={templateToUse != null}
        onClose={() => setTemplateToUse(null)}
        size="lg"
        title="Dùng template"
      >
        <form onSubmit={(e) => void createFromTemplate(e)} className="space-y-3 p-5">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Tạo lịch từ template</h2>
            <p className="mt-1 text-sm text-slate-500">
              {templateToUse?.title_vi}. Bản mới độc lập và không làm thay đổi template.
            </p>
          </div>
          {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
          <label className="block text-sm font-semibold text-slate-600">
            Tên lịch
            <input
              required
              maxLength={255}
              value={copyTitle}
              onChange={(e) => setCopyTitle(e.target.value)}
              className="field mt-1"
            />
          </label>
          <label className="block text-sm font-semibold text-slate-600">
            Link /lich/
            <span className="mt-1 flex overflow-hidden rounded-xl ring-1 ring-slate-200">
              <span className="shrink-0 bg-slate-50 px-2 py-2 text-[11px] text-slate-400">
                …/lich/
              </span>
              <input
                value={copySlug}
                onChange={(e) => setCopySlug(sanitizeShareSlugInput(e.target.value))}
                className="min-w-0 flex-1 border-0 px-2 py-2 text-sm outline-none"
                placeholder="tuy-chon"
                spellCheck={false}
              />
            </span>
          </label>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-sm font-semibold text-slate-600">Hồ sơ khách (tùy chọn)</p>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <label className="text-xs font-semibold text-slate-500">
                Chiều cao (cm)
                <input
                  type="number"
                  min={50}
                  max={250}
                  value={copyClientHeight}
                  onChange={(e) => setCopyClientHeight(e.target.value)}
                  className="field mt-1"
                />
              </label>
              <label className="text-xs font-semibold text-slate-500">
                Cân nặng (kg)
                <input
                  type="number"
                  min={20}
                  max={400}
                  step={0.1}
                  value={copyClientWeight}
                  onChange={(e) => setCopyClientWeight(e.target.value)}
                  className="field mt-1"
                />
              </label>
              <label className="text-xs font-semibold text-slate-500">
                Giới tính
                <select
                  value={copyClientGender || ""}
                  onChange={(e) =>
                    setCopyClientGender(
                      (e.target.value || null) as PlanClientProfile["gender"],
                    )
                  }
                  className="field mt-1"
                >
                  <option value="">Không nêu</option>
                  <option value="male">Nam</option>
                  <option value="female">Nữ</option>
                </select>
              </label>
            </div>
            <label className="mt-2 block text-xs font-semibold text-slate-500">
              Ghi chú
              <textarea
                value={copyClientNotes}
                onChange={(e) => setCopyClientNotes(e.target.value)}
                rows={2}
                className="field mt-1"
              />
            </label>
          </div>
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={() => setTemplateToUse(null)}
              disabled={copyingTemplate}
              className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-600"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={copyingTemplate}
              className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white disabled:opacity-50"
            >
              {copyingTemplate ? "Đang tạo…" : "Tạo lịch từ mẫu"}
            </button>
          </div>
        </form>
      </Modal>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} size="lg">
        <form onSubmit={(e) => void createBlank(e)} className="max-h-[90vh] space-y-3 overflow-y-auto p-5">
          <h2 className="text-lg font-bold text-slate-800">Tạo lịch trống</h2>
          <p className="text-sm text-slate-500">
            Đặt thời lượng, slug và hồ sơ khách — rồi tùy chỉnh bài / món.
          </p>
          <label className="block text-sm font-semibold text-slate-600">
            Tên lịch
            <input
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="field mt-1"
            />
          </label>
          <div>
            <p className="text-sm font-semibold text-slate-600">Thời lượng</p>
            <div className="mt-1 flex gap-2">
              <input
                type="number"
                min={1}
                max={100}
                required
                value={durationCount}
                onChange={(e) => setDurationCount(Number(e.target.value))}
                className="field w-24"
              />
              <select
                value={durationUnit}
                onChange={(e) => setDurationUnit(e.target.value as PlanDurationUnit)}
                className="field flex-1"
              >
                <option value="day">Ngày</option>
                <option value="week">Tuần</option>
                <option value="month">Tháng</option>
              </select>
            </div>
            <p
              className={`mt-1 text-xs font-medium ${
                durationOverMax(durationUnit, durationCount) ? "text-rose-600" : "text-slate-400"
              }`}
            >
              = {durationToDays(durationUnit, durationCount)} ngày
              {durationOverMax(durationUnit, durationCount) ? " (tối đa 100)" : ""}
            </p>
          </div>
          <label className="block text-sm font-semibold text-slate-600">
            Link /lich/
            <span className="mt-1 flex overflow-hidden rounded-xl ring-1 ring-slate-200">
              <span className="shrink-0 bg-slate-50 px-2 py-2 text-[11px] text-slate-400">…/lich/</span>
              <input
                value={newSlug}
                onChange={(e) => setNewSlug(sanitizeShareSlugInput(e.target.value))}
                className="min-w-0 flex-1 border-0 px-2 py-2 text-sm outline-none"
                placeholder="tuy-chon"
                spellCheck={false}
              />
            </span>
            <span className="mt-1 block text-[11px] font-normal text-slate-400">
              Tùy chọn. Trùng lịch khác hoặc mã tem sẽ báo lỗi khi tạo.
            </span>
          </label>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-sm font-semibold text-slate-600">Hồ sơ khách (tùy chọn)</p>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <label className="text-xs font-semibold text-slate-500">
                Chiều cao (cm)
                <input
                  type="number"
                  min={50}
                  max={250}
                  value={clientHeight}
                  onChange={(e) => setClientHeight(e.target.value)}
                  className="field mt-1"
                />
              </label>
              <label className="text-xs font-semibold text-slate-500">
                Cân nặng (kg)
                <input
                  type="number"
                  min={20}
                  max={400}
                  step={0.1}
                  value={clientWeight}
                  onChange={(e) => setClientWeight(e.target.value)}
                  className="field mt-1"
                />
              </label>
              <label className="text-xs font-semibold text-slate-500">
                Giới tính
                <select
                  value={clientGender || ""}
                  onChange={(e) =>
                    setClientGender((e.target.value || null) as PlanClientProfile["gender"])
                  }
                  className="field mt-1"
                >
                  <option value="">Không nêu</option>
                  <option value="male">Nam</option>
                  <option value="female">Nữ</option>
                </select>
              </label>
            </div>
            <label className="mt-2 block text-xs font-semibold text-slate-500">
              Ghi chú
              <textarea
                value={clientNotes}
                onChange={(e) => setClientNotes(e.target.value)}
                rows={2}
                className="field mt-1"
              />
            </label>
          </div>
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={() => setCreateOpen(false)}
              className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-600"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={creating || durationOverMax(durationUnit, durationCount)}
              className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {creating ? "Đang tạo…" : "Tạo lịch"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
