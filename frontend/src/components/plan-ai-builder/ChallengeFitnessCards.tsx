"use client";

import { useEffect, useState } from "react";
import ExerciseThumb from "@/components/ExerciseThumb";
import { api } from "@/lib/api";
import {
  BAND_LEVEL_OPTS,
  challengeTestMediaSpecs,
  pickChallengeExercise,
  type ChallengeTestDraft,
  type ChallengeTestMediaSpec,
  type ChallengeTestSpec,
} from "@/lib/challengeFitnessTests";
import { gifUrl, mediaUrl } from "@/lib/labels";
import { isDirectVideoUrl, youtubeEmbedUrl } from "@/lib/sharePlan";
import type { ExerciseListItem } from "@/lib/types";

function TestMedia({ ex, title }: { ex: ExerciseListItem | null; title: string }) {
  const [playYt, setPlayYt] = useState(false);
  const yt = youtubeEmbedUrl(ex?.video_url);
  const direct =
    (isDirectVideoUrl(ex?.video_url) ? mediaUrl(ex?.video_url) : null) ||
    (isDirectVideoUrl(ex?.gif_url) ? gifUrl(ex?.gif_url) || mediaUrl(ex?.gif_url) : null);

  useEffect(() => {
    setPlayYt(false);
  }, [ex?.id]);

  if (yt && playYt) {
    return (
      <div className="aspect-video w-full overflow-hidden rounded-xl bg-black">
        <iframe
          title={title}
          src={`${yt}${yt.includes("?") ? "&" : "?"}autoplay=1`}
          className="h-full w-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }

  if (direct) {
    return (
      <video
        src={direct}
        muted
        playsInline
        loop
        autoPlay
        controls
        className="aspect-video w-full rounded-xl bg-black object-contain"
      />
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl">
      <ExerciseThumb
        gif={ex?.gif_url}
        image={ex?.image_url}
        video={ex?.video_url}
        bodyPart={ex?.body_part || ""}
        className="aspect-video w-full"
        emojiSize="text-5xl"
        alt={title}
      />
      {yt ? (
        <button
          type="button"
          onClick={() => setPlayYt(true)}
          className="absolute inset-0 grid place-items-center bg-slate-900/25"
          aria-label={`Xem video ${title}`}
        >
          <span className="grid h-12 w-12 place-items-center rounded-full bg-white text-lg font-bold text-brand-600 shadow">
            ▶
          </span>
        </button>
      ) : null}
    </div>
  );
}

function sanitizeIntegerInput(raw: string, maxDigits = 4): string {
  return raw.replace(/[^\d]/g, "").slice(0, maxDigits);
}

function sanitizeKgInput(raw: string): string {
  const v = raw.replace(/,/g, ".").replace(/[^\d.]/g, "");
  const dot = v.indexOf(".");
  if (dot === -1) return v.slice(0, 3);
  const whole = v.slice(0, dot).slice(0, 3);
  const frac = v
    .slice(dot + 1)
    .replace(/\./g, "")
    .slice(0, 2);
  return frac.length > 0 || v.endsWith(".") ? `${whole}.${frac}` : whole;
}

function TestInputs({
  spec,
  values,
  onChange,
}: {
  spec: ChallengeTestMediaSpec;
  values: ChallengeTestDraft;
  onChange: (patch: Partial<ChallengeTestDraft>) => void;
}) {
  return (
    <>
      <label className="block text-sm font-semibold text-slate-600" htmlFor={`kit-test-${spec.id}`}>
        {spec.valueKind === "seconds" ? "Thời gian tối đa" : "Số cái tối đa"}
        <span className="mt-1 flex items-center gap-2">
          <input
            id={`kit-test-${spec.id}`}
            className="field bg-white"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            value={values[spec.repsField]}
            required
            onChange={(event) =>
              onChange({ [spec.repsField]: sanitizeIntegerInput(event.target.value) })
            }
          />
          <span className="w-12 shrink-0 text-xs font-normal text-slate-400">{spec.unit}</span>
        </span>
      </label>
      {spec.valueKind === "reps_kg" && spec.kgField ? (
        <label className="block text-sm font-semibold text-slate-600" htmlFor={`kit-test-${spec.id}-kg`}>
          Kg đang dùng
          <span className="mt-1 flex items-center gap-2">
            <input
              id={`kit-test-${spec.id}-kg`}
              className="field bg-white"
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={values[spec.kgField]}
              required={!spec.kgOptional}
              onChange={(event) =>
                onChange({ [spec.kgField!]: sanitizeKgInput(event.target.value) })
              }
            />
            <span className="w-12 shrink-0 text-xs font-normal text-slate-400">kg</span>
          </span>
        </label>
      ) : null}
      {spec.showBandLevel ? (
        <label
          className="block text-sm font-semibold text-slate-600"
          htmlFor={`kit-test-${spec.id}-band-level`}
        >
          Mức dây (tuỳ chọn)
          <select
            id={`kit-test-${spec.id}-band-level`}
            className="field mt-1 bg-white"
            value={values.bandLevel}
            onChange={(event) => onChange({ bandLevel: event.target.value })}
          >
            {BAND_LEVEL_OPTS.map((opt) => (
              <option key={opt.value || "none"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
    </>
  );
}

function TestCard({
  spec,
  values,
  onChange,
  media,
}: {
  spec: ChallengeTestSpec;
  values: ChallengeTestDraft;
  onChange: (patch: Partial<ChallengeTestDraft>) => void;
  media: Partial<Record<string, ExerciseListItem | null>>;
}) {
  const hardN = Number(values[spec.repsField] || 0);
  const easyFilled = Boolean(spec.regression && values[spec.regression.repsField]?.trim());
  const [tab, setTab] = useState<"primary" | "regression">(
    hardN > 0 || !easyFilled ? "primary" : "regression",
  );
  const showRegression = Boolean(spec.regression);
  const active = tab === "regression" && spec.regression ? spec.regression : spec;
  const ex = media[active.id] ?? null;

  return (
    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      {showRegression ? (
        <div className="flex gap-1 border-b border-slate-100 bg-slate-50 p-1">
          <button
            type="button"
            onClick={() => setTab("primary")}
            className={`flex-1 rounded-xl px-3 py-2 text-sm font-bold ${
              tab === "primary" ? "bg-white text-brand-700 shadow-sm" : "text-slate-500"
            }`}
          >
            {spec.titleVi}
          </button>
          <button
            type="button"
            onClick={() => setTab("regression")}
            className={`flex-1 rounded-xl px-3 py-2 text-sm font-bold ${
              tab === "regression" ? "bg-white text-brand-700 shadow-sm" : "text-slate-500"
            }`}
          >
            {spec.regression?.titleVi}
          </button>
        </div>
      ) : null}
      <TestMedia ex={ex} title={active.titleVi} />
      <div className="space-y-3 p-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900">{active.titleVi}</h3>
          {ex?.name_vi && ex.name_vi !== active.titleVi ? (
            <p className="mt-0.5 text-xs text-slate-400">{ex.name_vi}</p>
          ) : null}
          <p className="mt-1 text-xs leading-relaxed text-slate-500">{active.instructionVi}</p>
          {tab === "regression" && spec.regressionHintVi ? (
            <p className="mt-2 rounded-xl bg-brand-50 px-3 py-2 text-xs leading-relaxed text-brand-800">
              {spec.regressionHintVi}
            </p>
          ) : null}
        </div>
        <TestInputs spec={active} values={values} onChange={onChange} />
      </div>
    </article>
  );
}

export default function ChallengeFitnessCards({
  tests,
  values,
  onChange,
  hideIntro = false,
}: {
  tests: ChallengeTestSpec[];
  values: ChallengeTestDraft;
  onChange: (patch: Partial<ChallengeTestDraft>) => void;
  hideIntro?: boolean;
}) {
  const [media, setMedia] = useState<Partial<Record<string, ExerciseListItem | null>>>({});
  const mediaSpecs = challengeTestMediaSpecs(tests);
  const ids = mediaSpecs.map((t) => t.id).join("|");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next: Partial<Record<string, ExerciseListItem | null>> = {};
      await Promise.all(
        mediaSpecs.map(async (spec) => {
          try {
            const data = await api.searchExercises({
              q: spec.catalogNameEn || spec.query,
              page: 1,
              page_size: 12,
            });
            let picked = pickChallengeExercise(data.items || [], spec);
            if (!picked && spec.extraQuery) {
              const extra = await api.searchExercises({
                q: spec.extraQuery,
                page: 1,
                page_size: 12,
              });
              picked = pickChallengeExercise(extra.items || [], spec);
            }
            next[spec.id] = picked;
          } catch {
            next[spec.id] = null;
          }
        }),
      );
      if (!cancelled) setMedia(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [ids]);

  return (
    <div className="space-y-4">
      {hideIntro ? null : (
        <div>
          <p className="text-sm font-semibold text-slate-600">Thể lực theo dụng cụ</p>
          <p className="mt-1 text-xs leading-relaxed text-slate-500">
            Bốn bài dưới đây khớp kit bạn đã chọn. Nhập đủ số cái (và kg nếu có) để TAPTOT chỉnh tạ
            và số cái trên lịch.
          </p>
        </div>
      )}
      {tests.map((spec) => (
        <TestCard
          key={spec.id}
          spec={spec}
          values={values}
          onChange={onChange}
          media={media}
        />
      ))}
    </div>
  );
}
