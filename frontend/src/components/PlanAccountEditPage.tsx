"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import PlanDetailEditor from "@/components/PlanDetailEditor";
import { plansApi, type PlanDetail } from "@/lib/plansApi";
import { claimGuestPlansAfterAuth } from "@/lib/authApi";

export default function PlanAccountEditPage() {
  const params = useParams();
  const search = useSearchParams();
  const rawId = typeof params.id === "string" ? params.id : "";
  const planId = Number(rawId);
  const [detail, setDetail] = useState<PlanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const week = Number(search.get("week") || "") || undefined;
  const day = Number(search.get("day") || "") || undefined;
  const swap = Number(search.get("swap") || "") || undefined;

  useEffect(() => {
    if (!Number.isFinite(planId) || planId <= 0) {
      setErr("Link không hợp lệ.");
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr("");
      try {
        await claimGuestPlansAfterAuth();
        const next = await plansApi.get(planId);
        if (!cancelled) setDetail(next);
      } catch (ex) {
        if (!cancelled) setErr((ex as Error).message || "Không tải được lịch.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [planId]);

  if (loading) {
    return <p className="py-10 text-center text-sm text-slate-400">Đang mở lịch để sửa…</p>;
  }

  if (err || !detail) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl bg-white p-6 text-center shadow-soft">
        <p className="text-rose-500">{err || "Không tìm thấy lịch tập."}</p>
        <Link
          href="/tai-khoan/ke-hoach"
          className="mt-4 inline-flex rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
        >
          Về lịch của tôi
        </Link>
      </div>
    );
  }

  return (
    <PlanDetailEditor
      detail={detail}
      variant="page"
      initialWeek={week}
      initialDayNumber={day}
      initialSwapExerciseId={swap}
      onCancel={() => undefined}
      onSaved={setDetail}
    />
  );
}
