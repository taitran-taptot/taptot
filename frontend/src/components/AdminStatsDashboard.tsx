"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import { adminGetStats, type AdminStatsMonth, type AdminStatsResponse } from "@/lib/adminStatsApi";
import { formatVnd } from "@/lib/labels";

const ORDER_STATUS: Record<string, string> = {
  awaiting_confirm: "Chờ xác nhận",
  packing: "Đang đóng gói",
  shipping: "Đang giao",
  completed: "Hoàn thành",
  cancelled: "Đã hủy",
};

function monthLabel(ym: string): string {
  const part = ym.split("-")[1];
  const n = Number(part);
  return Number.isFinite(n) ? `Thg ${n}` : ym;
}

function yearOptions(selected: number): number[] {
  const now = new Date().getUTCFullYear();
  const years = new Set([now, now - 1, now - 2, selected]);
  return [...years].sort((a, b) => b - a);
}

function maxOf(months: AdminStatsMonth[], pick: (m: AdminStatsMonth) => number): number {
  return months.reduce((acc, m) => Math.max(acc, pick(m)), 0);
}

function Bar({ value, max, className }: { value: number; max: number; className: string }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
      <div className={`h-2 rounded-full ${className}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-soft">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums text-slate-800">{value}</p>
      {hint ? <p className="mt-0.5 text-xs text-slate-400">{hint}</p> : null}
    </div>
  );
}

export default function AdminStatsDashboard() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [year, setYear] = useState(() => new Date().getUTCFullYear());
  const [data, setData] = useState<AdminStatsResponse | None>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan/ke-hoach");
      return;
    }
    setAllowed(true);
  }, [router]);

  const load = useCallback(async (y: number) => {
    setLoading(true);
    setError("");
    try {
      setData(await adminGetStats(y));
    } catch (e) {
      setError((e as Error).message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!allowed) return;
    void load(year);
  }, [allowed, year, load]);

  const months = data?.months ?? [];
  const planMax = useMemo(
    () => maxOf(months, (m) => m.plans.generated + m.plans.admin_created + m.plans.hlv_created),
    [months],
  );
  const gmvMax = useMemo(() => maxOf(months, (m) => m.orders.gmv_vnd), [months]);
  const userMax = useMemo(() => maxOf(months, (m) => m.users.new), [months]);

  if (!allowed) return null;

  const kpis = data?.kpis;
  const open = data?.open_orders;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Thống kê</h1>
          <p className="mt-1 text-sm text-slate-500">
            Lịch AI / admin / HLV, đơn hàng, user mới và thanh toán challenge theo tháng.
          </p>
        </div>
        <label className="text-sm text-slate-600">
          Năm{" "}
          <select
            className="ml-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {yearOptions(year).map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
      </div>

      {open && (open.awaiting_confirm > 0 || open.awaiting_transfer > 0) ? (
        <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Đang chờ: {open.awaiting_confirm} đơn xác nhận · {open.awaiting_transfer} chuyển khoản.
        </p>
      ) : null}

      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      {loading ? <p className="mt-6 text-sm text-slate-400">Đang tải…</p> : null}

      {!loading && kpis ? (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Lịch AI" value={String(kpis.plans_generated)} hint="source = gen" />
            <Kpi label="Lịch admin" value={String(kpis.plans_admin_created)} hint="manual / imported" />
            <Kpi label="Lịch HLV" value={String(kpis.plans_hlv_created)} hint="mọi lịch thuộc account HLV" />
            <Kpi label="Đơn (không hủy)" value={String(kpis.orders_count)} />
            <Kpi label="GMV" value={formatVnd(kpis.orders_gmv_vnd)} />
            <Kpi label="Đã thu" value={formatVnd(kpis.orders_collected_vnd)} hint="paid + COD" />
            <Kpi label="User mới" value={String(kpis.users_new)} />
            <Kpi
              label="Challenge đã trả"
              value={formatVnd(kpis.challenge_paid_vnd)}
              hint={`Tem dùng ${kpis.redeem_used} · còn ${kpis.redeem_unused}`}
            />
            <Kpi label="Push-up xong" value={String(kpis.pushup_completed)} hint="camera challenge" />
          </div>

          <section className="mt-8 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">Lịch tập theo tháng</h2>
            <p className="mt-1 text-xs text-slate-400">
              AI gen (mọi owner), lịch admin, lịch thuộc account HLV, template, thử thách 100 ngày, guest.
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="text-xs text-slate-500">
                  <tr>
                    <th className="pb-2 font-medium">Tháng</th>
                    <th className="pb-2 font-medium">AI</th>
                    <th className="pb-2 font-medium">Admin</th>
                    <th className="pb-2 font-medium">HLV</th>
                    <th className="pb-2 font-medium">Template</th>
                    <th className="pb-2 font-medium">100 ngày</th>
                    <th className="pb-2 font-medium">Guest</th>
                    <th className="w-40 pb-2 font-medium">Tỷ lệ</th>
                  </tr>
                </thead>
                <tbody>
                  {months.map((m) => (
                    <tr key={m.month} className="border-t border-slate-100">
                      <td className="py-2 text-slate-600">{monthLabel(m.month)}</td>
                      <td className="tabular-nums">{m.plans.generated}</td>
                      <td className="tabular-nums">{m.plans.admin_created}</td>
                      <td className="tabular-nums">{m.plans.hlv_created}</td>
                      <td className="tabular-nums">{m.plans.templates}</td>
                      <td className="tabular-nums">{m.plans.challenge_100}</td>
                      <td className="tabular-nums">{m.plans.guest}</td>
                      <td className="py-2">
                        <Bar
                          value={m.plans.generated + m.plans.admin_created + m.plans.hlv_created}
                          max={planMax}
                          className="bg-brand-500"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">Lịch theo từng HLV</h2>
            <p className="mt-1 text-xs text-slate-400">
              Mọi lịch gắn với tài khoản HLV trong năm (AI, soạn tay, template, imported).
            </p>
            {(data?.hlv_accounts ?? []).length === 0 ? (
              <p className="mt-4 text-sm text-slate-400">Chưa có tài khoản HLV.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[560px] text-left text-sm">
                  <thead className="text-xs text-slate-500">
                    <tr>
                      <th className="pb-2 font-medium">HLV</th>
                      <th className="pb-2 font-medium">Tổng</th>
                      <th className="pb-2 font-medium">AI</th>
                      <th className="pb-2 font-medium">Soạn tay</th>
                      <th className="pb-2 font-medium">Template</th>
                      <th className="pb-2 font-medium">Imported</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data?.hlv_accounts ?? []).map((h) => (
                      <tr key={h.user_id} className="border-t border-slate-100">
                        <td className="py-2">
                          <p className="font-medium text-slate-800">{h.display_name || h.email || h.user_id}</p>
                          {h.email && h.display_name ? (
                            <p className="text-xs text-slate-400">{h.email}</p>
                          ) : null}
                        </td>
                        <td className="tabular-nums font-semibold">{h.total}</td>
                        <td className="tabular-nums">{h.generated}</td>
                        <td className="tabular-nums">{h.manual}</td>
                        <td className="tabular-nums">{h.template}</td>
                        <td className="tabular-nums">{h.imported}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">Đơn hàng</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="text-xs text-slate-500">
                  <tr>
                    <th className="pb-2 font-medium">Tháng</th>
                    <th className="pb-2 font-medium">Số đơn</th>
                    <th className="pb-2 font-medium">GMV</th>
                    <th className="pb-2 font-medium">Đã thu</th>
                    <th className="pb-2 font-medium">Trạng thái</th>
                    <th className="w-36 pb-2 font-medium">GMV</th>
                  </tr>
                </thead>
                <tbody>
                  {months.map((m) => (
                    <tr key={m.month} className="border-t border-slate-100 align-top">
                      <td className="py-2 text-slate-600">{monthLabel(m.month)}</td>
                      <td className="tabular-nums">{m.orders.count}</td>
                      <td className="tabular-nums">{formatVnd(m.orders.gmv_vnd)}</td>
                      <td className="tabular-nums">{formatVnd(m.orders.collected_vnd)}</td>
                      <td className="py-2 text-xs text-slate-500">
                        {Object.entries(m.orders.by_status)
                          .filter(([, n]) => n > 0)
                          .map(([k, n]) => `${ORDER_STATUS[k] || k} ${n}`)
                          .join(" · ") || "—"}
                      </td>
                      <td className="py-2">
                        <Bar value={m.orders.gmv_vnd} max={gmvMax} className="bg-emerald-500" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">User mới</h2>
            <div className="mt-4 space-y-2">
              {months.map((m) => (
                <div key={m.month} className="grid grid-cols-[3.5rem_1fr_auto] items-center gap-2 text-sm">
                  <span className="text-slate-500">{monthLabel(m.month)}</span>
                  <Bar value={m.users.new} max={userMax} className="bg-sky-500" />
                  <span className="tabular-nums text-slate-700">
                    {m.users.new}
                    {m.users.staff ? (
                      <span className="ml-1 text-xs text-slate-400">(+{m.users.staff} staff)</span>
                    ) : null}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">Challenge &amp; mã tem</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead className="text-xs text-slate-500">
                  <tr>
                    <th className="pb-2 font-medium">Tháng</th>
                    <th className="pb-2 font-medium">Challenge (lượt)</th>
                    <th className="pb-2 font-medium">Challenge (₫)</th>
                    <th className="pb-2 font-medium">Tem đã dùng</th>
                  </tr>
                </thead>
                <tbody>
                  {months.map((m) => (
                    <tr key={m.month} className="border-t border-slate-100">
                      <td className="py-2 text-slate-600">{monthLabel(m.month)}</td>
                      <td className="tabular-nums">{m.challenge.paid_count}</td>
                      <td className="tabular-nums">{formatVnd(m.challenge.paid_vnd)}</td>
                      <td className="tabular-nums">{m.redeem.used}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
