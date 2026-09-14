"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import { formatVnd } from "@/lib/labels";
import { shopApi } from "@/lib/shopApi";
import type { ShopOrder } from "@/lib/types";

const STATUS: Record<string, string> = {
  placed: "Đã đặt",
  cancelled: "Đã hủy",
};

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

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan");
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

  async function cancel(id: number) {
    if (!confirm("Hủy đơn này và hoàn kho?")) return;
    setBusyId(id);
    setError("");
    try {
      await shopApi.adminCancelOrder(id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  if (!allowed) return null;

  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight">Quản trị đơn hàng</h1>
      <p className="mt-1 text-sm text-slate-500">Hủy đơn đang chờ sẽ hoàn số lượng vào kho.</p>

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
          <option value="placed">Đã đặt</option>
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
                  Đơn #{o.id} · {STATUS[o.order_status] || o.order_status}
                </p>
                <p className="text-sm font-extrabold text-brand-700">{formatVnd(o.total_vnd)}</p>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                User {o.user_id} · {o.created_at ? new Date(o.created_at).toLocaleString("vi-VN") : ""}
              </p>
              <ul className="mt-3 space-y-1 text-sm">
                {(o.items || []).map((it) => (
                  <li key={it.id}>
                    {it.name_vi} × {it.quantity} — {formatVnd(it.line_total_vnd)}
                  </li>
                ))}
              </ul>
              {o.note && <p className="mt-2 text-sm text-slate-500">Ghi chú: {o.note}</p>}
              {o.order_status === "placed" && (
                <button
                  type="button"
                  disabled={busyId === o.id}
                  className="mt-3 rounded-lg bg-rose-50 px-3 py-1.5 text-sm font-semibold text-rose-700 disabled:opacity-50"
                  onClick={() => void cancel(o.id)}
                >
                  {busyId === o.id ? "Đang hủy…" : "Hủy đơn + hoàn kho"}
                </button>
              )}
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
