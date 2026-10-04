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

export default function CatalogShopOrderAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [items, setItems] = useState<ShopOrder[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [printBusy, setPrintBusy] = useState<number | null>(null);

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
      const d = await shopApi.adminListOrders({ page, order_status: filter || undefined });
      setItems(d.items || []);
      setPages(d.pages || 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

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

  if (!allowed) return null;

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Quản trị đơn hàng</h1>
      <p className="mt-1 text-sm text-slate-500">
        Đổi trạng thái giao hàng, hủy đơn chờ. Mỗi món có một mã kích hoạt — in bìa QR để gửi cùng dụng cụ.
      </p>

      <div className="mt-4 flex gap-2">
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
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <div className="mt-6 space-y-4">
        {loading ? (
          <p className="text-sm text-slate-400">Đang tải…</p>
        ) : items.length === 0 ? (
          <p className="text-slate-400">Chưa có đơn.</p>
        ) : (
          items.map((o) => (
            <div key={o.id} className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-bold">
                  {o.public_code || `Đơn #${o.id}`} · {STATUS[o.order_status] || o.order_status}
                </p>
                <p className="text-sm font-bold text-brand-700">{formatVnd(o.total_vnd)}</p>
              </div>
              {o.discount_vnd ? (
                <p className="mt-1 text-xs text-slate-500">
                  Giảm {o.discount_percent}% · −{formatVnd(o.discount_vnd)}
                </p>
              ) : null}
              <p className="mt-1 text-xs text-slate-500">
                {o.recipient_name || "—"} · {o.phone || "—"} ·{" "}
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
              <ul className="mt-3 space-y-1 text-sm">
                {(o.items || []).map((it) => (
                  <li key={it.id}>
                    {it.name_vi} × {it.quantity} — {formatVnd(it.line_total_vnd)}
                  </li>
                ))}
              </ul>
              {o.note && <p className="mt-2 text-sm text-slate-500">Ghi chú: {o.note}</p>}
              {(o.gift_codes || []).length > 0 ? (
                <div className="mt-3 rounded-xl bg-slate-50 px-3 py-2">
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
                    className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
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
          ))
        )}
      </div>
      <div className="mt-4 flex justify-end gap-2 text-sm">
        <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          Trước
        </button>
        <button type="button" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
          Sau
        </button>
      </div>
    </div>
  );
}
