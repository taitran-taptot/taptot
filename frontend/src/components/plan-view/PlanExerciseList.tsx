"use client";

import type { PlanExercise } from "@/lib/plansApi";
import { formatRest, formatSetsReps } from "@/lib/planLabels";
import ExerciseThumb from "../ExerciseThumb";

const SECTION_BADGE: Partial<Record<string, string>> = {
  warmup: "Làm nóng",
  cooldown: "Giãn cơ",
};

export default function PlanExerciseList({
  exercises,
  section,
  whyByExerciseId,
  showKnowledge = false,
  canSwap = false,
  onSelect,
  onSwapClick,
}: {
  exercises: PlanExercise[];
  section?: string;
  whyByExerciseId?: Record<number, string>;
  showKnowledge?: boolean;
  canSwap?: boolean;
  onSelect: (ex: PlanExercise) => void;
  onSwapClick?: (ex: PlanExercise) => void;
}) {
  if (!exercises.length) return null;
  const badge = section ? SECTION_BADGE[section] : undefined;

  return (
    <ul className="space-y-1.5">
      {exercises.map((ex) => {
        const rest = formatRest(ex.rest_seconds);
        const why =
          showKnowledge &&
          (whyByExerciseId?.[ex.exercise_id] || ex.notes_vi?.trim() || undefined);
        // When knowledge is off, keep cue short from notes only if very short.
        const shortCue =
          !showKnowledge && ex.notes_vi?.trim() && ex.notes_vi.trim().length <= 48
            ? ex.notes_vi.trim()
            : undefined;

        return (
          <li
            key={ex.id}
            className="flex items-center gap-2 rounded-xl bg-slate-50 p-2 ring-1 ring-slate-100/80"
          >
            <button
              type="button"
              onClick={() => onSelect(ex)}
              className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
            >
              <ExerciseThumb
                gif={ex.gif_url || ex.image_url}
                bodyPart={ex.body_part || ""}
                className="h-11 w-11 shrink-0 rounded-lg"
                emojiSize="text-xl"
              />
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-1.5">
                  {badge && (
                    <span className="rounded-md bg-amber-100 px-1.5 py-px text-[10px] font-bold text-amber-800">
                      {badge}
                    </span>
                  )}
                  <span className="text-sm font-medium leading-snug text-slate-900 [overflow-wrap:anywhere]">
                    {ex.name_vi}
                  </span>
                </span>
                {(why || shortCue) && (
                  <span className="mt-0.5 line-clamp-2 block text-[11px] text-sky-800/90">
                    {why || shortCue}
                  </span>
                )}
                <span className="mt-0.5 block text-xs font-semibold text-brand-600">
                  {formatSetsReps(ex.sets, ex.reps)}
                  {rest && <span className="font-normal text-slate-400"> · {rest}</span>}
                </span>
              </span>
            </button>
            {canSwap && onSwapClick && (
              <button
                type="button"
                onClick={() => onSwapClick(ex)}
                className="chip-secondary shrink-0 px-2 text-[11px] font-semibold"
              >
                Thay
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
