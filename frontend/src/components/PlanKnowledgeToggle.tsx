"use client";

import { useCallback, useEffect, useState } from "react";

import { migrateSessionKeys } from "@/lib/storageKeys";

const STORAGE_KEY = "taptot_plan_knowledge";
migrateSessionKeys([
  ["tfit_plan_knowledge", STORAGE_KEY],
  ["vietfit_plan_knowledge", STORAGE_KEY],
]);

/** Session preference for AI plan knowledge toggle (default OFF — schedule first). */
export function usePlanKnowledge(defaultOn = false) {
  const [showKnowledge, setShowKnowledge] = useState(defaultOn);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored === "0") setShowKnowledge(false);
      else if (stored === "1") setShowKnowledge(true);
    } catch {
      /* ignore */
    }
  }, []);

  const setKnowledge = useCallback((value: boolean) => {
    setShowKnowledge(value);
    try {
      sessionStorage.setItem(STORAGE_KEY, value ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, []);

  return { showKnowledge, setKnowledge };
}

export default function PlanKnowledgeToggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-soft">
      <div>
        <p className="text-sm font-bold text-slate-800">Hiển thị kiến thức</p>
        <p className="text-xs text-slate-500">Giải thích vì sao lịch tập & thực đơn được xếp như vậy</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-pressed={checked}
        aria-label="Hiển thị kiến thức"
        onClick={() => onChange(!checked)}
        className={`relative h-7 w-12 shrink-0 rounded-full transition ${
          checked ? "bg-brand-500" : "bg-slate-300"
        }`}
      >
        <span
          className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition ${
            checked ? "left-5" : "left-0.5"
          }`}
        />
      </button>
    </label>
  );
}
