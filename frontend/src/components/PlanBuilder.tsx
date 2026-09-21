"use client";

import dynamic from "next/dynamic";

const PlanBuilder = dynamic(() => import("./plan-builder/PlanBuilder"), {
  ssr: false,
  loading: () => <p className="p-6 text-sm text-slate-500">Đang mở trình tự tạo lịch…</p>,
});

export default PlanBuilder;
