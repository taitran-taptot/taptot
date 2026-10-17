"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import { adminGetStats, type AdminStatsResponse, type ShopStatsBucket } from "@/lib/adminStatsApi";
import { formatVnd } from "@/lib/labels";

const ORDER_STATUS: Record<string, string> = {
  awaiting_confirm: "Chờ xác nhận",
  packing: "Đang đóng gói",
  shipping: "Đang giao",
  completed: "Hoàn thành",
  cancelled: "Đã hủy",
};

const PAY: Record<string, string> = {
  cod: "COD",
  bank_transfer: "Chuyển khoản",
};

function shortSku(name: string, slug: string): string {
  const text = (name || slug).trim();
  return text.length > 18 ? `${text.slice(0, 16)}…` : text;
}

function periodLabel(period: string, grain: "month" | "day"): string {
  if (grain === "month") {
    const n = Number(period.split("-")[1]);
    return Number.isFinite(n) ? `Thg ${n}` : period;
  }
  const day = period.split("-")[2];
  return day ? `${Number(day)}` : period;
}

function yearOptions(selected: number): number[] {
  const now = new Date().getUTCFullYear();
  return [...new Set([now, now - 1, now - 2, selected])].sort((a, b) => b - a);
}

function pct(n: number): string {
  return `${Math.round(n * 1000) / 10}%`;
}

