"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { formatVnd } from "@/lib/labels";
import { shopApi } from "@/lib/shopApi";
import type { ShopOrder } from "@/lib/types";

function OrderSuccessInner() {
  const sp = useSearchParams();
  const router = useRouter();
  const code = (sp.get("code") || "").toUpperCase();
  const phone = sp.get("phone") || "";
  const gifts = Number(sp.get("gifts") || 0);
  const [order, setOrder] = useState<ShopOrder | null>(null);
  const [checked, setChecked] = useState(!code || !phone);

  useEffect(() => {
    if (!code || !phone) return;
    let cancelled = false;
    shopApi
      .trackOrder(phone, code)
      .then((next) => {
        if (cancelled) return;
        if (next.payment_method === "bank_transfer" && next.payment_status !== "paid") {
          router.replace(
            `/don-hang/thanh-toan?code=${encodeURIComponent(code)}&phone=${encodeURIComponent(phone)}`,
          );
          return;
        }
        setOrder(next);
        setChecked(true);
      })
      .catch(() => {
        if (!cancelled) setChecked(true);
      });
    return () => {
      cancelled = true;
    };
  }, [code, phone, router]);

  if (!checked) {
    return <div className="mx-auto h-40 max-w-lg animate-pulse rounded-2xl bg-white shadow-soft" />;
  }

  const bankPaid = order?.payment_method === "bank_transfer" && order.payment_status === "paid";

  return (
    <div className="mx-auto max-w-lg rounded-2xl bg-white p-8 text-center shadow-soft">
      <p className="text-lg font-bold text-emerald-700">
        {bankPaid ? "Đã nhận chuyển khoản" : "Đặt hàng thành công"}
      </p>
      <p className="mt-4 text-sm text-slate-600">Mã đơn hàng của bạn</p>
      <p className="mt-1 text-3xl font-extrabold tracking-wide text-slate-900">{code || "—"}</p>
      <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900 ring-1 ring-amber-100">
        Vui lòng chụp ảnh màn hình hoặc lưu lại Mã đơn hàng này để tra cứu trạng thái giao hàng.
      </p>
      {order ? (
        <p className="mt-3 text-sm text-slate-500">
          Tổng thanh toán: <strong>{formatVnd(order.total_vnd)}</strong>
          {gifts > 0 ? ` · ${gifts} mã lộ trình 100 ngày tặng kèm` : null}
        </p>
      ) : null}
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link
          href={`/tra-cuu-don?code=${encodeURIComponent(code)}&phone=${encodeURIComponent(phone)}`}
          className="rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white"
        >
          Tra cứu đơn hàng
        </Link>
        <Link href="/mua-dung-cu" className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700">
          Tiếp tục mua
        </Link>
      </div>
    </div>
  );
}

export default function OrderSuccessView() {
  return (
    <Suspense fallback={<div className="h-40 animate-pulse rounded-2xl bg-white" />}>
      <OrderSuccessInner />
    </Suspense>
  );
}
