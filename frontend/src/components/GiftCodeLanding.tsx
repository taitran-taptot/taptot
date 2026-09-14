"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getAccessToken } from "@/lib/auth";
import { BRAND_NAME } from "@/lib/brand";
import { formatGiftCodeInput, giftStartHref } from "@/lib/giftCode";
import { redeemCodeApi, type RedeemLookup } from "@/lib/shopApi";

export default function GiftCodeLanding() {
  const router = useRouter();
  const search = useSearchParams();
  const [code, setCode] = useState(() => formatGiftCodeInput(search.get("code") || ""));
  const [lookup, setLookup] = useState<RedeemLookup | null>(null);
  const [checking, setChecking] = useState(false);

  async function check(value: string) {
    const formatted = formatGiftCodeInput(value);
    if (formatted.replace(/-/g, "").length < 10) {
      setLookup(null);
      return;
    }
    setChecking(true);
    try {
      setLookup(await redeemCodeApi.lookup(formatted));
    } catch {
      setLookup({ valid: false, status: "invalid" });
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    if (!code) return;
    const timer = window.setTimeout(() => void check(code), 0);
    return () => window.clearTimeout(timer);
    // QR query is read once when this landing page mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function goStart() {
    const formatted = formatGiftCodeInput(code);
    if (!lookup?.valid || !formatted) return;
    router.push(giftStartHref(formatted, !!getAccessToken()));
  }

  const ready = formatGiftCodeInput(code).length >= 12 && lookup?.valid === true && !checking;

  return (
    <section className="mx-auto max-w-lg">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
          Nhận lộ trình 100 ngày của bạn
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Nhập mã trên tem sản phẩm {BRAND_NAME}. Mã chỉ được sử dụng sau khi lộ trình của bạn tạo thành công.
        </p>
      </div>

      <div className="rounded-2xl bg-white p-6 shadow-soft">
        <label className="block text-sm font-semibold text-slate-600">Mã trên tem</label>
        <input
          autoFocus
          inputMode="text"
          autoCapitalize="characters"
          autoCorrect="off"
          spellCheck={false}
          placeholder="TT-····-····"
          className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3.5 font-mono text-lg font-bold tracking-wide uppercase"
          value={code}
          onChange={(e) => {
            const next = formatGiftCodeInput(e.target.value);
            setCode(next);
            void check(next);
          }}
          onBlur={() => void check(code)}
        />
        {checking && <p className="mt-2 text-xs text-slate-400">Đang kiểm tra mã…</p>}
        {lookup && lookup.valid && (
          <p className="mt-2 text-sm font-medium text-emerald-700">
            Mã còn hiệu lực
            {lookup.product_name_vi ? ` · ${lookup.product_name_vi}` : ""}.
          </p>
        )}
        {lookup && !lookup.valid && (
          <p className="mt-2 text-sm text-rose-600">
            Mã đã được sử dụng hoặc không đúng. Hãy kiểm tra lại mã trên tem.
          </p>
        )}
        <button
          type="button"
          onClick={goStart}
          disabled={!ready}
          className="mt-5 w-full rounded-xl bg-brand-500 py-3.5 text-sm font-bold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Tạo lộ trình 100 ngày
        </button>
        <p className="mt-4 text-center text-xs leading-relaxed text-slate-500">
          Mỗi sản phẩm TAPTOT được tặng kèm một mã dùng một lần trên tem.
        </p>
      </div>
    </section>
  );
}
