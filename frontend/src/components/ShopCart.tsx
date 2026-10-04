"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { getStoredUser } from "@/lib/auth";
import { formatVnd, mediaUrl } from "@/lib/labels";
import { equipmentImageFitClass } from "@/lib/equipmentCatalog";
import {
  CART_CHANGED_EVENT,
  clearGuestCart,
  getGuestCart,
  setGuestCartQty,
} from "@/lib/guestCart";
import { shopApi } from "@/lib/shopApi";
import type { ShopCart, ShopCartItem, ShopCheckoutPayload } from "@/lib/types";
import {
  clearPushupDiscount,
  loadPushupDiscount,
  type PushupDiscount,
} from "@/lib/fitness-tracker/session/discount";
import TermsConsent, { termsAccepted } from "@/components/TermsConsent";
import { fetchDistricts, fetchProvinces, fetchWards, type AdminUnit } from "@/lib/vnAdminUnits";

const PHONE_RE = /^0\d{9}$/;
const FIELD =
  "mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50";

type FormState = {
  recipient_name: string;
  phone: string;
  province_code: string;
  province_name: string;
  district_code: string;
  district_name: string;
  ward_code: string;
  ward_name: string;
  address_line: string;
  payment_method: "cod" | "bank_transfer";
  note: string;
};

const emptyForm: FormState = {
  recipient_name: "",
  phone: "",
  province_code: "",
  province_name: "",
  district_code: "",
  district_name: "",
  ward_code: "",
  ward_name: "",
  address_line: "",
  payment_method: "cod",
  note: "",
};

