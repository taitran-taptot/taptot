"use client";

import { useEffect, useState } from "react";
import type { PlanExercise } from "@/lib/plansApi";
import type { ExerciseDetail } from "@/lib/types";
import { api } from "@/lib/api";
import { formatRest, formatSetsReps, localizeWorkoutCopy } from "@/lib/planLabels";
import { splitCoachLines } from "@/lib/exerciseCopy";
import { mediaUrl } from "@/lib/labels";
import { isDirectVideoUrl, youtubeEmbedUrl } from "@/lib/sharePlan";
import ExerciseThumb from "../ExerciseThumb";
import Modal from "../Modal";

export default function PlanExerciseDetailSheet({
  exercise,
  why,
  canSwap,
  foundation = false,
  onSwap,
  onClose,
}: {
  exercise: PlanExercise | null;
  why?: string;
  canSwap?: boolean;
  foundation?: boolean;
  onSwap?: () => void;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<ExerciseDetail | null>(null);

  useEffect(() => {
    if (!exercise?.exercise_id) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    api
      .getExercise(exercise.exercise_id)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch(() => {
        if (!cancelled) setDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [exercise?.exercise_id]);

  if (!exercise) return null;

  const displayName = foundation ? localizeWorkoutCopy(exercise.name_vi) : exercise.name_vi;
  const displayWhy = why && foundation ? localizeWorkoutCopy(why) : why;
  const rest = formatRest(exercise.rest_seconds);
  const media = exercise.gif_url || exercise.image_url || detail?.gif_url || detail?.image_url;
  const videoUrl = exercise.video_url || detail?.video_url;
  const yt = youtubeEmbedUrl(videoUrl);
  const videoSrc = isDirectVideoUrl(videoUrl) ? mediaUrl(videoUrl) : null;
  const steps =
    (detail?.instruction_steps_vi || exercise.instruction_steps_vi)?.filter(Boolean) ||
    (detail?.instruction_vi || exercise.instruction_vi ? [detail?.instruction_vi || exercise.instruction_vi!] : []);
  const muscles = [detail?.target_muscle || exercise.body_part, ...(detail?.secondary_muscles || [])]
    .filter(Boolean)
    .join(" · ");

  return (
    <Modal open={!!exercise} onClose={onClose} size="lg" lockScroll title={`Cách làm: ${displayName}`}>
      <div className="flex max-h-[92vh] flex-col">
        <div className="shrink-0 border-b border-slate-100 px-4 py-4 sm:px-5">
          <div className="flex items-start gap-3">
            <ExerciseThumb
              gif={exercise.gif_url || exercise.image_url}
              bodyPart={exercise.body_part || ""}
              className="h-14 w-14 shrink-0 rounded-xl"
              emojiSize="text-2xl"
              alt={displayName}
            />
            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-bold leading-snug text-slate-900 [overflow-wrap:anywhere]">
                {displayName}
              </h2>
              {muscles && (
                <p className="mt-0.5 text-sm font-medium text-brand-700">Nhóm cơ: {muscles}</p>
              )}
              <p className="mt-2 inline-flex rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-700 ring-1 ring-brand-100">
                {formatSetsReps(exercise.sets, exercise.reps, { foundation })}
                {rest && <span className="font-normal text-slate-500"> · {rest}</span>}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="min-h-11 shrink-0 rounded-xl px-3 text-sm font-semibold text-slate-600 hover:bg-slate-50"
            >
              Đóng
            </button>
          </div>
          {displayWhy && (
            <p className="mt-3 rounded-lg bg-sky-50 px-3 py-2 text-xs leading-relaxed text-sky-900">
              {displayWhy}
            </p>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-5">
          {yt ? (
            <div className="mb-4 aspect-video overflow-hidden rounded-xl bg-black">
              <iframe
                title={displayName}
                src={yt}
                className="h-full w-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          ) : videoSrc ? (
            <div className="mb-4 overflow-hidden rounded-xl bg-black">
              <video
                src={videoSrc}
                controls
                muted
                playsInline
                className="aspect-video w-full max-w-full object-contain"
              />
            </div>
          ) : media ? (
            <ExerciseThumb
              gif={exercise.gif_url || exercise.image_url || detail?.gif_url}
              image={detail?.image_url}
              bodyPart={exercise.body_part || ""}
              className="mb-4 h-48 w-full rounded-xl sm:h-56"
              emojiSize="text-5xl"
              alt={exercise.name_vi}
            />
          ) : null}

          <h3 className="text-sm font-extrabold text-slate-800">Cách thực hiện</h3>
          {steps.length > 0 ? (
            <ol className="mt-2 list-decimal space-y-1.5 pl-4 text-sm leading-relaxed text-slate-600 [overflow-wrap:anywhere]">
              {steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          ) : (
            <p className="mt-2 text-sm text-slate-400">Chưa có hướng dẫn chi tiết cho bài này.</p>
          )}

          {splitCoachLines(detail?.common_mistakes_vi).length > 0 && (
            <div className="mt-4 rounded-xl bg-amber-50 px-3 py-3">
              <h3 className="text-sm font-extrabold text-amber-900">Lỗi thường gặp</h3>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-sm leading-relaxed text-amber-950">
                {splitCoachLines(detail?.common_mistakes_vi).map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </div>
          )}
          {splitCoachLines(detail?.tips_vi).length > 0 && (
            <div className="mt-3 rounded-xl bg-slate-50 px-3 py-3">
              <h3 className="text-sm font-extrabold text-slate-800">Mẹo</h3>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-sm leading-relaxed text-slate-600">
                {splitCoachLines(detail?.tips_vi).map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {canSwap && onSwap && (
          <div className="shrink-0 border-t border-slate-100 p-4 sm:px-5">
            <button
              type="button"
              onClick={onSwap}
              className="flex min-h-[44px] w-full items-center justify-center rounded-xl bg-brand-500 text-sm font-bold text-white hover:bg-brand-600"
            >
              Bài thay thế
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}
