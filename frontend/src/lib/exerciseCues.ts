import { formatRest } from "./planLabels";

export type ExerciseTechnique = "drop_set" | "super_set";

export type ExerciseCueFields = {
  rir?: number | null;
  rpe?: number | null;
  tempo?: string | null;
  technique?: string | null;
  superset_group?: number | null;
  set_prescriptions?: SetPrescriptionFields[] | null;
};

export type SetPrescriptionFields = {
  reps?: string | number | null;
  rest_seconds?: number | null;
  rir?: number | null;
  rpe?: number | null;
  tempo?: string | null;
  technique?: string | null;
  load_note_vi?: string | null;
};

function trimNum(n: number): string {
  return Number.isInteger(n) ? String(n) : String(n);
}

export function hasSetPrescriptions(ex: ExerciseCueFields): boolean {
  return Array.isArray(ex.set_prescriptions) && ex.set_prescriptions.length > 0;
}

export function formatExerciseCue(ex: ExerciseCueFields): string | null {
  const parts: string[] = [];
  if (ex.rpe != null && Number.isFinite(ex.rpe)) parts.push(`RPE ${trimNum(ex.rpe)}`);
  if (ex.rir != null && Number.isFinite(ex.rir)) parts.push(`RIR ${ex.rir}`);
  const tempo = (ex.tempo || "").trim();
  if (tempo) parts.push(`Tempo ${tempo}`);
  return parts.length ? parts.join(" · ") : null;
}

function formatSetRepsDose(reps: string | number | null | undefined): string {
  const raw = reps == null || reps === "" ? "" : String(reps).trim();
  if (!raw) return "—";
  const s = raw.toLowerCase();
  const minutes = s.match(/^(\d+)\s*(p|phút|phut|min|mins|m)$/i);
  if (minutes) return `${minutes[1]} phút`;
  const seconds = s.match(/^(\d+)\s*(s|sec|secs|giây|giay)$/i);
  if (seconds) return `${seconds[1]} giây`;
  if (/(lần|phút|giây)/i.test(raw)) return raw;
  return `${raw} lần`;
}

function formatLoadSuggestion(note: string | null | undefined): string | null {
  const s = (note || "").trim();
  if (!s) return null;
  const compact = s
    .replace(/\s*mỗi tay\s*/gi, "")
    .replace(/\s*tổng\s*/gi, "")
    .replace(/(\d)\s+kg\b/gi, "$1kg")
    .replace(/\s{2,}/g, " ")
    .trim();
  if (compact.toLowerCase().startsWith("gợi ý")) return compact;
  return `Gợi ý: ${compact}`;
}

export function formatSetPrescriptionLine(row: SetPrescriptionFields, index: number): string {
  const bits = [`Hiệp ${index + 1}`, formatSetRepsDose(row.reps)];
  const cue = formatExerciseCue(row);
  if (cue) bits.push(cue);
  const restSec = row.rest_seconds;
  if (restSec != null && restSec > 0) {
    const rest = formatRest(restSec);
    if (rest) bits.push(rest);
  }
  const load = formatLoadSuggestion(row.load_note_vi);
  if (load) bits.push(load);
  return bits.join(" · ");
}

