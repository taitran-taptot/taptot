"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { formatVnd } from "@/lib/labels";
import { shopApi } from "@/lib/shopApi";
import type { ShopOrder } from "@/lib/types";

const STATUS: Record<string, { vi: string; cls: string }> = {
  placed: { vi: "Đã đặt", cls: "badge-easy" },
  cancelled: { vi: "Đã hủy", cls: "badge-gray" },
};

export default function MyShopOrders() {
  const [items, setItems] = useState<ShopOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    shopApi
      .myOrders()
      .then((d) => setItems(d.items || []))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section>
      <div className="mb-6 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Đơn hàng của tôi</h1>
          <p className="mt-1 text-sm text-slate-500">Dụng cụ đã đặt — chưa gồm thanh toán trực tuyến.</p>
        </div>
        <Link href="/mua-dung-cu" className="text-sm font-semibold text-brand-600">
          Mua thêm
        </Link>
      </div>
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {loading ? (
        <div className="h-40 animate-pulse rounded-2xl bg-white shadow-soft" />
      ) : items.length === 0 ? (
        <p className="py-12 text-center text-slate-400">Chưa có đơn hàng.</p>
      ) : (
        <div className="space-y-4">
          {items.map((o) => {
            const st = STATUS[o.order_status] || { vi: o.order_status, cls: "badge-gray" };
            const giftCount = (o.items || []).reduce((sum, item) => sum + item.quantity, 0);
            return (
              <div key={o.id} className="rounded-2xl bg-white p-5 shadow-soft">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-bold">Đơn #{o.id}</p>
                  <span className={`badge ${st.cls}`}>{st.vi}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {o.created_at ? new Date(o.created_at).toLocaleString("vi-VN") : ""}
                </p>
                <ul className="mt-3 space-y-1 text-sm">
                  {(o.items || []).map((it) => (
                    <li key={it.id} className="flex justify-between gap-3">
                      <span>
                        {it.name_vi} × {it.quantity}
                      </span>
                      <span className="font-medium">{formatVnd(it.line_total_vnd)}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-4 rounded-xl bg-brand-50 px-4 py-3 ring-1 ring-brand-100">
                  <p className="text-sm font-bold text-brand-900">
                    Đơn này có {giftCount} mã lộ trình 100 ngày tặng kèm
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-brand-800/75">
                    Mã nằm trên tem của từng sản phẩm. Khi nhận hàng, quét QR hoặc{" "}
                    <Link href="/qua-tang" className="font-bold underline underline-offset-2">
                      nhập mã tại đây
                    </Link>
                    .
                  </p>
                </div>
                <p className="mt-3 text-right font-extrabold text-brand-700">Tổng {formatVnd(o.total_vnd)}</p>
                {o.note && <p className="mt-2 text-sm text-slate-500">Ghi chú: {o.note}</p>}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
