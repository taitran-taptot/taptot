"use client";

import { useEffect, useState } from "react";
import { fetchSitePageMedia } from "@/lib/sitePageMedia";

export default function TradeNoticeBadge({ className = "" }: { className?: string }) {
  const [href, setHref] = useState("");

  useEffect(() => {
    let live = true;
    void fetchSitePageMedia().then((media) => {
      if (live) setHref((media.bo_cong_thuong_url || "").trim());
    });
    return () => {
      live = false;
    };
  }, []);

  if (!href) return null;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex shrink-0 rounded-lg bg-white p-1 ring-1 ring-slate-200 ${className}`.trim()}
    >
      <img src="/brand/bo-cong-thuong.svg" alt="Đã thông báo Bộ Công Thương" className="h-12 w-auto" />
    </a>
  );
}
