"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import {
  adminGetStats,
  adminSetMonthCosts,
  type AdminStatsResponse,
  type FinanceMonth,
  type FinanceProduct,
  type FinanceProductMonth,
} from "@/lib/adminStatsApi";
import { formatVnd } from "@/lib/labels";

const BAR_COLORS = ["#059669", "#0284c7", "#d97706"];

const ORDER_STATUS = [
  ["awaiting_confirm", "Chờ xác nhận"],
  ["packing", "Đang đóng gói"],
  ["shipping", "Đang giao"],
  ["completed", "Hoàn thành"],
  ["cancelled", "Đã hủy"],
  ["returned", "Khách trả hàng"],
] as const;

type MonthDraft = {
  operating: string;
  marketing: string;
  costs: Record<number, string>;
};

function yearOptions(selected: number): number[] {
  const now = new Date().getUTCFullYear();
  return [...new Set([now, now - 1, now - 2, selected])].sort((a, b) => b - a);
}

function digits(value: string): string {
  return value.replace(/[^\d]/g, "");
}

function money(value: string): number | null {
  const parsed = Number(value === "" ? "0" : value);
  if (!Number.isInteger(parsed) || parsed < 0) return null;
  return parsed;
}

function unitsOf(row: FinanceMonth, productId: number): number {
  return row.units_by_product.find((item) => item.product_id === productId)?.units ?? 0;
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

function GroupedBars({
  title,
  products,
  pick,
  format,
  showValues = false,
}: {
  title: string;
  products: FinanceProduct[];
  pick: (month: FinanceProductMonth) => number;
  format: (value: number) => string;
  showValues?: boolean;
}) {
  const series = products;
  const values = series.flatMap((product) => product.months.map((month) => pick(month)));
  const max = Math.max(1, ...values.map((value) => Math.abs(value)));
  const negative = values.some((value) => value < 0);
  const barW = showValues ? 16 : 12;
  const gap = showValues ? 8 : 2;
  const groupW = Math.max(showValues ? 78 : 52, series.length * (barW + gap) + 8);
  const height = 160;
  const top = showValues ? 16 : 0;
  const width = 8 + 12 * groupW;
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      {series.length === 0 ? (
        <p className="mt-3 text-sm text-slate-400">Chưa có sản phẩm.</p>
      ) : (
        <>
          <div className="mt-3 overflow-x-auto">
            <svg width={width} height={top + height + 22} role="img" aria-label={title}>
              {Array.from({ length: 12 }, (_, index) => {
                const month = index + 1;
                const x0 = 8 + index * groupW;
                const span = negative ? height / 2 : height;
                const zeroY = top + (negative ? height / 2 : height);
                return (
                  <g key={month}>
                    {negative ? <line x1={x0} x2={x0 + groupW - 4} y1={zeroY} y2={zeroY} stroke="#e2e8f0" /> : null}
                    {series.map((product, seriesIndex) => {
                      const point = product.months.find((row) => row.month === month);
                      const value = point ? pick(point) : 0;
                      const barH = Math.round((Math.abs(value) / max) * span);
                      const x = x0 + seriesIndex * (barW + gap);
                      const y = value >= 0 ? zeroY - barH : zeroY;
                      return (
                        <g key={product.id}>
                          {showValues && value > 0 ? (
                            <text
                              x={x + barW / 2}
                              y={y - 3}
                              textAnchor="middle"
                              fontSize={10}
                              fill="#334155"
                            >
                              {value}
                            </text>
                          ) : null}
                          <rect
                            x={x}
                            y={y}
                            width={barW}
                            height={barH}
                            rx={2}
                            fill={value < 0 ? "#e11d48" : BAR_COLORS[seriesIndex % BAR_COLORS.length]}
                          >
                            <title>{`${product.name_vi} · tháng ${month}: ${format(value)}`}</title>
                          </rect>
                        </g>
                      );
                    })}
                    <text x={x0 + 6} y={top + height + 16} fontSize={11} fill="#64748b">
                      {month}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
          <ul className="mt-2 flex flex-wrap gap-3 text-xs text-slate-600">
            {series.map((product, index) => (
              <li key={product.id} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-sm"
                  style={{ background: BAR_COLORS[index % BAR_COLORS.length] }}
                />
                {product.name_vi}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function ValueBars({
  title,
  points,
  format,
}: {
  title: string;
  points: { month: number; value: number }[];
  format: (value: number) => string;
}) {
  const max = Math.max(1, ...points.map((point) => Math.abs(point.value)));
  const negative = points.some((point) => point.value < 0);
  const height = 160;
  const top = 8;
  const groupW = 52;
  const width = 8 + 12 * groupW;
  const span = negative ? height / 2 : height;
  const zeroY = top + (negative ? height / 2 : height);
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      <div className="mt-3 overflow-x-auto">
        <svg width={width} height={top + height + 22} role="img" aria-label={title}>
          {Array.from({ length: 12 }, (_, index) => {
            const month = index + 1;
            const value = points.find((point) => point.month === month)?.value ?? 0;
            const barH = Math.round((Math.abs(value) / max) * span);
            const x = 16 + index * groupW;
            const y = value >= 0 ? zeroY - barH : zeroY;
            return (
              <g key={month}>
                {negative ? <line x1={x - 4} x2={x + 22} y1={zeroY} y2={zeroY} stroke="#e2e8f0" /> : null}
                <rect x={x} y={y} width={18} height={barH} rx={2} fill={value < 0 ? "#e11d48" : "#059669"}>
                  <title>{`Tháng ${month}: ${format(value)}`}</title>
                </rect>
                <text x={x + 2} y={top + height + 16} fontSize={11} fill="#64748b">
                  {month}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

export default function AdminStatsDashboard() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [year, setYear] = useState(() => new Date().getUTCFullYear());
  const [data, setData] = useState<AdminStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [drafts, setDrafts] = useState<Record<number, MonthDraft>>({});
  const [savingMonth, setSavingMonth] = useState<number | null>(null);
  const [month, setMonth] = useState(() => new Date().getMonth() + 1);

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

  useEffect(() => {
    const next: Record<number, MonthDraft> = {};
    for (const row of data?.finance?.months ?? []) {
      const costs: Record<number, string> = {};
      for (const item of row.costs.product_costs) {
        costs[item.product_id] = String(item.cost_vnd ?? 0);
      }
      next[row.month] = {
        operating: String(row.costs.operating_vnd ?? 0),
        marketing: String(row.costs.marketing_vnd ?? 0),
        costs,
      };
    }
    setDrafts(next);
  }, [data]);

  async function saveMonth(month: number) {
    const draft = drafts[month];
    if (!draft) return;
    const operating = money(draft.operating);
    const marketing = money(draft.marketing);
    const productCosts = (data?.finance?.products ?? []).map((product) => ({
      product_id: product.id,
      cost_vnd: money(draft.costs[product.id] ?? "0"),
    }));
    if (operating === null || marketing === null || productCosts.some((row) => row.cost_vnd === null)) {
      setError("Giá nhập, vận hành và marketing là số nguyên không âm.");
      return;
    }
    setSavingMonth(month);
    setError("");
    try {
      await adminSetMonthCosts({
        year,
        month,
        operating_vnd: operating,
        marketing_vnd: marketing,
        product_costs: productCosts.map((row) => ({
          product_id: row.product_id,
          cost_vnd: row.cost_vnd ?? 0,
        })),
      });
      await load(year);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingMonth(null);
    }
  }

  if (!allowed) return null;

  const life = data?.finance?.lifetime;
  const products = data?.finance?.products ?? [];
  const months = data?.finance?.months ?? [];
  const selectedMonth = months.find((item) => item.month === month);
  const draft = selectedMonth
    ? drafts[selectedMonth.month] ?? { operating: "0", marketing: "0", costs: {} }
    : null;
  const spend = (life?.operating_vnd ?? 0) + (life?.marketing_vnd ?? 0);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Thống kê shop</h1>
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

      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      {loading ? <p className="mt-6 text-sm text-slate-400">Đang tải…</p> : null}

      {!loading && life ? (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Doanh thu tổng" value={formatVnd(life.revenue_vnd)} hint="cả thời gian" />
            <Kpi label="Lãi ròng" value={formatVnd(life.profit_vnd)} hint="cả thời gian" />
            <Kpi
              label="Chi phí vận hành và marketing"
              value={formatVnd(spend)}
              hint={`Vận hành ${formatVnd(life.operating_vnd)} · Marketing ${formatVnd(life.marketing_vnd)}`}
            />
            <Kpi label="Tổng đơn đã bán" value={String(life.orders)} hint="cả thời gian" />
            <Kpi
              label="Đã thu"
              value={formatVnd(life.collected_vnd ?? 0)}
              hint="chuyển khoản đã nhận và COD đã giao"
            />
            <Kpi
              label="Chưa thu"
              value={formatVnd(life.uncollected_vnd ?? 0)}
              hint="đơn còn hiệu lực chưa nhận tiền"
            />
          </div>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">Trạng thái đơn</h2>
            <p className="mt-1 text-xs text-slate-400">
              Toàn bộ đơn hiện tại. Chỉ là số lượng, không cộng vào doanh thu hay lãi.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {ORDER_STATUS.map(([key, label]) => (
                <Kpi key={key} label={label} value={String(data?.finance?.order_status?.[key] ?? 0)} />
              ))}
            </div>
          </section>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">Doanh thu theo sản phẩm</h2>
            <p className="mt-1 text-xs text-slate-400">Số lượng bán và doanh thu sau giảm của từng sản phẩm, theo tháng {year}.</p>
            <div className="mt-5 grid gap-6 xl:grid-cols-2">
              <GroupedBars
                title="Số lượng bán"
                products={products}
                pick={(month) => month.units}
                format={String}
                showValues
              />
              <GroupedBars
                title="Doanh thu"
                products={products}
                pick={(month) => month.revenue_vnd}
                format={formatVnd}
              />
            </div>
            <div className="mt-6">
              <GroupedBars
                title="Lãi theo sản phẩm"
                products={products}
                pick={(month) => month.profit_vnd ?? 0}
                format={formatVnd}
              />
              <p className="mt-2 text-xs text-slate-400">
                Doanh thu trừ số lượng bán nhân giá nhập của tháng đó. Chưa trừ vận hành và marketing.
              </p>
            </div>
          </section>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="font-bold text-slate-800">Doanh thu theo tháng</h2>
              </div>
              <label className="text-sm text-slate-600">
                Tháng{" "}
                <select
                  className="ml-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  value={month}
                  aria-label="Chọn tháng"
                  onChange={(e) => setMonth(Number(e.target.value))}
                >
                  {Array.from({ length: 12 }, (_, index) => index + 1).map((value) => (
                    <option key={value} value={value}>
                      Tháng {value}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="mt-4">
              <ValueBars
                title="Lãi ròng theo tháng"
                points={months.map((row) => ({ month: row.month, value: row.profit_vnd }))}
                format={formatVnd}
              />
            </div>
            <div className="mt-4">
              {!selectedMonth || !draft ? (
                <p className="text-sm text-slate-400">Chưa có số liệu tháng {month}.</p>
              ) : (
                  <article className="rounded-xl border border-slate-100 p-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h3 className="font-semibold text-slate-800">Tháng {selectedMonth.month}</h3>
                      <p className="text-sm text-slate-600">
                        Doanh thu <span className="font-semibold tabular-nums">{formatVnd(selectedMonth.revenue_vnd)}</span>
                        <span className="mx-2 text-slate-300">·</span>
                        Lãi ròng <span className="font-semibold tabular-nums">{formatVnd(selectedMonth.profit_vnd)}</span>
                      </p>
                    </div>
                    <div className="mt-3 grid gap-3 lg:grid-cols-2">
                      {products.map((product) => (
                        <label key={product.id} className="text-xs text-slate-500">
                          {product.name_vi}
                          <span className="ml-1 text-slate-400">· đã bán {unitsOf(selectedMonth, product.id)}</span>
                          <input
                            inputMode="numeric"
                            aria-label={`Giá nhập ${product.name_vi} tháng ${selectedMonth.month}`}
                            className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm tabular-nums text-slate-800"
                            value={draft.costs[product.id] ?? "0"}
                            onChange={(e) => {
                              const value = digits(e.target.value);
                              setDrafts((prev) => {
                                const current = prev[selectedMonth.month] ?? draft;
                                return {
                                  ...prev,
                                  [selectedMonth.month]: {
                                    ...current,
                                    costs: { ...current.costs, [product.id]: value },
                                  },
                                };
                              });
                            }}
                          />
                        </label>
                      ))}
                      <label className="text-xs text-slate-500">
                        Chi phí vận hành
                        <input
                          inputMode="numeric"
                          aria-label={`Chi phí vận hành tháng ${selectedMonth.month}`}
                          className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm tabular-nums text-slate-800"
                          value={draft.operating}
                          onChange={(e) => {
                            const value = digits(e.target.value);
                            setDrafts((prev) => {
                              const current = prev[selectedMonth.month] ?? draft;
                              return { ...prev, [selectedMonth.month]: { ...current, operating: value } };
                            });
                          }}
                        />
                      </label>
                      <label className="text-xs text-slate-500">
                        Marketing
                        <input
                          inputMode="numeric"
                          aria-label={`Marketing tháng ${selectedMonth.month}`}
                          className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm tabular-nums text-slate-800"
                          value={draft.marketing}
                          onChange={(e) => {
                            const value = digits(e.target.value);
                            setDrafts((prev) => {
                              const current = prev[selectedMonth.month] ?? draft;
                              return { ...prev, [selectedMonth.month]: { ...current, marketing: value } };
                            });
                          }}
                        />
                      </label>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs text-slate-400">Giá vốn {formatVnd(selectedMonth.cogs_vnd)}</p>
                      <button
                        type="button"
                        disabled={savingMonth === selectedMonth.month}
                        className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                        onClick={() => void saveMonth(selectedMonth.month)}
                      >
                        {savingMonth === selectedMonth.month ? "Đang lưu…" : "Lưu"}
                      </button>
                    </div>
                  </article>
              )}
            </div>
          </section>

          <section className="mt-6 rounded-2xl bg-white p-5 shadow-soft">
            <h2 className="font-bold text-slate-800">Kho</h2>
            <p className="mt-1 text-xs text-slate-400">
              Cả đời shop. Còn lại là số đang nằm trong kho. Tổng = số sản phẩm đã bán + còn lại.
            </p>
            <div className="mt-4 grid grid-cols-3 gap-3">
              <Kpi label="Tổng" value={String(data?.inventory?.totals.total ?? 0)} />
              <Kpi label="Số sản phẩm đã bán" value={String(data?.inventory?.totals.sold ?? 0)} />
              <Kpi label="Còn lại" value={String(data?.inventory?.totals.remaining ?? 0)} />
            </div>
            {!data?.inventory?.products.length ? (
              <p className="mt-4 text-sm text-slate-400">Chưa có sản phẩm.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[28rem] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-xs text-slate-500">
                      <th className="py-2 pr-3 font-medium">Sản phẩm</th>
                      <th className="py-2 pr-3 text-right font-medium">Tổng</th>
                      <th className="py-2 pr-3 text-right font-medium">Số sản phẩm</th>
                      <th className="py-2 text-right font-medium">Còn lại</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.inventory.products.map((product) => (
                      <tr key={product.id} className="border-b border-slate-50">
                        <td className="py-2 pr-3 text-slate-800">{product.name_vi}</td>
                        <td className="py-2 pr-3 text-right tabular-nums">{product.total}</td>
                        <td className="py-2 pr-3 text-right tabular-nums">{product.sold}</td>
                        <td className="py-2 text-right tabular-nums">{product.remaining}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
