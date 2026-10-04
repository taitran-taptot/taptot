"use client";

import type { PlanExercise } from "@/lib/plansApi";
import { formatRest, formatSetsReps, localizeWorkoutCopy } from "@/lib/planLabels";
import {
  formatExerciseCue,
  formatSetPrescriptionLine,
  groupExercisesForDisplay,
  hasSetPrescriptions,
} from "@/lib/exerciseCues";
import ExerciseThumb from "../ExerciseThumb";

function ExerciseRow({
  ex,
  slot,
  whyByExerciseId,
  showKnowledge,
  onSelect,
  foundation,
}: {
  ex: PlanExercise;
  slot?: string | null;
  whyByExerciseId?: Record<number, string>;
  showKnowledge?: boolean;
  onSelect: (ex: PlanExercise) => void;
  foundation?: boolean;
}) {
  const rest = formatRest(ex.rest_seconds);
  const whyRaw =
    showKnowledge && (whyByExerciseId?.[ex.exercise_id] || ex.notes_vi?.trim() || undefined);
  const why = whyRaw && foundation ? localizeWorkoutCopy(whyRaw) : whyRaw;
  const shortCueRaw =
    !showKnowledge && ex.notes_vi?.trim() && ex.notes_vi.trim().length <= 48
      ? ex.notes_vi.trim()
      : undefined;
  const shortCue = shortCueRaw && foundation ? localizeWorkoutCopy(shortCueRaw) : shortCueRaw;
  const perSet = hasSetPrescriptions(ex);
  const cue = perSet ? null : formatExerciseCue(ex);

  return (
    <li className="flex items-center gap-2 rounded-xl bg-slate-50 p-2 ring-1 ring-slate-100/80">
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
            {slot && (
              <span className="rounded-md bg-violet-100 px-1.5 py-px text-[10px] font-bold text-violet-800">
                {slot}
              </span>
            )}
            <span className="text-sm font-medium leading-snug text-slate-900 [overflow-wrap:anywhere]">
              {foundation ? localizeWorkoutCopy(ex.name_vi) : ex.name_vi}
            </span>
          </span>
          {(why || shortCue) && (
            <span className="mt-0.5 line-clamp-2 block text-[11px] text-sky-800/90">
              {why || shortCue}
            </span>
          )}
          {cue && (
            <span className="mt-0.5 block text-[11px] font-medium text-slate-500">{cue}</span>
          )}
          {perSet ? (
            <span className="mt-0.5 block space-y-0.5">
              {ex.set_prescriptions!.map((row, i) => (
                <span key={`${ex.id}-s${i}`} className="block text-xs font-semibold text-brand-600">
                  {formatSetPrescriptionLine(row, i)}
                  {row.rest_seconds != null && row.rest_seconds > 0 && (
                    <span className="font-normal text-slate-400">
                      {" "}
                      · {formatRest(row.rest_seconds)}
                    </span>
                  )}
                </span>
              ))}
            </span>
          ) : (
            <span className="mt-0.5 block text-xs font-semibold text-brand-600">
              {formatSetsReps(ex.sets, ex.reps, { foundation })}
              {rest && <span className="font-normal text-slate-400"> · {rest}</span>}
            </span>
          )}
        </span>
      </button>
    </li>
  );
}

export default function PlanExerciseList({
  exercises,
  section,
  whyByExerciseId,
  showKnowledge = false,
  onSelect,
  foundation = false,
}: {
  exercises: PlanExercise[];
  section?: string;
  whyByExerciseId?: Record<number, string>;
  showKnowledge?: boolean;
  onSelect: (ex: PlanExercise) => void;
  foundation?: boolean;
}) {
  if (!exercises.length) return null;
  const blocks = groupExercisesForDisplay(exercises);

  return (
    <ul className="space-y-1.5">
      {blocks.map((block) => {
        if (block.kind === "single" || block.kind === "dropset") {
          const row = (
            <ExerciseRow
              key={block.exercise.id}
              ex={block.exercise}
              whyByExerciseId={whyByExerciseId}
              showKnowledge={showKnowledge}
              onSelect={onSelect}
              foundation={foundation}
            />
          );
          if (block.kind === "single") return row;
          return (
            <li key={`ds-${block.exercise.id}`} className="space-y-1.5">
              <p className="px-1 text-[11px] font-bold uppercase tracking-wide text-amber-800">
                Dropset
              </p>
              <ul className="space-y-1.5 border-l-2 border-amber-200 pl-2">{row}</ul>
            </li>
          );
        }
        return (
          <li key={`ss-${block.letter}-${block.exercises[0].id}`} className="space-y-1.5">
            <p className="px-1 text-[11px] font-bold uppercase tracking-wide text-violet-700">
              Super set {block.letter}
            </p>
            <ul className="space-y-1.5 border-l-2 border-violet-200 pl-2">
              {block.exercises.map((ex, i) => (
                <ExerciseRow
                  key={ex.id}
                  ex={ex}
                  slot={`${block.letter}${i + 1}`}
                  whyByExerciseId={whyByExerciseId}
                  showKnowledge={showKnowledge}
                  onSelect={onSelect}
                  foundation={foundation}
                />
              ))}
            </ul>
          </li>
        );
      })}
    </ul>
  );
}
