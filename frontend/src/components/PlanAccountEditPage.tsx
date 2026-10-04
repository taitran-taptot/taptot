"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import PlanDetailEditor from "@/components/PlanDetailEditor";
import { plansApi, type PlanDetail } from "@/lib/plansApi";
import { claimGuestPlansAfterAuth } from "@/lib/authApi";
import { getStoredUser } from "@/lib/auth";
import { accountShellHref } from "@/lib/accountWorkspace";

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

  const load = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!Number.isFinite(planId) || planId <= 0) {
        setErr("Link không hợp lệ.");
        setLoading(false);
        return;
      }
      if (!opts?.silent) {
        setLoading(true);
        setErr("");
      }
      try {
        await claimGuestPlansAfterAuth();
        const next = await plansApi.get(planId);
        setDetail(next);
        setErr("");
      } catch (ex) {
        setErr((ex as Error).message || "Không tải được lịch.");
      } finally {
        setLoading(false);
      }
    },
    [planId],
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const onPageShow = (e: PageTransitionEvent) => {
      if (e.persisted) void load({ silent: true });
    };
    const onVisible = () => {
      if (document.visibilityState === "visible") void load({ silent: true });
    };
    window.addEventListener("pageshow", onPageShow);
    window.addEventListener("focus", onVisible);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("pageshow", onPageShow);
      window.removeEventListener("focus", onVisible);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [load]);

  if (loading && !detail) {
    return <p className="py-10 text-center text-sm text-slate-400">Đang mở lịch để sửa…</p>;
  }

  if ((err || !detail) && !loading) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl bg-white p-6 text-center shadow-soft">
        <p className="text-rose-500">{err || "Không tìm thấy lịch tập."}</p>
        <Link
          href={accountShellHref(getStoredUser()?.role, "ke-hoach")}
          className="mt-4 inline-flex rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
        >
          Về lịch của tôi
        </Link>
      </div>
    );
  }

  if (!detail) {
    return <p className="py-10 text-center text-sm text-slate-400">Đang mở lịch để sửa…</p>;
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
