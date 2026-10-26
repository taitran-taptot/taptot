"use client";

import Link from "next/link";
import { PAYMENT_POLICY_HREF, PRIVACY_HREF, SALES_POLICY_HREF } from "@/lib/legalMeta";
import { TERMS_AGE_CHECKBOX, TERMS_AGREE_CHECKBOX, TERMS_HREF } from "@/lib/terms";

export function termsAccepted(ageOk: boolean, termsOk: boolean) {
  return ageOk && termsOk;
}

export default function TermsConsent({
  ageOk,
  termsOk,
  onAgeOk,
  onTermsOk,
  idPrefix = "terms",
  showAge = true,
  includeCommerce = false,
}: {
  ageOk: boolean;
  termsOk: boolean;
  onAgeOk: (v: boolean) => void;
  onTermsOk: (v: boolean) => void;
  idPrefix?: string;
  showAge?: boolean;
  includeCommerce?: boolean;
}) {
  return (
    <fieldset className="space-y-3 rounded-2xl border border-amber-200 bg-amber-50/70 p-4">
      <legend className="type-kicker px-1 text-amber-800">
        Xác nhận trước khi tiếp tục
      </legend>
      {showAge ? (
      <label htmlFor={`${idPrefix}-age`} className="flex cursor-pointer items-start gap-3 text-sm leading-snug text-slate-700">
        <input
          id={`${idPrefix}-age`}
          type="checkbox"
          checked={ageOk}
          onChange={(e) => onAgeOk(e.target.checked)}
          className="mt-0.5 h-4 w-4 shrink-0 accent-brand-500"
        />
        <span>{TERMS_AGE_CHECKBOX}</span>
      </label>
      ) : null}
      <label htmlFor={`${idPrefix}-agree`} className="flex cursor-pointer items-start gap-3 text-sm leading-snug text-slate-700">
        <input
          id={`${idPrefix}-agree`}
          type="checkbox"
          checked={termsOk}
          onChange={(e) => onTermsOk(e.target.checked)}
          className="mt-0.5 h-4 w-4 shrink-0 accent-brand-500"
        />
        <span>
          Tôi đã đọc, hiểu và đồng ý với{" "}
          <Link
            href={TERMS_HREF}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800"
            onClick={(e) => e.stopPropagation()}
          >
            Điều khoản dịch vụ
          </Link>
          {includeCommerce ? ", " : " cùng "}
          <Link
            href={PRIVACY_HREF}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800"
            onClick={(e) => e.stopPropagation()}
          >
            Chính sách bảo mật
          </Link>
          {includeCommerce ? (
            <>
              {", "}
              <Link
                href={SALES_POLICY_HREF}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800"
                onClick={(e) => e.stopPropagation()}
              >
                Chính sách bán hàng
              </Link>
              {" và "}
              <Link
                href={PAYMENT_POLICY_HREF}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800"
                onClick={(e) => e.stopPropagation()}
              >
                Chính sách thanh toán
              </Link>
            </>
          ) : null}{" "}
          của hệ thống.
        </span>
      </label>
      {includeCommerce ? null : <p className="sr-only">{TERMS_AGREE_CHECKBOX}</p>}
    </fieldset>
  );
}
