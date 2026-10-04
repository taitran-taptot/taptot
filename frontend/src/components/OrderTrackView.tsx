"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { formatVnd } from "@/lib/labels";
import { shopApi } from "@/lib/shopApi";
import type { ShopOrder } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  awaiting_confirm: "Chờ xác nhận",
  packing: "Đang đóng gói",
  shipping: "Đang giao",
  completed: "Hoàn thành",
  cancelled: "Đã hủy",
  placed: "Chờ xác nhận",
};

const FLOW = ["awaiting_confirm", "packing", "shipping", "completed"] as const;
const PHONE_RE = /^0\d{9}$/;

function formatOrderDate(iso?: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("vi-VN");
}

function OrderDetail({ order }: { order: ShopOrder }) {
  const status = order.order_status || "";
  const stepIdx = FLOW.indexOf(status as (typeof FLOW)[number]);
  return (
    <div className="rounded-2xl bg-white p-5 shadow-soft ring-1 ring-slate-100">
      <p className="text-lg font-bold text-slate-900">{order.public_code}</p>
      <p className="mt-1 text-sm text-slate-500">
        {STATUS_LABEL[order.order_status] || order.order_status} · {formatVnd(order.total_vnd)}
        {order.created_at ? ` · ${formatOrderDate(order.created_at)}` : ""}
      </p>
      {order.order_status !== "cancelled" ? (
        <ol className="mt-5 space-y-2">
          {FLOW.map((s, i) => {
            const done = stepIdx >= 0 && i <= stepIdx;
            return (
              <li
                key={s}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                  done ? "bg-brand-50 font-semibold text-brand-800" : "text-slate-400"
                }`}
              >
                <span
                  className={`grid h-6 w-6 place-items-center rounded-full text-xs ${
                    done ? "bg-brand-600 text-white" : "bg-slate-100"
                  }`}
                >
                  {i + 1}
                </span>
                {STATUS_LABEL[s]}
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="mt-3 text-sm font-medium text-red-600">Đơn đã hủy</p>
      )}
      {order.items?.length ? (
        <ul className="mt-4 space-y-1 border-t border-slate-100 pt-3 text-sm text-slate-600">
          {order.items.map((it) => (
            <li key={it.id}>
              {it.name_vi} × {it.quantity}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function TrackInner() {
  const sp = useSearchParams();
  const [phone, setPhone] = useState(sp.get("phone") || "");
  const [code, setCode] = useState((sp.get("code") || "").toUpperCase());
  const [order, setOrder] = useState<ShopOrder | null>(null);
  const [orders, setOrders] = useState<ShopOrder[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(p = phone, c = code) {
    setError("");
    setOrder(null);
    setOrders([]);
    const phoneNorm = p.replace(/\D/g, "");
    if (!phoneNorm) {
      setError("Nhập số điện thoại.");
      return;
    }
    if (!PHONE_RE.test(phoneNorm)) {
      setError("Số điện thoại gồm 10 chữ số, bắt đầu bằng 0.");
      return;
    }
    const trimmedCode = c.trim().toUpperCase();
    setLoading(true);
    try {
      if (trimmedCode) {
        if (!trimmedCode.startsWith("TAPTOT-")) {
          setError("Mã đơn phải dạng TAPTOT-xxxxx.");
          return;
        }
        setOrder(await shopApi.trackOrder(phoneNorm, trimmedCode));
        return;
      }
      const listed = await shopApi.trackOrdersByPhone(phoneNorm);
      const items = listed.items || [];
      if (!items.length) {
        setError("Không tìm thấy đơn với số điện thoại này.");
        return;
      }
      setOrders(items);
    } catch (e) {
      const msg = (e as Error).message || "";
      setError(/not found/i.test(msg) ? "Không tìm thấy đơn với số điện thoại này." : msg || "Không tìm thấy đơn");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    window.scrollTo(0, 0);
    const p = sp.get("phone") || "";
    const c = (sp.get("code") || "").toUpperCase();
    if (p) void submit(p, c);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Tra cứu đơn hàng</h1>
        <p className="mt-1 text-sm text-slate-500">
          Nhập số điện thoại để xem các đơn đã đặt. Có mã đơn thì điền thêm để mở đúng đơn.
        </p>
      </div>
      <form
        className="space-y-3 rounded-2xl bg-white p-5 shadow-soft ring-1 ring-slate-100"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Số điện thoại</span>
          <input
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            value={phone}
            onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 10))}
            inputMode="numeric"
            maxLength={10}
            placeholder="0xxxxxxxxx"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Mã đơn hàng (tuỳ chọn)</span>
          <input
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 uppercase outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="TAPTOT-XXXXX"
          />
        </label>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
        >
          {loading ? "Đang tra…" : "Tra cứu"}
        </button>
      </form>

      {order ? (
        <div className="space-y-3">
          {orders.length ? (
            <button
              type="button"
              onClick={() => setOrder(null)}
              className="text-sm font-semibold text-brand-700 hover:underline"
            >
              Quay lại danh sách
            </button>
          ) : null}
          <OrderDetail order={order} />
        </div>
      ) : orders.length ? (
        <ul className="space-y-2">
          {orders.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => setOrder(item)}
                className="w-full rounded-2xl bg-white p-4 text-left shadow-soft ring-1 ring-slate-100 transition hover:ring-brand-200"
              >
                <p className="font-bold text-slate-900">{item.public_code}</p>
                <p className="mt-1 text-sm text-slate-500">
                  {STATUS_LABEL[item.order_status] || item.order_status} · {formatVnd(item.total_vnd)}
                  {item.created_at ? ` · ${formatOrderDate(item.created_at)}` : ""}
                </p>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default function OrderTrackView() {
  return (
    <Suspense fallback={<div className="h-40 animate-pulse rounded-2xl bg-white" />}>
      <TrackInner />
    </Suspense>
  );
}