function Bar({ value, max, className }: { value: number; max: number; className: string }) {
  const width = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
      <div className={`h-2 rounded-full ${className}`} style={{ width: `${width}%` }} />
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
  const [month, setMonth] = useState<number | 0>(0);
  const [data, setData] = useState<AdminStatsResponse | null>(null);
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

  const load = useCallback(async (y: number, m: number) => {
    setLoading(true);
    setError("");
    try {
      setData(await adminGetStats(y, m || null));
    } catch (e) {
      setError((e as Error).message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!allowed) return;
    void load(year, month);
  }, [allowed, year, month, load]);

  const shop = data?.shop;
  const series = shop?.series ?? [];
  const netMax = useMemo(
    () => series.reduce((acc, row) => Math.max(acc, row.net_vnd), 0),
    [series],
  );
  const grain = shop?.grain ?? "month";
  const skuColumns = shop?.products ?? [];

  if (!allowed) return null;

  const k = shop?.kpis;
  const open = data?.open_orders;
  const pushup = shop?.pushup;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Thống kê shop</h1>
          <p className="mt-1 text-sm text-slate-500">
            Đơn hàng, sản phẩm đang bán, giảm giá chống đẩy và tiền theo năm / tháng / ngày. Lợi nhuận ròng
            cần giá vốn — chưa có trong hệ thống.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
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
          <label className="text-sm text-slate-600">
            Tháng{" "}
            <select
              className="ml-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={month}
              onChange={(e) => setMonth(Number(e.target.value) as number | 0)}
            >
              <option value={0}>Cả năm</option>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {open && (open.awaiting_confirm > 0 || open.awaiting_transfer > 0) ? (
        <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Đang chờ: {open.awaiting_confirm} đơn xác nhận · {open.awaiting_transfer} chuyển khoản.
        </p>
      ) : null}

      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      {loading ? <p className="mt-6 text-sm text-slate-400">Đang tải…</p> : null}

      {!loading && k ? (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Đơn hiệu lực" value={String(k.orders)} hint={`${k.cancelled} hủy · ${pct(k.cancel_rate)}`} />
            <Kpi label="Số lượng bán" value={String(k.units)} />
            <Kpi label="Doanh thu hàng" value={formatVnd(k.gross_vnd)} hint="trước giảm" />
            <Kpi label="Giảm chống đẩy" value={formatVnd(k.discount_vnd)} hint={`${k.discount_orders} đơn`} />
            <Kpi label="Khách trả" value={formatVnd(k.net_vnd)} hint={`AOV ${formatVnd(k.aov_vnd)}`} />
            <Kpi label="Đã thu" value={formatVnd(k.collected_vnd)} hint="paid + COD" />
            <Kpi label="Phí ship" value={formatVnd(k.shipping_vnd)} />
            <Kpi
              label="Khách / mua lại"
              value={`${k.unique_customers} / ${k.repeat_customers}`}
              hint="cùng SĐT hoặc tài khoản"
            />
          </div>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">Sản phẩm</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="text-xs text-slate-500">
                  <tr>
                    <th className="pb-2 font-medium">Sản phẩm</th>
                    <th className="pb-2 font-medium">Đã bán</th>
                    <th className="pb-2 font-medium">Doanh thu dòng</th>
                    <th className="pb-2 font-medium">Số đơn</th>
                    <th className="pb-2 font-medium">Tồn kho</th>
                  </tr>
                </thead>
                <tbody>
                  {(shop?.products ?? []).map((p) => (
                    <tr key={p.slug} className="border-t border-slate-100">
                      <td className="py-2">
                        <p className="font-medium text-slate-800">{p.name_vi}</p>
                        <p className="text-xs text-slate-400">{p.slug}</p>
                      </td>
                      <td className="tabular-nums">{p.units}</td>
                      <td className="tabular-nums">{formatVnd(p.line_vnd)}</td>
                      <td className="tabular-nums">{p.order_count}</td>
                      <td className="tabular-nums">{p.stock_qty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">Giảm giá chống đẩy</h2>
            <p className="mt-1 text-xs text-slate-400">
              Chỉ đơn hiệu lực có tiền giảm / phần trăm từ ticket. Session camera hoàn thành trong kỳ.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Kpi label="Session xong" value={String(pushup?.sessions_completed ?? 0)} />
              <Kpi label="Đơn dùng giảm" value={String(pushup?.discount_orders ?? 0)} hint={pct(k.discount_order_rate)} />
              <Kpi label="Tiền giảm" value={formatVnd(pushup?.discount_vnd ?? 0)} />
              <div className="rounded-2xl bg-slate-50 p-4 text-sm">
                <p className="text-xs font-medium text-slate-500">Bậc %</p>
                <p className="mt-1 tabular-nums text-slate-700">
                  5% {pushup?.by_percent["5"] ?? 0} · 10% {pushup?.by_percent["10"] ?? 0} · 15%{" "}
                  {pushup?.by_percent["15"] ?? 0}
                  {(pushup?.by_percent.other ?? 0) > 0 ? ` · khác ${pushup?.by_percent.other}` : ""}
                </p>
              </div>
            </div>
          </section>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">{grain === "day" ? "Theo ngày" : "Theo tháng"}</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-xs text-slate-500">
                  <tr>
                    <th className="pb-2 font-medium">{grain === "day" ? "Ngày" : "Tháng"}</th>
                    <th className="pb-2 font-medium">Đơn</th>
                    <th className="pb-2 font-medium">Hủy</th>
                    <th className="pb-2 font-medium">SL</th>
                    <th className="pb-2 font-medium">Hàng</th>
                    <th className="pb-2 font-medium">Giảm</th>
                    <th className="pb-2 font-medium">Khách trả</th>
                    <th className="pb-2 font-medium">Đã thu</th>
                    {skuColumns.map((p) => (
                      <th key={p.slug} className="pb-2 font-medium">
                        {shortSku(p.name_vi, p.slug)}
                      </th>
                    ))}
                    <th className="w-28 pb-2 font-medium">Net</th>
                  </tr>
                </thead>
                <tbody>
                  {series.map((row: ShopStatsBucket) => (
                    <tr key={row.period} className="border-t border-slate-100">
                      <td className="py-2 text-slate-600">{periodLabel(row.period, grain)}</td>
                      <td className="tabular-nums">{row.orders}</td>
                      <td className="tabular-nums">{row.cancelled}</td>
                      <td className="tabular-nums">{row.units}</td>
                      <td className="tabular-nums">{formatVnd(row.gross_vnd)}</td>
                      <td className="tabular-nums">{formatVnd(row.discount_vnd)}</td>
                      <td className="tabular-nums">{formatVnd(row.net_vnd)}</td>
                      <td className="tabular-nums">{formatVnd(row.collected_vnd)}</td>
                      {skuColumns.map((p) => (
                        <td key={p.slug} className="tabular-nums">
                          {row.units_by_slug[p.slug] || 0}
                        </td>
                      ))}
                      <td className="py-2">
                        <Bar value={row.net_vnd} max={netMax} className="bg-emerald-500" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl bg-white p-5 shadow-soft">
              <h2 className="font-bold text-slate-800">Trạng thái đơn (kỳ này)</h2>
              <ul className="mt-3 space-y-1 text-sm">
                {Object.entries(shop?.funnel ?? {}).map(([status, n]) => (
                  <li key={status} className="flex justify-between">
                    <span className="text-slate-500">{ORDER_STATUS[status] || status}</span>
                    <span className="tabular-nums font-medium">{n}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl bg-white p-5 shadow-soft">
              <h2 className="font-bold text-slate-800">Thanh toán (đơn hiệu lực)</h2>
              <ul className="mt-3 space-y-1 text-sm">
                {Object.keys(shop?.payments ?? {}).length === 0 ? (
                  <li className="text-slate-400">Chưa có.</li>
                ) : (
                  Object.entries(shop?.payments ?? {}).map(([method, n]) => (
                    <li key={method} className="flex justify-between">
                      <span className="text-slate-500">{PAY[method] || method}</span>
                      <span className="tabular-nums font-medium">{n}</span>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
