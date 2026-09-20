"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { aiApi } from "@/lib/authApi";
import {
  applyFitnessResultToExistingDraft,
  builderPathAfterFitnessTest,
  clearFitnessTestReturnPath,
  fitnessTestReturnPath,
  isAdvancedFitnessTest,
  isFitnessTestFromBuilder,
  isFoundationExitTest,
  loadFitnessTestResult,
  offerIncludesRun,
  offerStandardLevel,
  resultToBaseline,
  seedPlanDraftFromFitnessTest,
} from "@/lib/fitness-tracker";
import { formatCountdown, offerLabel } from "@/lib/fitness-tracker/session/offers";

type AdvicePayload = {
  overall_failed: boolean;
  stretch_failed: boolean;
  package_level: "basic" | "advanced";
  package_pass: boolean;
  checks: Record<string, boolean | null>;
  not_met: string[];
  standards: { key: string; label_vi: string; display_vi: string }[];
  advice_vi: string[];
  used_openai: boolean;
  recommended_path?: string;
};

const CHECK_LABEL: Record<string, string> = {
  push: "Chống đẩy",
  pull: "Kéo / treo xà",
  squat: "Squat",
  plank: "Plank",
  run: "Chạy 10 phút",
};

export default function FitnessAdviceView({
  code,
  from,
}: {
  code: string;
  from?: string;
}) {
  const router = useRouter();
  const [fromSession, setFromSession] = useState(false);
  const fromBuilder = isFitnessTestFromBuilder(from) || fromSession;
  const [result, setResult] = useState<ReturnType<typeof loadFitnessTestResult>>(null);
  const [advice, setAdvice] = useState<AdvicePayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setFromSession(!!fitnessTestReturnPath());
    const stored = loadFitnessTestResult();
    setResult(stored);
    if (!stored || stored.code !== code) {
      setLoading(false);
      setError("Chưa có dữ liệu bài test. Hãy làm bài kiểm tra trước.");
      return;
    }
    aiApi
      .fitnessTestAdvice({
        gender: stored.gender,
        offer: stored.offer,
        fitness_baseline: resultToBaseline(stored),
        stretch_completed: stored.stretchCompleted,
        feeling: stored.feeling,
      })
      .then(setAdvice)
      .catch((e) => setError((e as Error).message || "Không lấy được lời khuyên."))
      .finally(() => setLoading(false));
  }, [code]);

  function continuePlan() {
    if (!result) return;
    if (fromBuilder) {
      if (!applyFitnessResultToExistingDraft()) {
        seedPlanDraftFromFitnessTest(code);
        applyFitnessResultToExistingDraft();
      }
      const next = builderPathAfterFitnessTest(from);
      clearFitnessTestReturnPath();
      router.push(next);
      return;
    }
    if (isAdvancedFitnessTest(result.offer)) {
      router.push("/kiemtratheluc");
      return;
    }
    seedPlanDraftFromFitnessTest(code);
    router.push(`/taolich/${encodeURIComponent(code)}`);
  }

  function backToBuilder() {
    router.push(builderPathAfterFitnessTest(from));
  }

  if (loading && !result) {
    return <p className="text-sm text-slate-500">Đang tải kết quả…</p>;
  }

  if (!result || result.code !== code) {
    return (
      <div className="rounded-3xl bg-white p-8 shadow-soft">
        <h1 className="text-2xl font-extrabold">Chưa có kết quả</h1>
        <p className="mt-2 text-sm text-slate-600">{error || "Hãy hoàn thành bài test trước."}</p>
        <Link href="/kiemtratheluc" className="mt-4 inline-block font-bold text-brand-700">
          Về danh sách thử thách
        </Link>
      </div>
    );
  }

  const durationMin = Math.round((result.finishedAt - result.startedAt) / 60000);
  const pullReps =
    result.gender !== "female" ||
    isAdvancedFitnessTest(result.offer) ||
    isFoundationExitTest(result.offer);
  const continueLabel = fromBuilder
    ? "Dùng kết quả này để tạo lịch"
    : isAdvancedFitnessTest(result.offer)
      ? "Về kiểm tra thể lực"
      : isFoundationExitTest(result.offer)
        ? "Tiếp tục tạo lịch thử thách nâng cao"
        : "Tiếp tục tạo lịch";

  return (
    <div className="space-y-6">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 to-white px-6 py-8 shadow-soft ring-1 ring-brand-100">
        {fromBuilder ? (
          <button
            type="button"
            onClick={backToBuilder}
            className="mb-3 text-sm font-bold text-brand-700 hover:underline"
          >
            ← Quay lại tạo lịch
          </button>
        ) : null}
        <p className="text-xs font-bold tracking-wide text-brand-600 uppercase">Lời khuyên sau test</p>
        <h1 className="mt-2 text-2xl font-extrabold sm:text-3xl">{offerLabel(result.offer)}</h1>
        <p className="mt-2 text-sm text-slate-600">
          {result.gender === "female" ? "Nữ" : "Nam"} · ~{durationMin} phút · chuẩn{" "}
          {offerStandardLevel(result.offer) === "advanced" ? "nâng cao" : "nền"}
        </p>
      </header>

      {(advice?.overall_failed || result.stretchSkipped) && (
        <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-800">
          Bài test thể lực bị đánh failed
          {result.stretchSkipped ? " vì bỏ giãn cơ." : "."} Bạn vẫn có thể tạo lịch.
        </p>
      )}

      <section className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
        <h2 className="text-lg font-extrabold">Thông số của bạn</h2>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          <li className="flex justify-between py-2">
            <span>Chống đẩy</span>
            <span className="font-bold">{result.pushupsMax} cái / 1 phút</span>
          </li>
          <li className="flex justify-between py-2">
            <span>{pullReps ? "Kéo xà" : "Treo xà"}</span>
            <span className="font-bold">
              {pullReps
                ? `${result.pullupsMax} cái`
                : `${Math.round(result.pullHoldSeconds)} giây`}
            </span>
          </li>
          <li className="flex justify-between py-2">
            <span>Squat</span>
            <span className="font-bold">{result.squatsMax} cái</span>
          </li>
          <li className="flex justify-between py-2">
            <span>Plank</span>
            <span className="font-bold">{formatCountdown(result.plankSeconds)}</span>
          </li>
          {offerIncludesRun(result.offer) ? (
            <li className="flex justify-between py-2">
              <span>Chạy 10 phút</span>
              <span className="font-bold">{(result.run10MinMeters / 1000).toFixed(2)} km</span>
            </li>
          ) : null}
        </ul>
      </section>

      {advice?.standards?.length ? (
        <section className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
          <h2 className="text-lg font-extrabold">So với chuẩn gói</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {advice.standards
              .filter((row) => offerIncludesRun(result.offer) || row.key !== "run")
              .map((row) => {
              const ok = advice.checks[row.key];
              return (
                <li key={row.key} className="flex items-center justify-between gap-3">
                  <span>
                    {row.label_vi}: {row.display_vi}
                  </span>
                  <span className={ok ? "font-bold text-brand-700" : "font-bold text-rose-600"}>
                    {ok ? "Đạt" : "Chưa đạt"}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      <section className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
        <h2 className="text-lg font-extrabold">Lời khuyên</h2>
        {loading && <p className="mt-2 text-sm text-slate-500">Đang soạn lời khuyên…</p>}
        {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}
        <ul className="mt-3 space-y-3 text-sm leading-relaxed text-slate-700">
          {(advice?.advice_vi || []).map((line) => (
            <li key={line} className="rounded-2xl bg-slate-50 px-4 py-3">
              {line}
            </li>
          ))}
        </ul>
        {advice?.not_met?.length ? (
          <p className="mt-3 text-xs text-slate-500">
            Chưa đạt: {advice.not_met.map((k) => CHECK_LABEL[k] || k).join(", ")}
          </p>
        ) : null}
      </section>

      {result.feeling ? (
        <p className="text-sm text-slate-500">Cảm nhận của bạn: {result.feeling}</p>
      ) : null}

      <button
        type="button"
        onClick={continuePlan}
        className="w-full rounded-2xl bg-brand-500 py-4 text-base font-extrabold text-white shadow-soft hover:bg-brand-600"
      >
        {continueLabel}
      </button>
    </div>
  );
}
