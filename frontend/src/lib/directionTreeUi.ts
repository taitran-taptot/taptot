import type { DirectionSelection, SpecializationBranchKey } from "@/lib/directionTree";

export const SPEC_THEME: Record<
  SpecializationBranchKey,
  { idle: string; selected: string; icon: string; kicker: string; panel: string; leaf: string }
> = {
  gym: {
    idle: "border-emerald-200 bg-emerald-50 text-emerald-950 hover:border-emerald-400 hover:bg-emerald-100/80",
    selected: "border-emerald-400 bg-emerald-100 text-emerald-950 ring-2 ring-emerald-500 shadow-md",
    icon: "text-emerald-600",
    kicker: "text-emerald-700",
    panel: "border-emerald-100 border-l-4 border-l-emerald-500",
    leaf: "border-emerald-200 bg-emerald-50/80 text-emerald-900 hover:bg-emerald-100",
  },
  calisthenic: {
    idle: "border-sky-200 bg-sky-50 text-sky-950 hover:border-sky-400 hover:bg-sky-100/80",
    selected: "border-sky-400 bg-sky-100 text-sky-950 ring-2 ring-sky-500 shadow-md",
    icon: "text-sky-600",
    kicker: "text-sky-700",
    panel: "border-sky-100 border-l-4 border-l-sky-500",
    leaf: "border-sky-200 bg-sky-50/80 text-sky-900 hover:bg-sky-100",
  },
  sport: {
    idle: "border-orange-200 bg-orange-50 text-orange-950 hover:border-orange-400 hover:bg-orange-100/80",
    selected: "border-orange-400 bg-orange-100 text-orange-950 ring-2 ring-orange-500 shadow-md",
    icon: "text-orange-600",
    kicker: "text-orange-700",
    panel: "border-orange-100 border-l-4 border-l-orange-500",
    leaf: "border-orange-200 bg-orange-50/80 text-orange-900 hover:bg-orange-100",
  },
  martial: {
    idle: "border-rose-200 bg-rose-50 text-rose-950 hover:border-rose-400 hover:bg-rose-100/80",
    selected: "border-rose-400 bg-rose-100 text-rose-950 ring-2 ring-rose-500 shadow-md",
    icon: "text-rose-600",
    kicker: "text-rose-700",
    panel: "border-rose-100 border-l-4 border-l-rose-500",
    leaf: "border-rose-200 bg-rose-50/80 text-rose-900 hover:bg-rose-100",
  },
  hybrid: {
    idle: "border-violet-200 bg-violet-50 text-violet-950 hover:border-violet-400 hover:bg-violet-100/80",
    selected: "border-violet-400 bg-violet-100 text-violet-950 ring-2 ring-violet-500 shadow-md",
    icon: "text-violet-600",
    kicker: "text-violet-700",
    panel: "border-violet-100 border-l-4 border-l-violet-500",
    leaf: "border-violet-200 bg-violet-50/80 text-violet-900 hover:bg-violet-100",
  },
  other: {
    idle: "border-lime-200 bg-lime-50 text-lime-950 hover:border-lime-400 hover:bg-lime-100/80",
    selected: "border-lime-400 bg-lime-100 text-lime-950 ring-2 ring-lime-500 shadow-md",
    icon: "text-lime-700",
    kicker: "text-lime-700",
    panel: "border-lime-100 border-l-4 border-l-lime-500",
    leaf: "border-lime-200 bg-lime-50/80 text-lime-900 hover:bg-lime-100",
  },
};

export function panelTheme(selection: DirectionSelection) {
  if (selection.kind === "foundation") {
    return {
      panel: "border-brand-100 border-l-4 border-l-brand-500",
      kicker: "text-brand-700",
      continueBtn: "bg-brand-500 hover:bg-brand-600",
      leaf: "border-slate-200 bg-slate-50 text-slate-600",
    };
  }
  if (selection.kind === "challenge") {
    return {
      panel: "border-amber-100 border-l-4 border-l-amber-500",
      kicker: "text-amber-700",
      continueBtn: "bg-amber-500 hover:bg-amber-600",
      leaf: "border-amber-200 bg-amber-50 text-amber-900",
    };
  }
  const spec = SPEC_THEME[selection.branch];
  return {
    panel: spec.panel,
    kicker: spec.kicker,
    continueBtn: "bg-brand-500 hover:bg-brand-600",
    leaf: spec.leaf,
  };
}
