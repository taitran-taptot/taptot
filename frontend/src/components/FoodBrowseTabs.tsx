"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { COOK_HREF, FOODS_HREF } from "@/lib/foodRoutes";

const TABS = [
  {
    href: FOODS_HREF,
    label: "Thực phẩm",
    match: (pathname: string) => pathname === FOODS_HREF || pathname.startsWith(`${FOODS_HREF}/`),
  },
  {
    href: COOK_HREF,
    label: "Cách nấu món Việt",
    match: (pathname: string) => pathname === COOK_HREF || pathname.startsWith(`${COOK_HREF}/`),
  },
] as const;

export default function FoodBrowseTabs() {
  const pathname = usePathname() || FOODS_HREF;
  return (
    <div className="mb-4 flex gap-1.5 rounded-2xl bg-white p-1.5 shadow-soft sm:gap-2">
      {TABS.map((t) => {
        // Detail of a recipe still lives under /cach-nau?mon=… — keep “Cách nấu” tab active.
        const active = t.match(pathname);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`flex-1 rounded-xl px-1.5 py-2.5 text-center text-[11px] font-bold leading-tight transition sm:px-3 sm:text-sm ${
              active ? "bg-brand-500 text-white shadow-soft" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {t.label}
          </Link>
        );
      })}
    </div>
  );
}
