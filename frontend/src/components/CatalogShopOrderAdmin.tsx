"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import { formatVnd } from "@/lib/labels";
import { shopApi } from "@/lib/shopApi";
import type { ShopOrder } from "@/lib/types";

const STATUS: Record<string, string> = {
  awaiting_confirm: "Chờ xác nhận",
  packing: "Đang đóng gói",
  shipping: "Đang giao",
  completed: "Hoàn thành",
  cancelled: "Đã hủy",
  placed: "Chờ xác nhận",
};

const PAY: Record<string, string> = {
  cod: "COD",
  bank_transfer: "Chuyển khoản",
  unpaid: "Chưa thanh toán",
  awaiting_transfer: "Chờ CK",
  paid: "Đã nhận CK",
};

const CODE_STATUS: Record<string, string> = {
  unused: "Chưa dùng",
  processing: "Đang tạo lịch",
  redeemed: "Đã dùng",
  void: "Đã hủy",
};

const FLOW = ["awaiting_confirm", "packing", "shipping", "completed"];
const PAGE_SIZES = [10, 20, 50, 100] as const;

function statusTone(status: string) {
  if (status === "completed") return "bg-emerald-50 text-emerald-800";
  if (status === "cancelled") return "bg-rose-50 text-rose-700";
  if (status === "shipping") return "bg-sky-50 text-sky-800";
  if (status === "packing") return "bg-amber-50 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

function itemSummary(o: ShopOrder) {
  const items = o.items || [];
  if (items.length === 0) return "—";
  const first = `${items[0].name_vi} × ${items[0].quantity}`;
  if (items.length === 1) return first;
  return `${first} +${items.length - 1}`;
}

export default function CatalogShopOrderAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [items, setItems] = useState<ShopOrder[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [filter, setFilter] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [printBusy, setPrintBusy] = useState<number | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkStatus, setBulkStatus] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan/ke-hoach");
      return;
    }
    setAllowed(true);
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const d = await shopApi.adminListOrders({
        page,
        page_size: pageSize,
        order_status: filter || undefined,
        created_from: fromDate || undefined,
        created_to: toDate || undefined,
      });
      setItems(d.items || []);
      setPages(d.pages || 1);
      setTotal(d.total || 0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filter, fromDate, toDate]);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  async function setStatus(id: number, order_status: string) {
    setBusyId(id);
    setError("");
    try {
      await shopApi.adminUpdateOrderStatus(id, order_status);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  async function cancel(id: number) {
    if (!confirm("Hủy đơn này, hoàn kho, hủy mã quà tặng; nếu đã tạo lịch từ mã sẽ xóa lịch?")) return;
    await setStatus(id, "cancelled");
  }

  async function printCovers(o: ShopOrder) {
    setPrintBusy(o.id);
    setError("");
    try {
      await shopApi.adminDownloadActivationCovers(o.id, `bia-${o.public_code || o.id}.pdf`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPrintBusy(null);
    }
  }

  const pageIds = items.map((o) => o.id);
  const allPageSelected = pageIds.length > 0 && pageIds.every((id) => selected.has(id));

  function toggleSelected(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectPage() {
    setSelected((prev) => {
      const next = new Set(prev);
      if (allPageSelected) {
        for (const id of pageIds) next.delete(id);
      } else {
        for (const id of pageIds) next.add(id);
      }
      return next;
    });
  }

  async function printSelected() {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    setBulkBusy(true);
    setError("");
    try {
      await shopApi.adminDownloadBulkActivationCovers(ids, `bia-${ids.length}-don.pdf`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBulkBusy(false);
    }
  }

  async function applyBulkStatus() {
    const ids = Array.from(selected);
    if (ids.length === 0 || !bulkStatus) return;
    if (bulkStatus === "cancelled") {
      if (
        !confirm(
          `Hủy ${ids.length} đơn đã chọn, hoàn kho, hủy mã quà tặng; nếu đã tạo lịch từ mã sẽ xóa lịch?`,
        )
      ) {
        return;
      }
    }
    setBulkBusy(true);
    setError("");
    try {
      const d = await shopApi.adminBulkUpdateOrderStatus(ids, bulkStatus);
      const parts = [`Đã cập nhật ${d.updated_count} đơn`];
      if (d.skipped_count) parts.push(`bỏ qua ${d.skipped_count} (đã đúng trạng thái)`);
      if (d.error_count) {
        const first = d.errors[0];
        parts.push(`lỗi ${d.error_count}${first ? `: #${first.id} ${first.message}` : ""}`);
      }
      if (d.error_count) setError(parts.join(" · "));
      const done = new Set([...d.updated_ids, ...d.skipped_ids]);
      setSelected((prev) => new Set(Array.from(prev).filter((id) => !done.has(id))));
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBulkBusy(false);
    }
  }

  if (!allowed) return null;

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Quản trị đơn hàng</h1>
      <p className="mt-1 text-sm text-slate-500">
        Đổi trạng thái giao hàng, hủy đơn chờ. Mỗi món có một mã kích hoạt — in bìa QR để gửi cùng dụng cụ.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={filter}
          onChange={(e) => {
            setPage(1);
            setFilter(e.target.value);
          }}
        >
          <option value="">Tất cả</option>
          {FLOW.map((s) => (
            <option key={s} value={s}>
              {STATUS[s]}
            </option>
          ))}
          <option value="cancelled">Đã hủy</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-slate-600">
          Từ
          <input
            type="date"
            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
            value={fromDate}
            onChange={(e) => {
              setPage(1);
              setFromDate(e.target.value);
            }}
          />
        </label>
        <label className="flex items-center gap-1.5 text-sm text-slate-600">
          Đến
          <input
            type="date"
            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
            value={toDate}
            onChange={(e) => {
              setPage(1);
              setToDate(e.target.value);
            }}
          />
        </label>
        {fromDate || toDate ? (
          <button
            type="button"
            className="text-sm text-slate-500 underline"
            onClick={() => {
              setPage(1);
              setFromDate("");
              setToDate("");
            }}
          >
            Xóa ngày
          </button>
        ) : null}
        <select
          className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
          value={bulkStatus}
          disabled={selected.size === 0 || bulkBusy}
          onChange={(e) => setBulkStatus(e.target.value)}
        >
          <option value="">Đổi trạng thái…</option>
          {FLOW.map((s) => (
            <option key={s} value={s}>
              {STATUS[s]}
            </option>
          ))}
          <option value="cancelled">Đã hủy</option>
        </select>
        <button
          type="button"
          disabled={selected.size === 0 || !bulkStatus || bulkBusy}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 disabled:opacity-40"
          onClick={() => void applyBulkStatus()}
        >
          Áp dụng ({selected.size})
        </button>
        <button
          type="button"
          disabled={selected.size === 0 || bulkBusy}
          className="rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40"
          onClick={() => void printSelected()}
        >
          {bulkBusy ? "Đang xử lý…" : `In bìa đã chọn (${selected.size})`}
        </button>
        <label className="ml-auto flex items-center gap-2 text-sm text-slate-600">
          Hiển thị
          <select
            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
            value={pageSize}
            onChange={(e) => {
              setPage(1);
              setPageSize(Number(e.target.value));
            }}
          >
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          / trang
        </label>
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
        {loading ? (
          <p className="px-4 py-6 text-sm text-slate-400">Đang tải…</p>
        ) : items.length === 0 ? (
          <p className="px-4 py-6 text-slate-400">Chưa có đơn.</p>
        ) : (
          <ul>
            <li className="flex items-center gap-3 border-b border-slate-100 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
              <input
                type="checkbox"
                className="h-4 w-4"
                checked={allPageSelected}
                disabled={pageIds.length === 0}
                onChange={toggleSelectPage}
                aria-label="Chọn tất cả đơn trên trang"
              />
              <span>Chọn trang này ({pageIds.length})</span>
            </li>
            {items.map((o) => {
              const open = openId === o.id;
              return (
                <li key={o.id} className="border-b border-slate-100 last:border-b-0">
                  <div className="flex items-center gap-2 px-3 hover:bg-slate-50">
                    <input
                      type="checkbox"
                      className="h-4 w-4 shrink-0"
                      checked={selected.has(o.id)}
                      onChange={() => toggleSelected(o.id)}
                      aria-label={`Chọn đơn ${o.public_code || o.id}`}
                    />
                    <button
                      type="button"
                      className="flex min-w-0 flex-1 items-center gap-3 py-2 text-left"
                      onClick={() => setOpenId(open ? null : o.id)}
                      aria-expanded={open}
                    >
                    <span className="w-28 shrink-0 truncate text-sm font-semibold text-slate-800">
                      {o.public_code || `#${o.id}`}
                    </span>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusTone(o.order_status)}`}
                    >
                      {STATUS[o.order_status] || o.order_status}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-600">
                      {o.recipient_name || "—"} · {o.phone || "—"}
                    </span>
                    <span className="hidden min-w-0 max-w-[28%] truncate text-xs text-slate-400 sm:block">
                      {itemSummary(o)}
                    </span>
                    <span className="hidden shrink-0 text-xs text-slate-400 md:block">
                      {o.created_at ? new Date(o.created_at).toLocaleString("vi-VN") : ""}
                    </span>
                    <span className="w-24 shrink-0 text-right text-sm font-bold text-brand-700">
                      {formatVnd(o.total_vnd)}
                    </span>
                    <span className="w-4 shrink-0 text-center text-slate-400">{open ? "▾" : "▸"}</span>
                    </button>
                  </div>
                  {open ? (
                    <div className="border-t border-slate-100 bg-slate-50/70 px-4 py-3">
                      {o.discount_vnd ? (
                        <p className="text-xs text-slate-500">
                          Giảm thử thách {o.discount_percent}% · −{formatVnd(o.discount_vnd)}
                        </p>
                      ) : null}
                      {o.promo_code ? (
                        <p className="text-xs text-slate-500">
                          Giảm mã {o.promo_code} {o.promo_percent ?? 0}% · −{formatVnd(o.promo_discount_vnd || 0)}
                        </p>
                      ) : null}
                      <p className="text-xs text-slate-500">
                        {PAY[o.payment_method || ""] || o.payment_method} /{" "}
                        {PAY[o.payment_status || ""] || o.payment_status}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        {[o.address_line, o.ward_name, o.district_name, o.province_name]
                          .filter(Boolean)
                          .join(", ")}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        {o.user_id ? `User ${o.user_id}` : "Guest"} ·{" "}
                        {o.created_at ? new Date(o.created_at).toLocaleString("vi-VN") : ""}
                      </p>
                      <ul className="mt-2 space-y-1 text-sm">
                        {(o.items || []).map((it) => (
                          <li key={it.id}>
                            {it.name_vi} × {it.quantity} — {formatVnd(it.line_total_vnd)}
                          </li>
                        ))}
                      </ul>
                      {o.note && <p className="mt-2 text-sm text-slate-500">Ghi chú: {o.note}</p>}
                      {(o.gift_codes || []).length > 0 ? (
                        <div className="mt-3 rounded-xl bg-white px-3 py-2">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Mã kích hoạt ({o.gift_codes!.length})
                          </p>
                          <ul className="mt-1 space-y-0.5 font-mono text-sm">
                            {o.gift_codes!.map((c) => (
                              <li key={c.id}>
                                {c.code}{" "}
                                <span className="font-sans text-xs text-slate-500">
                                  · {CODE_STATUS[c.status] || c.status}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      <div className="mt-3 flex flex-wrap gap-2">
                        {o.order_status !== "cancelled" && o.order_status !== "completed" ? (
                          <select
                            className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
                            value={o.order_status}
                            disabled={busyId === o.id}
                            onChange={(e) => void setStatus(o.id, e.target.value)}
                          >
                            {FLOW.map((s) => (
                              <option key={s} value={s}>
                                {STATUS[s]}
                              </option>
                            ))}
                          </select>
                        ) : null}
                        {o.order_status === "awaiting_confirm" || o.order_status === "placed" ? (
                          <button
                            type="button"
                            disabled={busyId === o.id}
                            className="rounded-lg bg-rose-50 px-3 py-1.5 text-sm font-semibold text-rose-700 disabled:opacity-50"
                            onClick={() => void cancel(o.id)}
                          >
                            Hủy + hoàn kho
                          </button>
                        ) : null}
                        {(o.gift_codes || []).length > 0 ? (
                          <button
                            type="button"
                            disabled={printBusy === o.id}
                            className="rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
                            onClick={() => void printCovers(o)}
                          >
                            {printBusy === o.id ? "Đang tạo bìa…" : "In bìa"}
                          </button>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
        <p>
          {total ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} / ${total}` : "0 đơn"}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-3 py-1.5 disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Trước
          </button>
          <span className="self-center">
            {page}/{pages}
          </span>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-3 py-1.5 disabled:opacity-40"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Sau
          </button>
        </div>
      </div>
    </div>
  );
}
