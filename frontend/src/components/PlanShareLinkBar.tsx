"use client";

import { useState } from "react";
import { copyText, planPublicPath, planShareUrl } from "@/lib/sharePlan";
import { isValidShareSlug, sanitizeShareSlugInput, shareSlugError } from "@/lib/shareSlug";

export default function PlanShareLinkBar({
  plan,
  slug,
  onSlugChange,
}: {
  plan: {
    share_url_path?: string | null;
    redeem_code?: string | null;
    share_token?: string | null;
  };
  slug?: string;
  onSlugChange?: (next: string) => void;
}) {
  const savedPath = planPublicPath(plan);
  const [copied, setCopied] = useState(false);
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const draft = (slug ?? "").trim();
  const err = onSlugChange ? shareSlugError(draft) : "";
  const copyPath =
    onSlugChange && draft && isValidShareSlug(draft) ? `/lich/${draft}` : savedPath;
  const url = copyPath ? planShareUrl(copyPath) : "";

  if (!savedPath && !onSlugChange) return null;

  async function copy() {
    if (!url) return;
    const ok = await copyText(url);
    if (!ok) return;
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div>
      <p className="text-sm font-semibold text-slate-600">Link chia sẻ</p>
      <div className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-stretch">
        <span className="flex min-w-0 flex-1 overflow-hidden rounded-xl ring-1 ring-slate-200">
          <span className="shrink-0 bg-slate-50 px-2 py-2 text-[11px] text-slate-400">
            {origin}/lich/
          </span>
          {onSlugChange ? (
            <input
              value={slug ?? ""}
              onChange={(e) => onSlugChange(sanitizeShareSlugInput(e.target.value))}
              className="min-w-0 flex-1 border-0 px-2 py-2 text-sm outline-none"
              placeholder="tuy-chon"
              spellCheck={false}
              aria-label="Đường dẫn /lich/"
            />
          ) : (
            <input
              readOnly
              value={(savedPath || "").replace(/^\/lich\//, "")}
              className="min-w-0 flex-1 border-0 bg-white px-2 py-2 text-sm text-slate-700 outline-none"
              aria-label="Link chia sẻ"
            />
          )}
        </span>
        <button
          type="button"
          onClick={() => void copy()}
          disabled={!url}
          className="shrink-0 rounded-xl bg-brand-500 px-3 py-2 text-xs font-bold text-white hover:bg-brand-600 disabled:opacity-40"
        >
          {copied ? "Đã sao chép" : "Sao chép"}
        </button>
      </div>
      {onSlugChange ? (
        err ? (
          <p className="mt-1 text-[11px] font-medium text-rose-600">{err}</p>
        ) : (
          <p className="mt-1 text-[11px] text-slate-400">
            3–48 ký tự a-z 0-9 và dấu gạch. Lưu để áp dụng đường dẫn mới.
          </p>
        )
      ) : null}
    </div>
  );
}
