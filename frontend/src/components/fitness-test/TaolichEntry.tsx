"use client";

import { useEffect, useState } from "react";
import PlanAiBuilder from "@/components/PlanAiBuilder";
import { formatGiftCodeInput } from "@/lib/giftCode";
import { seedPlanDraftFromFitnessTest } from "@/lib/fitness-tracker";
import { FITNESS_TEST_GUEST_SLUG } from "@/lib/fitness-tracker/session/offers";

export default function TaolichEntry({ code }: { code: string }) {
  const raw = decodeURIComponent(code || "");
  const formatted =
    raw.toLowerCase() === FITNESS_TEST_GUEST_SLUG
      ? FITNESS_TEST_GUEST_SLUG
      : formatGiftCodeInput(raw);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    seedPlanDraftFromFitnessTest(formatted);
    setReady(true);
  }, [formatted]);
  if (!ready) return <p className="text-sm text-slate-500">Đang mở trình tạo lịch…</p>;
  return <PlanAiBuilder initialGiftCode={formatted} />;
}
