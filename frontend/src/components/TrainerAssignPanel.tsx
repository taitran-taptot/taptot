"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getStoredUser } from "@/lib/auth";
import { plansApi, trainerApi, type PlanSummary } from "@/lib/plansApi";
import { trainerClientsApi, type TrainerClient } from "@/lib/phase3Api";

export default function TrainerAssignPanel() {
  const user = getStoredUser();
  const isTrainer = user?.role === "trainer" || user?.role === "admin";

  const [templates, setTemplates] = useState<PlanSummary[]>([]);
  const [clients, setClients] = useState<TrainerClient[]>([]);
  const [clientId, setClientId] = useState("");
  const [sourcePlanId, setSourcePlanId] = useState<number | "">("");
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [adding, setAdding] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const [all, tpls, clientRows] = await Promise.all([
        plansApi.list(),
        plansApi.listTemplates(),
        trainerClientsApi.list(),
      ]);
      const options = tpls.length ? tpls : all;
      setTemplates(options);
      setClients(clientRows.filter((c) => c.status === "active"));
      setSourcePlanId((prev) => (prev === "" && options.length ? options[0].id : prev));
      setClientId((prev) => {
        if (prev) return prev;
        const first = clientRows.find((c) => c.status === "active");
        return first?.client_id || "";
      });
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isTrainer) void load();
    else setLoading(false);
  }, [isTrainer, load]);

  async function onAddClient(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    setErr("");
    setMsg("");
    try {
      const row = await trainerClientsApi.add(email.trim());
      setClients((prev) => [row, ...prev.filter((c) => c.client_id !== row.client_id)]);
      setClientId(row.client_id);
      setEmail("");
      setMsg(
        `Đã thêm khách hàng ${row.display_name || row.email || row.client_id}. Bổ sung thông tin ở Quản lý khách hàng nếu cần.`,
      );
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setAdding(false);
    }
  }

  async function onRemoveClient(id: string) {
    try {
      await trainerClientsApi.remove(id);
      setClients((prev) => prev.filter((c) => c.client_id !== id));
      if (clientId === id) setClientId("");
    } catch (ex) {
      setErr((ex as Error).message);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!clientId.trim() || !sourcePlanId) {
      setErr("Chọn khách hàng và lịch nguồn.");
      return;
    }
    setSubmitting(true);
    setErr("");
    setMsg("");
    try {
      const res = await trainerApi.assignPlan({
        client_id: clientId.trim(),
        source_plan_id: Number(sourcePlanId),
        title_vi: title.trim() || undefined,
        notes_vi: notes.trim() || undefined,
      });
      setMsg(
        `Đã giao lịch #${res.plan_id}. ${res.share_url_path ? `Link: ${res.share_url_path}` : ""}`,
      );
      await load();
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!user) {
    return (
      <section className="mx-auto max-w-lg px-4 py-10 text-center">
        <h1 className="text-xl font-extrabold">Khu vực HLV</h1>
        <p className="mt-2 text-sm text-slate-500">Vui lòng đăng nhập bằng tài khoản huấn luyện viên.</p>
        <Link href="/dang-nhap" className="mt-4 inline-block font-semibold text-brand-600">
          Đăng nhập
        </Link>
      </section>
    );
  }

  if (!isTrainer) {
    return (
      <section className="mx-auto max-w-lg px-4 py-10 text-center">
        <h1 className="text-xl font-extrabold">Khu vực HLV</h1>
        <p className="mt-2 text-sm text-slate-500">
          Tài khoản không có quyền trainer.{" "}
          <Link href="/lien-he" className="font-semibold text-brand-600">
            Tìm HLV
          </Link>
        </p>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-2xl space-y-5 px-4 py-8">
      <div>
        <h1 className="text-xl font-extrabold tracking-tight sm:text-2xl">HLV — Giao lịch khách hàng</h1>
        <p className="mt-1 text-sm text-slate-500">
          Thêm khách hàng bằng email và giao lịch/mẫu tập. Thông tin chi tiết nhập ở{" "}
          <Link href="/hlv/hoc-vien" className="font-semibold text-brand-600">
            Quản lý khách hàng
          </Link>
          .
        </p>
      </div>

      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
      {msg && <p className="rounded-xl bg-brand-50 px-3 py-2 text-sm text-brand-700">{msg}</p>}

      {loading ? (
        <p className="text-sm text-slate-400">Đang tải…</p>
      ) : (
        <>
          <form onSubmit={(e) => void onAddClient(e)} className="rounded-2xl bg-white p-5 shadow-soft">
            <p className="mb-3 text-sm font-semibold text-slate-700">Thêm khách hàng</p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                className="field flex-1"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email khách hàng đã đăng ký"
                required
              />
              <button
                type="submit"
                disabled={adding}
                className="rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50"
              >
                {adding ? "Đang thêm…" : "Thêm"}
              </button>
            </div>
          </form>

          <div className="rounded-2xl bg-white p-5 shadow-soft">
            <p className="mb-3 text-sm font-semibold text-slate-700">Danh sách khách hàng</p>
            {!clients.length ? (
              <p className="text-sm text-slate-400">Chưa có khách hàng active.</p>
            ) : (
              <ul className="space-y-2">
                {clients.map((c) => (
                  <li
                    key={c.client_id}
                    className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
                      clientId === c.client_id ? "bg-brand-50 ring-1 ring-brand-200" : "bg-slate-50"
                    }`}
                  >
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => setClientId(c.client_id)}
                    >
                      <p className="truncate font-semibold">{c.full_name || c.display_name || "Khách hàng"}</p>
                      <p className="truncate text-xs text-slate-400">
                        {c.email} · {c.active_plans} lịch active
                      </p>
                    </button>
                    <button
                      type="button"
                      onClick={() => void onRemoveClient(c.client_id)}
                      className="text-xs font-semibold text-rose-500"
                    >
                      Gỡ
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <form onSubmit={(e) => void onSubmit(e)} className="space-y-4 rounded-2xl bg-white p-5 shadow-soft">
            <p className="text-sm font-semibold text-slate-700">Giao lịch</p>
            <label className="block space-y-1.5">
              <span className="text-sm font-semibold text-slate-600">Khách hàng</span>
              <select
                className="field"
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                required
              >
                <option value="">— Chọn —</option>
                {clients.map((c) => (
                  <option key={c.client_id} value={c.client_id}>
                    {c.full_name || c.display_name || c.email || c.client_id}
                  </option>
                ))}
              </select>
            </label>

            <label className="block space-y-1.5">
              <span className="text-sm font-semibold text-slate-600">Lịch / mẫu nguồn</span>
              <select
                className="field"
                value={sourcePlanId}
                onChange={(e) => setSourcePlanId(Number(e.target.value))}
                required
              >
                {templates.map((p) => (
                  <option key={p.id} value={p.id}>
                    #{p.id} {p.title_vi}
                    {p.is_template ? " (mẫu)" : ""} — {p.day_count} ngày
                  </option>
                ))}
              </select>
            </label>

            <label className="block space-y-1.5">
              <span className="text-sm font-semibold text-slate-600">Tiêu đề (tuỳ chọn)</span>
              <input className="field" value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>

            <label className="block space-y-1.5">
              <span className="text-sm font-semibold text-slate-600">Ghi chú HLV</span>
              <textarea
                className="field min-h-[80px]"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </label>

            <button
              type="submit"
              disabled={submitting || !templates.length || !clients.length}
              className="w-full rounded-xl bg-brand-500 py-3 text-sm font-bold text-white shadow-soft hover:bg-brand-600 disabled:opacity-50"
            >
              {submitting ? "Đang giao…" : "Giao lịch"}
            </button>
          </form>
        </>
      )}

      <p className="text-center text-xs text-slate-400">
        <Link href="/hlv/hoc-vien" className="font-semibold text-brand-600">
          Quản lý khách hàng →
        </Link>
      </p>
    </section>
  );
}
