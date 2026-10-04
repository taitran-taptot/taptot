"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { formatVnd } from "@/lib/labels";
import { shopApi } from "@/lib/shopApi";
import type { ShopOrder } from "@/lib/types";

function BankPayInner() {
  const sp = useSearchParams();
  const router = useRouter();
  const code = (sp.get("code") || "").toUpperCase();
  const phone = sp.get("phone") || "";
  const [order, setOrder] = useState<ShopOrder | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!code || !phone) {
      setError("Thiếu mã đơn hoặc số điện thoại");
      return;
    }
    shopApi
      .trackOrder(phone, code)
      .then(setOrder)
      .catch((e) => setError((e as Error).message));
  }, [code, phone]);

  const bank = order?.bank_transfer;

  return (
    <div className="mx-auto max-w-lg space-y-5 rounded-2xl bg-white p-6 shadow-soft sm:p-8">
      <h1 className="text-xl font-bold text-slate-900">Chuyển khoản đơn hàng</h1>
      <p className="text-sm text-slate-600">
        Mã đơn: <strong className="text-slate-900">{code}</strong>
      </p>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {bank ? (
        <>
          {bank.qr_image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={bank.qr_image_url}
              alt="QR chuyển khoản"
              className="mx-auto h-56 w-56 rounded-xl border border-slate-100 bg-white object-contain"
            />
          ) : (
            <p className="text-sm text-amber-700">QR chưa cấu hình STK — dùng thông tin bên dưới.</p>
          )}
          <dl className="space-y-2 rounded-xl bg-slate-50 p-4 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Ngân hàng</dt>
              <dd className="font-medium text-slate-900">{bank.bank_name || "—"}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Số tài khoản</dt>
              <dd className="font-medium text-slate-900">{bank.account_number || "—"}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Chủ tài khoản</dt>
              <dd className="font-medium text-slate-900">{bank.account_name || "—"}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Số tiền</dt>
              <dd className="font-bold text-slate-900">{formatVnd(bank.amount_vnd)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Nội dung CK</dt>
              <dd className="font-extrabold text-brand-800">{bank.transfer_content}</dd>
            </div>
          </dl>
          <p className="text-xs text-slate-500">
            Nội dung chuyển khoản phải đúng mã đơn để chúng tôi đối soát nhanh.
          </p>
        </>
      ) : !error ? (
        <p className="text-sm text-slate-400">Đang tải thông tin thanh toán…</p>
      ) : null}
      <button
        type="button"
        className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white"
        onClick={() =>
          router.push(
            `/don-hang/thanh-cong?code=${encodeURIComponent(code)}&phone=${encodeURIComponent(phone)}`,
          )
        }
      >
        Tôi đã chuyển khoản / Tiếp tục
      </button>
      <p className="text-center text-sm">
        <Link href="/tra-cuu-don" className="text-brand-700 underline">
          Tra cứu đơn hàng
        </Link>
      </p>
    </div>
  );
}

export default function BankTransferPayView() {
  return (
    <Suspense fallback={<div className="h-40 animate-pulse rounded-2xl bg-white" />}>
      <BankPayInner />
    </Suspense>
  );
}