export default function ShopCart() {
  const router = useRouter();
  const [cart, setCart] = useState<ShopCart | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [ageOk, setAgeOk] = useState(false);
  const [termsOk, setTermsOk] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [provinces, setProvinces] = useState<AdminUnit[]>([]);
  const [districts, setDistricts] = useState<AdminUnit[]>([]);
  const [wards, setWards] = useState<AdminUnit[]>([]);
  const [discount, setDiscount] = useState<PushupDiscount | null>(null);

  const loggedIn = !!getStoredUser();

  async function loadCart() {
    setError("");
    try {
      if (getStoredUser()) {
        setCart(await shopApi.getCart());
      } else {
        const lines = getGuestCart();
        if (!lines.length) {
          setCart({ items: [], total_vnd: 0 });
          return;
        }
        const catalog = await shopApi.listProducts(1, 100);
        const byId = new Map((catalog.items || []).map((p) => [p.id, p]));
        const items: ShopCartItem[] = [];
        let total = 0;
        for (const line of lines) {
          const p = byId.get(line.product_id);
          if (!p || !p.is_active) continue;
          const qty = Math.min(line.quantity, Math.max(p.stock_qty, 0));
          if (qty < 1) continue;
          const lineTotal = p.price_vnd * qty;
          total += lineTotal;
          items.push({
            product_id: p.id,
            name_vi: p.name_vi,
            price_vnd: p.price_vnd,
            stock_qty: p.stock_qty,
            image_url: p.image_url,
            is_active: p.is_active,
            quantity: qty,
            line_total_vnd: lineTotal,
          });
        }
        setCart({ items, total_vnd: total });
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadCart();
    setDiscount(loadPushupDiscount());
    fetchProvinces()
      .then(setProvinces)
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (!form.province_code) {
      setDistricts([]);
      setWards([]);
      return;
    }
    fetchDistricts(form.province_code)
      .then(setDistricts)
      .catch((e) => setError((e as Error).message));
  }, [form.province_code]);

  useEffect(() => {
    if (!form.district_code) {
      setWards([]);
      return;
    }
    fetchWards(form.district_code)
      .then(setWards)
      .catch((e) => setError((e as Error).message));
  }, [form.district_code]);

  const items = cart?.items || [];
  const giftCount = useMemo(
    () => items.reduce((sum, item) => sum + item.quantity, 0),
    [items],
  );
  const subtotal = cart?.total_vnd || 0;
  const ticket = discount?.ticket;
  const discountPercent = discount?.ticket ? discount.percent : 0;
  const discountVnd = discountPercent ? Math.floor((subtotal * discountPercent) / 100) : 0;
  const payTotal = Math.max(0, subtotal - discountVnd);

  async function setQty(productId: number, quantity: number) {
    setError("");
    try {
      if (getStoredUser()) {
        setCart(await shopApi.setCartQty(productId, quantity));
        window.dispatchEvent(new CustomEvent(CART_CHANGED_EVENT));
      } else {
        setGuestCartQty(productId, quantity);
        await loadCart();
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function validateForm(): string | null {
    if (form.recipient_name.trim().length < 2) return "Nhập họ và tên người nhận";
    const phone = form.phone.replace(/\D/g, "");
    if (!PHONE_RE.test(phone)) return "Số điện thoại phải gồm 10 chữ số, bắt đầu bằng 0";
    if (!form.province_code || !form.province_name) return "Chọn Tỉnh/Thành phố";
    if (!form.district_code || !form.district_name) return "Chọn Quận/Huyện";
    if (!form.ward_code || !form.ward_name) return "Chọn Phường/Xã";
    if (form.address_line.trim().length < 3) return "Nhập số nhà, tên đường";
    if (!termsAccepted(ageOk, termsOk)) return "Bạn cần đồng ý điều khoản";
    if (!items.length) return "Giỏ hàng trống";
    return null;
  }

  async function placeOrder() {
    const err = validateForm();
    if (err) {
      setError(err);
      return;
    }
    setSaving(true);
    setError("");
    try {
      const phone = form.phone.replace(/\D/g, "");
      const payload: ShopCheckoutPayload = {
        note: form.note.trim() || null,
        recipient_name: form.recipient_name.trim(),
        phone,
        province_code: form.province_code,
        province_name: form.province_name,
        district_code: form.district_code,
        district_name: form.district_name,
        ward_code: form.ward_code,
        ward_name: form.ward_name,
        address_line: form.address_line.trim(),
        payment_method: form.payment_method,
      };
      if (ticket) payload.pushup_ticket = ticket;
      if (!loggedIn) {
        payload.items = items.map((i) => ({
          product_id: i.product_id,
          quantity: i.quantity,
        }));
      }
      const order = await shopApi.checkout(payload);
      clearPushupDiscount();
      setDiscount(null);
      if (!loggedIn) clearGuestCart();
      else window.dispatchEvent(new CustomEvent(CART_CHANGED_EVENT));
      const code = order.public_code || String(order.id);
      if (form.payment_method === "bank_transfer") {
        router.push(
          `/don-hang/thanh-toan?code=${encodeURIComponent(code)}&phone=${encodeURIComponent(phone)}`,
        );
      } else {
        router.push(
          `/don-hang/thanh-cong?code=${encodeURIComponent(code)}&phone=${encodeURIComponent(phone)}&gifts=${giftCount}`,
        );
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="h-48 animate-pulse rounded-2xl bg-white shadow-soft" />;
  }

  if (!items.length) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center shadow-soft">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-600" aria-hidden>
          <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
            <path d="M6 6h15l-1.5 9h-12zM6 6 5 3H2" />
            <circle cx="9" cy="20" r="1" />
            <circle cx="18" cy="20" r="1" />
          </svg>
        </span>
        <p className="mt-4 text-lg font-bold text-slate-900">Giỏ hàng trống</p>
        <p className="mt-1 text-sm text-slate-500">Chọn dụng cụ để bắt đầu đặt hàng.</p>
        <Link
          href="/mua-dung-cu"
          className="mt-5 inline-flex min-h-11 items-center justify-center rounded-xl bg-brand-600 px-5 text-sm font-bold text-white transition hover:bg-brand-700"
        >
          Xem dụng cụ
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Giỏ hàng & đặt hàng</h1>
          <p className="mt-2 inline-flex items-center rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
            Free ship toàn quốc
          </p>
        </div>
        <Link
          href="/mua-dung-cu"
          className="text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
        >
          Tiếp tục mua
        </Link>
      </div>

      {error ? (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
      <section className="rounded-2xl bg-white p-5 shadow-soft ring-1 ring-slate-100">
        <h2 className="text-lg font-bold text-slate-900">1. Thông tin người nhận</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm sm:col-span-2">
            <span className="font-medium text-slate-700">Họ và tên người nhận *</span>
            <input
              className={FIELD}
              value={form.recipient_name}
              onChange={(e) => setForm({ ...form, recipient_name: e.target.value })}
              autoComplete="name"
              required
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="font-medium text-slate-700">Số điện thoại *</span>
            <input
              className={FIELD}
              value={form.phone}
              onChange={(e) =>
                setForm({ ...form, phone: e.target.value.replace(/\D/g, "").slice(0, 10) })
              }
              inputMode="numeric"
              maxLength={10}
              placeholder="0xxxxxxxxx"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Tỉnh/Thành phố *</span>
            <select
              className={FIELD}
              value={form.province_code}
              onChange={(e) => {
                const code = e.target.value;
                const name = provinces.find((p) => p.code === code)?.name || "";
                setForm({
                  ...form,
                  province_code: code,
                  province_name: name,
                  district_code: "",
                  district_name: "",
                  ward_code: "",
                  ward_name: "",
                });
              }}
              required
            >
              <option value="">Chọn tỉnh/thành</option>
              {provinces.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Quận/Huyện *</span>
            <select
              className={FIELD}
              value={form.district_code}
              disabled={!form.province_code}
              onChange={(e) => {
                const code = e.target.value;
                const name = districts.find((d) => d.code === code)?.name || "";
                setForm({
                  ...form,
                  district_code: code,
                  district_name: name,
                  ward_code: "",
                  ward_name: "",
                });
              }}
              required
            >
              <option value="">Chọn quận/huyện</option>
              {districts.map((d) => (
                <option key={d.code} value={d.code}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="font-medium text-slate-700">Phường/Xã *</span>
            <select
              className={FIELD}
              value={form.ward_code}
              disabled={!form.district_code}
              onChange={(e) => {
                const code = e.target.value;
                const name = wards.find((w) => w.code === code)?.name || "";
                setForm({ ...form, ward_code: code, ward_name: name });
              }}
              required
            >
              <option value="">Chọn phường/xã</option>
              {wards.map((w) => (
                <option key={w.code} value={w.code}>
                  {w.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="font-medium text-slate-700">Số nhà, tên đường, tòa nhà/thôn/xóm *</span>
            <input
              className={FIELD}
              value={form.address_line}
              onChange={(e) => setForm({ ...form, address_line: e.target.value })}
              autoComplete="street-address"
              required
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="font-medium text-slate-700">Ghi chú (tuỳ chọn)</span>
            <textarea
              className={`${FIELD} resize-none`}
              rows={2}
              value={form.note}
              onChange={(e) => setForm({ ...form, note: e.target.value })}
              placeholder="Ví dụ: giao giờ hành chính, gọi trước khi giao…"
            />
          </label>
        </div>
      </section>

      <section className="rounded-2xl bg-white p-5 shadow-soft ring-1 ring-slate-100">
        <h2 className="text-lg font-bold text-slate-900">2. Sản phẩm & thanh toán</h2>
        <ul className="mt-4 space-y-4">
          {items.map((it) => (
            <li key={it.product_id} className="flex gap-3 border-b border-slate-100 pb-4 last:border-0">
              <div className={`h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-slate-50 ${equipmentImageFitClass(undefined)}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={mediaUrl(it.image_url) || ""} alt="" className="h-full w-full object-contain" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{it.name_vi}</p>
                    <p className="text-sm text-slate-500">{formatVnd(it.price_vnd)}</p>
                  </div>
                  <p className="shrink-0 text-sm font-bold text-slate-900">{formatVnd(it.line_total_vnd)}</p>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <div className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50">
                    <button
                      type="button"
                      aria-label="Giảm số lượng"
                      disabled={it.quantity <= 1}
                      onClick={() => void setQty(it.product_id, it.quantity - 1)}
                      className="grid h-9 w-9 place-items-center rounded-full text-lg font-bold text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:text-slate-300"
                    >
                      −
                    </button>
                    <span className="min-w-8 text-center text-sm font-bold text-slate-900">{it.quantity}</span>
                    <button
                      type="button"
                      aria-label="Tăng số lượng"
                      disabled={it.quantity >= it.stock_qty}
                      onClick={() => void setQty(it.product_id, it.quantity + 1)}
                      className="grid h-9 w-9 place-items-center rounded-full text-lg font-bold text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:text-slate-300"
                    >
                      +
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => void setQty(it.product_id, 0)}
                    className="text-xs font-semibold text-rose-600 hover:underline"
                  >
                    Xóa
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
        {ticket ? (
          <div className="mt-4 rounded-xl border border-brand-100 bg-brand-50 px-3 py-3">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-semibold text-brand-800">
                Giảm {discountPercent}% thử thách chống đẩy
              </p>
              <button
                type="button"
                className="text-xs font-semibold text-slate-600 hover:underline"
                onClick={() => {
                  clearPushupDiscount();
                  setDiscount(null);
                }}
              >
                Bỏ
              </button>
            </div>
            <p className="mt-1 text-xs text-brand-700">
              {discount?.reps} cái · tối đa 1 ngày · đóng tab thì mất phiếu trên máy này
            </p>
          </div>
        ) : null}

        <div className="mt-4 space-y-2 rounded-xl bg-slate-50 px-3 py-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">Tạm tính · Ship miễn phí</p>
            <p className="text-sm font-semibold text-slate-900">{formatVnd(subtotal)}</p>
          </div>
          {discountVnd > 0 ? (
            <div className="flex items-center justify-between">
              <p className="text-sm text-brand-700">Giảm thử thách chống đẩy</p>
              <p className="text-sm font-semibold text-brand-700">−{formatVnd(discountVnd)}</p>
            </div>
          ) : null}
          <div className="flex items-center justify-between border-t border-slate-200 pt-2">
            <p className="text-sm font-semibold text-slate-700">Thanh toán</p>
            <p className="text-base font-bold text-slate-900">{formatVnd(payTotal)}</p>
          </div>
        </div>

        <fieldset className="mt-5 space-y-2">
          <legend className="text-sm font-semibold text-slate-800">Phương thức thanh toán</legend>
          <label
            className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 text-sm transition ${
              form.payment_method === "cod"
                ? "border-brand-400 bg-brand-50 ring-2 ring-brand-100"
                : "border-slate-200 hover:border-slate-300"
            }`}
          >
            <input
              type="radio"
              name="pay"
              className="mt-1"
              checked={form.payment_method === "cod"}
              onChange={() => setForm({ ...form, payment_method: "cod" })}
            />
            <span>
              <span className="block font-semibold text-slate-900">Thanh toán khi nhận hàng (COD)</span>
              <span className="mt-0.5 block text-xs text-slate-500">Trả tiền mặt hoặc chuyển khoản cho shipper.</span>
            </span>
          </label>
          <label
            className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 text-sm transition ${
              form.payment_method === "bank_transfer"
                ? "border-brand-400 bg-brand-50 ring-2 ring-brand-100"
                : "border-slate-200 hover:border-slate-300"
            }`}
          >
            <input
              type="radio"
              name="pay"
              className="mt-1"
              checked={form.payment_method === "bank_transfer"}
              onChange={() => setForm({ ...form, payment_method: "bank_transfer" })}
            />
            <span>
              <span className="block font-semibold text-slate-900">Chuyển khoản ngân hàng (QR)</span>
              <span className="mt-0.5 block text-xs text-slate-500">Quét VietQR sau khi đặt hàng.</span>
            </span>
          </label>
        </fieldset>

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
          disabled={saving}
          onClick={() => void placeOrder()}
          className="mt-5 w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
        >
          {saving ? "Đang đặt…" : "Tiếp tục"}
        </button>
      </section>
      </div>
    </div>
  );
}