/** One compact line: `3 Hiệp · 19-24 lần · nghỉ 1 phút 30 giây · Gợi ý: Dây đen · 30 lbs`. */
export function formatCollapsedSetPrescriptions(rows: SetPrescriptionFields[] | null | undefined): string | null {
  if (!rows?.length) return null;
  const n = rows.length;
  const repsRaw = rows.map((r) => (r.reps == null || r.reps === "" ? "" : String(r.reps).trim()));
  const uniqueReps = [...new Set(repsRaw.filter(Boolean))];
  const repsBit =
    uniqueReps.length <= 1
      ? formatSetRepsDose(uniqueReps[0] || rows[0]?.reps)
      : `${uniqueReps.join(" / ")} lần`;
  const bits = [`${n} Hiệp`, repsBit];
  const firstCue = formatExerciseCue(rows[0]);
  if (firstCue && rows.every((r) => formatExerciseCue(r) === firstCue)) bits.push(firstCue);
  const rests = rows.map((r) => r.rest_seconds ?? null);
  const rest0 = rests[0];
  if (rest0 != null && rest0 > 0 && rests.every((s) => s === rest0)) {
    const rest = formatRest(rest0);
    if (rest) bits.push(rest);
  }
  const loads = [
    ...new Set(
      rows
        .map((r) => formatLoadSuggestion(r.load_note_vi))
        .filter((s): s is string => Boolean(s)),
    ),
  ];
  if (loads.length === 1) bits.push(loads[0]);
  else if (loads.length > 1) bits.push(loads.join(" / "));
  return bits.join(" · ");
}

export function isDropsetExercise(ex: ExerciseCueFields): boolean {
  if (ex.technique === "drop_set") return true;
  return (ex.set_prescriptions || []).some((row) => row.technique === "drop_set");
}

export function shouldShowDropsetTitle(ex: ExerciseCueFields): boolean {
  if (ex.technique === "super_set") return false;
  return isDropsetExercise(ex);
}

export function formatSetPrescriptionsReps(rows: SetPrescriptionFields[] | null | undefined): string | null {
  if (!rows?.length) return null;
  const parts = rows.map((r) => (r.reps == null || r.reps === "" ? "—" : String(r.reps).trim()));
  return parts.join(" / ");
}

export function formatExerciseTechniqueLabel(technique?: string | null): string | null {
  if (technique === "drop_set") return "Dropset";
  if (technique === "super_set") return "Super set";
  return null;
}

export type ExerciseListBlock<T> =
  | { kind: "single"; exercise: T }
  | { kind: "dropset"; exercise: T }
  | { kind: "superset"; letter: string; exercises: T[] };

export function groupExercisesForDisplay<T extends ExerciseCueFields>(
  exercises: T[],
): ExerciseListBlock<T>[] {
  const blocks: ExerciseListBlock<T>[] = [];
  let pairIndex = 0;
  let i = 0;
  while (i < exercises.length) {
    const cur = exercises[i];
    const group = cur.superset_group;
    if (cur.technique === "super_set" && group != null) {
      const pair: T[] = [cur];
      let j = i + 1;
      while (
        j < exercises.length &&
        exercises[j].technique === "super_set" &&
        exercises[j].superset_group === group
      ) {
        pair.push(exercises[j]);
        j += 1;
      }
      if (pair.length >= 2) {
        const letter = String.fromCharCode(65 + (pairIndex % 26));
        pairIndex += 1;
        blocks.push({ kind: "superset", letter, exercises: pair.slice(0, 2) });
        for (const leftover of pair.slice(2)) {
          blocks.push({
            kind: shouldShowDropsetTitle(leftover) ? "dropset" : "single",
            exercise: leftover,
          });
        }
        i = j;
        continue;
      }
    }
    blocks.push({
      kind: shouldShowDropsetTitle(cur) ? "dropset" : "single",
      exercise: cur,
    });
    i += 1;
  }
  return blocks;
}

export function nextSupersetGroup(exercises: ExerciseCueFields[]): number {
  let max = 0;
  for (const ex of exercises) {
    if (ex.superset_group != null && ex.superset_group > max) max = ex.superset_group;
  }
  return max + 1;
}

export function supersetSlotLabel(
  exercises: ExerciseCueFields[],
  indexInSection: number,
): string | null {
  const blocks = groupExercisesForDisplay(exercises);
  let walked = 0;
  for (const block of blocks) {
    if (block.kind !== "superset") {
      if (walked === indexInSection) return null;
      walked += 1;
      continue;
    }
    for (let s = 0; s < block.exercises.length; s += 1) {
      if (walked === indexInSection) return `${block.letter}${s + 1}`;
      walked += 1;
    }
  }
  return null;
}
