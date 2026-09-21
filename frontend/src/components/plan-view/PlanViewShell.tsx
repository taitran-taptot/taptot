"use client";

import type { PlanViewTab } from "./types";
import { PLAN_VIEW_TABS } from "./types";

export default function PlanViewShell({
  title,
  recap,
  chips,
  calorieLine,
  calorieHint,
  belowHero,
  activeTab,
  onTabChange,
  nav,
  children,
  tabs = PLAN_VIEW_TABS,
}: {
  title: string;
  recap?: string | null;
  chips: string[];
  calorieLine?: string | null;
  calorieHint?: string | null;
  belowHero?: React.ReactNode;
  activeTab: PlanViewTab;
  onTabChange: (tab: PlanViewTab) => void;
  nav?: React.ReactNode;
  children: React.ReactNode;
  tabs?: { id: PlanViewTab; label: string }[];
}) {
  return (
    <div className="mx-auto max-w-3xl space-y-3 overflow-x-hidden px-3 py-4 sm:space-y-4 sm:px-4 sm:py-6 lg:max-w-5xl">
      <div className="rounded-2xl bg-gradient-to-br from-brand-500 to-emerald-600 p-4 text-white shadow-soft sm:p-5">
        <h1 className="text-lg font-semibold leading-tight break-words sm:text-xl">{title}</h1>
        {recap && (
          <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed opacity-90 [overflow-wrap:anywhere]">
            {recap}
          </p>
        )}
        {chips.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {chips.slice(0, 4).map((s) => (
              <span
                key={s}
                className="max-w-full rounded-full bg-white/20 px-2.5 py-0.5 text-[11px] font-semibold sm:text-xs"
              >
                {s}
              </span>
            ))}
          </div>
        )}
        {calorieLine && (
          <p className="mt-2 text-xs font-semibold opacity-90">{calorieLine}</p>
        )}
        {calorieHint && (
          <p className="mt-0.5 text-[11px] font-medium opacity-80">{calorieHint}</p>
        )}
      </div>

      {belowHero}

      <div className="sticky top-16 z-20 -mx-3 space-y-2 border-b border-slate-100 bg-slate-50/95 px-3 py-2 backdrop-blur supports-[backdrop-filter]:bg-slate-50/80 sm:-mx-4 sm:px-4">
        <div
          className="flex rounded-xl bg-slate-200/60 p-1"
          role="tablist"
          aria-label="Phần lịch tập"
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`min-h-[44px] flex-1 rounded-lg px-2 text-xs font-bold transition sm:text-sm ${
                activeTab === tab.id
                  ? "bg-white text-brand-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-800"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        {nav}
      </div>

      <div role="tabpanel">{children}</div>
    </div>
  );
}
