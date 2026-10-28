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
