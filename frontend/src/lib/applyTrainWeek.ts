import {
  clusterWeeksByMonth,
  monthOfWeek,
  weekGroupForDay,
  type WeekGroup,
} from "./planWeeks";

export type TrainApplyScope = "month" | "plan";

export const TRAIN_APPLY_SCOPE_LABEL: Record<TrainApplyScope, string> = {
  month: "Tháng này",
  plan: "Cả lịch",
};

export function trainApplyScopesForNav(weekGroups: WeekGroup[]): TrainApplyScope[] {
  if (weekGroups.length <= 1) return [];
  if (clusterWeeksByMonth(weekGroups).length <= 1) return ["plan"];
  return ["month", "plan"];
}

export function weeksForTrainApplyScope(opts: {
  weekGroups: WeekGroup[];
  currentDayNumber: number;
  scope: TrainApplyScope;
}): WeekGroup[] {
  if (opts.scope === "plan") return opts.weekGroups;
  const source = weekGroupForDay(opts.weekGroups, opts.currentDayNumber);
  if (!source) return [];
  const month = monthOfWeek(source.week);
  return opts.weekGroups.filter((g) => monthOfWeek(g.week) === month);
}

export function trainApplyTargetWeekCount(opts: {
  weekGroups: WeekGroup[];
  currentDayNumber: number;
  scope: TrainApplyScope;
}): number {
  const source = weekGroupForDay(opts.weekGroups, opts.currentDayNumber);
  if (!source) return 0;
  return weeksForTrainApplyScope(opts).filter((g) => g.week !== source.week).length;
}

export function applyWeekTraining<
  TEx,
  TDay extends {
    day_number: number;
    title_vi: string | null;
    exercises: TEx[];
  },
>(opts: {
  days: TDay[];
  weekGroups: WeekGroup[];
  sourceDayNumber: number;
  scope: TrainApplyScope;
  cloneExercise: (ex: TEx) => TEx;
}): TDay[] {
  const sourceWeek = weekGroupForDay(opts.weekGroups, opts.sourceDayNumber);
  if (!sourceWeek) return opts.days;

  const dayByNumber = new Map(opts.days.map((d) => [d.day_number, d]));
  const sourceDraftDays = [...sourceWeek.days]
    .sort((a, b) => a.day_number - b.day_number)
    .map((d) => dayByNumber.get(d.day_number))
    .filter((d): d is TDay => Boolean(d));

  const overwrite = new Map<number, TDay>();
  for (const week of weeksForTrainApplyScope({
    weekGroups: opts.weekGroups,
    currentDayNumber: opts.sourceDayNumber,
    scope: opts.scope,
  })) {
    if (week.week === sourceWeek.week) continue;
    const targetSorted = [...week.days].sort((a, b) => a.day_number - b.day_number);
    const n = Math.min(sourceDraftDays.length, targetSorted.length);
    for (let i = 0; i < n; i++) {
      const src = sourceDraftDays[i];
      const tgt = dayByNumber.get(targetSorted[i].day_number);
      if (!src || !tgt) continue;
      overwrite.set(tgt.day_number, {
        ...tgt,
        title_vi: src.title_vi,
        exercises: src.exercises.map(opts.cloneExercise),
      });
    }
  }

  if (!overwrite.size) return opts.days;
  return opts.days.map((d) => overwrite.get(d.day_number) ?? d);
}
