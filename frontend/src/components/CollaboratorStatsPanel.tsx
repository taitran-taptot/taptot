"use client";

import { useEffect, useState } from "react";
import { collaboratorApi, type CollaboratorPeriodStats, type PromoOrder } from "@/lib/collaboratorApi";
import { formatVnd } from "@/lib/labels";

type Period = "day" | "month" | "year";

function vnParts(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const pick = (type: string) => parts.find((part) => part.type === type)?.value || "";
  return { year: pick("year"), month: pick("month"), day: pick("day") };
}

function defaultOn(period: Period) {
  const { year, month, day } = vnParts();
  if (period === "year") return year;
  if (period === "month") return `${year}-${month}`;
  return `${year}-${month}-${day}`;
}

export default function CollaboratorStatsPanel() {
  const [period, setPeriod] = useState<Period>("day");
  const [on, setOn] = useState(() => defaultOn("day"));
  const [page, setPage] = useState(1);
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<"asc" | "desc">("desc");
  const [status, setStatus] = useState("");
  const [stats, setStats] = useState<CollaboratorPeriodStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    collaboratorApi
      .stats(period, on, page, 10, query, sort, status)
      .then((data) => {
        if (cancelled) return;
        setStats(data);
        setError("");
        setLoading(false);
      })
      .catch((ex: unknown) => {
        if (cancelled) return;
        setStats(null);
        setError(ex instanceof Error ? ex.message : "Không tải được thống kê");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period, on, page, query, sort, status]);

  function choosePeriod(next: Period) {
    setPeriod(next);
    setOn(defaultOn(next));
    setPage(1);
    setLoading(true);
  }

  return (
    <div className="space-y-4">
      <section className="rounded-2xl bg-white p-5 shadow-soft">
        <h2 className="type-display">Thống kê</h2>
        <p className="mt-1 text-sm text-slate-500">
          Theo ngày, tháng hoặc năm, giờ Việt Nam. Tổng giá đơn và tổng đã giảm chỉ tính đơn hoàn thành.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {(
            [
              ["day", "Ngày"],
              ["month", "Tháng"],
              ["year", "Năm"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => choosePeriod(value)}
              className={`rounded-lg px-3 py-2 text-sm font-semibold ${
                period === value ? "bg-brand-500 text-white" : "border border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <label className="mt-4 block text-sm font-semibold text-slate-600">
          {period === "day" ? "Ngày" : period === "month" ? "Tháng" : "Năm"}
          <input
            type={period === "year" ? "number" : period === "month" ? "month" : "date"}
            min={period === "year" ? 2020 : undefined}
            max={period === "year" ? 2100 : undefined}
            value={on}
            onChange={(e) => {
              setOn(e.target.value);
              setPage(1);
              setLoading(true);
            }}
            className="field mt-1 max-w-xs"
          />
        </label>
        {error && <p className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>}
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Số đơn" value={loading || !stats ? "…" : String(stats.order_count)} hint={stats?.label} />
        <StatCard label="Tổng giá đơn" value={loading || !stats ? "…" : formatVnd(stats.total_vnd)} hint={stats?.label} />
        <StatCard label="Tổng đã giảm" value={loading || !stats ? "…" : formatVnd(stats.discount_vnd)} hint={stats?.label} />
      </section>

      <section className="rounded-2xl bg-white p-5 shadow-soft">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-base font-bold text-slate-900">Đơn trong kỳ</h2>
          <button
            type="button"
            onClick={() => {
              setSort((current) => (current === "desc" ? "asc" : "desc"));
              setPage(1);
              setLoading(true);
            }}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            {sort === "desc" ? "Ngày: mới nhất" : "Ngày: cũ nhất"}
          </button>
        </div>
        <form
          className="mt-3 flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(draft.trim());
            setPage(1);
            setLoading(true);
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value.toUpperCase())}
            placeholder="Tìm mã đơn"
            className="field min-w-0 flex-1 font-mono uppercase"
            aria-label="Tìm theo mã đơn"
          />
          <select
            value={status}
            aria-label="Lọc trạng thái đơn"
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
              setLoading(true);
            }}
            className="field w-auto"
          >
            <option value="">Mọi trạng thái</option>
            <option value="awaiting_confirm">Chờ xác nhận</option>
            <option value="packing">Đang đóng gói</option>
            <option value="shipping">Đang giao</option>
            <option value="completed">Hoàn thành</option>
            <option value="cancelled">Đã hủy</option>
          </select>
          <button
            type="submit"
            className="rounded-lg bg-brand-500 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-600"
          >
            Tìm
          </button>
        </form>
        {!stats?.orders.items.length ? (
          <p className="mt-3 text-sm text-slate-500">
            {query || status ? "Không có đơn khớp bộ lọc." : "Chưa có đơn."}
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100">
            {stats.orders.items.map((order, index) => (
              <OrderLine
                key={order.id}
                order={order}
                index={(stats.orders.page - 1) * stats.orders.page_size + index + 1}
              />
            ))}
          </ul>
        )}
        <Pager page={stats?.orders.page ?? page} pages={stats?.orders.pages ?? 1} onPage={setPage} />
      </section>
    </div>
  );
}

const STATUS: Record<string, string> = {
  awaiting_confirm: "Chờ xác nhận",
  packing: "Đang đóng gói",
  shipping: "Đang giao",
  completed: "Hoàn thành",
  cancelled: "Đã hủy",
  placed: "Chờ xác nhận",
};

function OrderLine({ order, index }: { order: PromoOrder; index: number }) {
  const when = order.created_at
    ? new Date(order.created_at).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })
    : "";
  return (
    <li className="flex items-center gap-3 py-2.5 text-sm">
      <p className="w-8 shrink-0 text-right font-semibold text-slate-400">{index}</p>
      <div className="min-w-0 flex-1">
        <p className="font-mono font-semibold text-slate-900">{order.public_code || `#${order.id}`}</p>
        <p className="text-xs text-slate-500">
          {STATUS[order.order_status] || order.order_status}
          {when ? ` · ${when}` : ""}
        </p>
      </div>
      <p className="shrink-0 font-semibold text-slate-800">{formatVnd(order.total_vnd)}</p>
    </li>
  );
}

function Pager({ page, pages, onPage }: { page: number; pages: number; onPage: (page: number) => void }) {
  if (pages <= 1) return null;
  return (
    <div className="mt-4 flex items-center justify-between gap-3 text-sm">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
        className="rounded-lg border border-slate-200 px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"
      >
        Trước
      </button>
      <p className="text-slate-500">
        Trang {page} / {pages}
      </p>
      <button
        type="button"
        disabled={page >= pages}
        onClick={() => onPage(page + 1)}
        className="rounded-lg border border-slate-200 px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"
      >
        Sau
      </button>
    </div>
  );
}

function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-soft">
      <p className="text-sm font-semibold text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-400">{hint}</p> : null}
    </div>
  );
}
