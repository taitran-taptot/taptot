"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getStoredUser } from "@/lib/auth";
import { formatVnd, mediaUrl } from "@/lib/labels";
import { equipmentImageFitClass } from "@/lib/equipmentCatalog";
import { shopApi } from "@/lib/shopApi";
import type { ShopCart } from "@/lib/types";
import TermsConsent, { termsAccepted } from "@/components/TermsConsent";

export default function ShopCart() {
  const router = useRouter();
  const [cart, setCart] = useState<ShopCart | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [doneId, setDoneId] = useState<number | null>(null);
  const [doneGiftCount, setDoneGiftCount] = useState(0);
  const [ageOk, setAgeOk] = useState(false);
  const [termsOk, setTermsOk] = useState(false);

  useEffect(() => {
    if (!getStoredUser()) {
      router.replace(`/dang-nhap?next=${encodeURIComponent("/gio-hang")}`);
      return;
    }
    shopApi
      .getCart()
      .then(setCart)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [router]);

  async function setQty(productId: number, quantity: number) {
    setError("");
    try {
      setCart(await shopApi.setCartQty(productId, quantity));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function placeOrder() {
    if (!termsAccepted(ageOk, termsOk)) return;
    setSaving(true);
    setError("");
    try {
      const order = await shopApi.checkout(note);
      setDoneGiftCount((cart?.items || []).reduce((sum, item) => sum + item.quantity, 0));
      setDoneId(order.id);
      setCart({ items: [], total_vnd: 0 });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="h-48 animate-pulse rounded-2xl bg-white shadow-soft" />;
  }

  if (doneId) {
    return (
      <div className="rounded-2xl bg-white p-8 text-center shadow-soft">
        <p className="text-lg font-bold text-emerald-700">Đã đặt đơn #{doneId}</p>
        <p className="mt-2 text-sm text-slate-500">
          Đơn của bạn đã được ghi nhận, gồm {doneGiftCount} mã lộ trình 100 ngày tặng kèm.
        </p>
        <div className="mx-auto mt-5 max-w-md rounded-2xl bg-brand-50 px-5 py-4 text-left ring-1 ring-brand-100">
          <p className="font-bold text-brand-900">Khi nhận hàng</p>
          <p className="mt-1 text-sm leading-relaxed text-brand-800/80">
            Tìm tem TAPTOT trên từng sản phẩm, quét mã QR rồi tạo lịch tập và lịch ăn phù hợp với bạn.
          </p>
        </div>
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <Link
            href="/tai-khoan/don-hang"
            className="rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
          >
            Xem đơn hàng
          </Link>
          <Link href="/mua-dung-cu" className="rounded-xl px-4 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50">
            Tiếp tục mua
          </Link>
        </div>
      </div>
    );
  }

  const items = cart?.items || [];
  const giftCount = items.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <section>
      <h1 className="type-display">Giỏ hàng</h1>
      {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}

      {items.length === 0 ? (
        <div className="mt-8 rounded-2xl bg-white p-8 text-center shadow-soft">
          <p className="text-slate-500">Giỏ hàng trống.</p>
          <Link href="/mua-dung-cu" className="mt-4 inline-block text-sm font-semibold text-brand-600">
            Mua dụng cụ →
          </Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_280px]">
          <div className="space-y-3">
            {items.map((it) => {
              const img = mediaUrl(it.image_url);
              return (
                <div key={it.product_id} className="flex gap-4 rounded-2xl bg-white p-4 shadow-soft">
                  <div className="h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-slate-100">
                    {img ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={img}
                        alt=""
                        className={`h-full w-full ${
                          (it.image_url || "").includes("gymnastic-rings")
                            ? equipmentImageFitClass("gymnastic-rings")
                            : "object-cover"
                        }`}
                      />
                    ) : (
                      <div className="grid h-full place-items-center text-2xl">🏋️</div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-bold">{it.name_vi}</p>
                    <p className="text-sm text-brand-700">{formatVnd(it.price_vnd)}</p>
                    <p className="mt-0.5 text-xs font-semibold text-emerald-700">
                      Kèm 1 mã lộ trình cho mỗi sản phẩm
                    </p>
                    <p className="text-xs text-slate-400">Kho: {it.stock_qty}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <input
                        type="number"
                        min={1}
                        max={it.stock_qty}
                        className="w-20 rounded-lg border border-slate-200 px-2 py-1 text-sm"
                        value={it.quantity}
                        onChange={(e) => void setQty(it.product_id, Number(e.target.value) || 1)}
                      />
                      <button
                        type="button"
                        className="text-sm font-semibold text-rose-600"
                        onClick={() => void setQty(it.product_id, 0)}
                      >
                        Xóa
                      </button>
                    </div>
                  </div>
                  <p className="shrink-0 font-bold">{formatVnd(it.line_total_vnd)}</p>
                </div>
              );
            })}
          </div>
          <aside className="h-fit rounded-2xl bg-white p-5 shadow-soft">
            <p className="text-sm text-slate-500">Tổng cộng</p>
            <p className="mt-1 text-2xl font-bold text-brand-700">{formatVnd(cart?.total_vnd || 0)}</p>
            <div className="mt-4 rounded-xl bg-brand-50 px-3.5 py-3 ring-1 ring-brand-100">
              <p className="text-sm font-bold text-brand-900">
                Tặng kèm {giftCount} mã lộ trình 100 ngày
              </p>
              <p className="mt-1 text-xs leading-relaxed text-brand-800/75">
                Mã được dán trên từng sản phẩm khi giao đến bạn.
              </p>
            </div>
            <label className="mt-4 block text-sm">
              Ghi chú
              <textarea
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                rows={3}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Ghi chú cho đơn hàng (không bắt buộc)"
              />
            </label>
            <div className="mt-4">
              <TermsConsent
                idPrefix="shop-checkout"
                ageOk={ageOk}
                termsOk={termsOk}
                onAgeOk={setAgeOk}
                onTermsOk={setTermsOk}
              />
            </div>
            <button
              type="button"
              disabled={saving || !termsAccepted(ageOk, termsOk)}
              onClick={() => void placeOrder()}
              className="mt-4 w-full rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {saving ? "Đang đặt…" : "Đặt hàng"}
            </button>
            <p className="mt-2 text-xs text-slate-400">Chưa thanh toán trực tuyến — đơn được lưu và trừ kho.</p>
          </aside>
        </div>
      )}
    </section>
  );
}
