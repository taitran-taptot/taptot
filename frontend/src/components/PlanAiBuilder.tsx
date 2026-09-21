"use client";

import dynamic from "next/dynamic";

const PlanAiBuilder = dynamic(() => import("./plan-ai-builder/PlanAiBuilder"), {
  ssr: false,
  loading: () => <p className="p-6 text-sm text-slate-500">Đang mở trình tạo lịch…</p>,
});

export default PlanAiBuilder;
