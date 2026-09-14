import { Suspense } from "react";
import PlanAccountEditPage from "@/components/PlanAccountEditPage";

export default function Page() {
  return (
    <Suspense fallback={<p className="py-10 text-center text-sm text-slate-400">Đang mở lịch…</p>}>
      <PlanAccountEditPage />
    </Suspense>
  );
}
