"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { COOK_HREF, DISHES_HREF, FOODS_HREF } from "@/lib/foodRoutes";

const TABS = [
  {
    href: FOODS_HREF,
    label: "Thực phẩm",
    match: (pathname: string) => pathname === FOODS_HREF || pathname.startsWith(`${FOODS_HREF}/`),
  },
  {
    href: DISHES_HREF,
    label: "Món truyền thống",
    match: (pathname: string) => pathname === DISHES_HREF || pathname.startsWith(`${DISHES_HREF}/`),
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
    <div className="mb-4 flex gap-2 rounded-2xl bg-white p-1.5 shadow-soft">
      {TABS.map((t) => {
        const active = t.match(pathname);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`flex-1 rounded-xl px-2 py-2.5 text-center text-sm font-bold transition sm:px-3 ${
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
