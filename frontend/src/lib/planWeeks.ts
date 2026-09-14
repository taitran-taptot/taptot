import type { PlanDay } from "./plansApi";

export type WeekGroup = {
  week: number;
  phase: number | null;
  isDeload: boolean;
  isRepeatOfWeek1: boolean;
  days: PlanDay[];
};

export type PhaseCluster = {
  key: string;
  phase: number | null;
  weeks: WeekGroup[];
};

export function formatWeekRange(weeks: number[]): string {
  if (!weeks.length) return "";
  if (weeks.length === 1) return `Tuần ${weeks[0]}`;
  return `Tuần ${weeks[0]}–${weeks[weeks.length - 1]}`;
}

/** Gom tuần liên tiếp cùng pha (lịch mẫu / mesocycle). */
export function clusterWeeksByPhase(weekGroups: WeekGroup[]): PhaseCluster[] {
  const clusters: PhaseCluster[] = [];
  for (const group of weekGroups) {
    const last = clusters[clusters.length - 1];
    if (last && group.phase != null && last.phase === group.phase) {
      last.weeks.push(group);
      continue;
    }
    clusters.push({
      key: group.phase != null ? `phase-${group.phase}` : `week-${group.week}`,
      phase: group.phase,
      weeks: [group],
    });
  }
  return clusters;
}

/** Lịch mẫu có pha: gom nav thay vì một chip mỗi tuần. */
export function shouldGroupWeekNav(weekGroups: WeekGroup[]): boolean {
  if (weekGroups.length < 3) return false;
  return clusterWeeksByPhase(weekGroups).some((c) => c.phase != null && c.weeks.length >= 2);
}

function weekFromTitle(title: string | null | undefined): number | null {
  if (!title) return null;
  const m = title.match(/Tuần\s+(\d+)/i);
  return m ? Number(m[1]) : null;
}

function phaseFromTitle(title: string | null | undefined): number | null {
  if (!title) return null;
  const m = title.match(/(?:Pha|Giai đoạn)\s+(\d+)/i);
  return m ? Number(m[1]) : null;
}

function isDeloadTitle(title: string | null | undefined): boolean {
  return /deload|giảm nhẹ|nhẹ hơn/i.test(title || "");
}

/** Coach-facing short label for home-foundation weeks (8 tuần / 2 giai đoạn). */
export function foundationWeekCoachLabel(week: number, isDeload = false): string {
  if (isDeload || week === 4 || week === 8) return "Nhẹ hơn";
  if (week <= 2) return "Làm quen";
  if (week === 3) return "Tăng nhẹ";
  if (week === 5) return "Tập chắc hơn";
  if (week === 6) return "Dày hơn";
  if (week === 7) return "Mạnh nhất";
  return "";
}

/** One-line HLV banner for foundation challenge by week. */
export function foundationWeekCoachBlurb(week: number): { title: string; body: string } {
  if (week <= 2) {
    return {
      title: "Tháng đầu · làm quen với chính mình",
      body: "Ít lần một hiệp là đúng sức nền — không phải lịch yếu. Làm chắc form, thở được, xong buổi là thắng.",
    };
  }
  if (week === 3) {
    return {
      title: "Tăng nhẹ một nhịp",
      body: "Tuần này dày hơn chút. Vẫn đừng ép đến kiệt — gần mức cao của khoảng lần là đủ.",
    };
  }
  if (week === 4 || week === 8) {
    return {
      title: "Tuần nhẹ hơn có chủ đích",
      body: "Không phải bạn tụt tiến bộ. Giống chạy marathon có đoạn đi bộ — để cơ và đầu kịp theo rồi leo tiếp.",
    };
  }
  if (week === 5) {
    return {
      title: "Sang tháng hai · tập chắc hơn",
      body: "Cùng khung lịch, dày hơn một chút. Bài chưa cần khó hơn nếu tuần trước bạn mới làm vững.",
    };
  }
  if (week === 6) {
    return {
      title: "Dày hơn một chút",
      body: "Giữ đều 3 buổi. Cảm giác buổi tập đỡ “lạ” — đó là tín hiệu đẹp.",
    };
  }
  return {
    title: "Tuần mạnh nhất trong 8 tuần",
    body: "Đỉnh nhẹ của lộ trình. Làm sạch, nghỉ đủ — tuần sau sẽ nhẹ lại để nhìn lại mình đã đi được bao xa.",
  };
}

function dayFingerprint(day: PlanDay): string {
  return day.exercises
    .filter((e) => e.section === "main")
    .map((e) => `${e.exercise_id}:${e.sets}:${e.reps}:${e.rest_seconds}`)
    .join("|");
}

function weekFingerprint(days: PlanDay[]): string {
  return days.map(dayFingerprint).join(";;");
}

export function groupPlanDaysByWeek(days: PlanDay[]): WeekGroup[] {
  if (!days.length) return [];
  const titled = days.every((d) => weekFromTitle(d.title_vi) != null);
  const buckets = new Map<number, PlanDay[]>();
  if (titled) {
    for (const day of days) {
      const w = weekFromTitle(day.title_vi) ?? 1;
      const list = buckets.get(w) || [];
      list.push(day);
      buckets.set(w, list);
    }
  } else {
    buckets.set(1, [...days]);
  }

  const weeks = [...buckets.keys()].sort((a, b) => a - b);
  const templateFpByPhase = new Map<number, string>();
  const templateWeekByPhase = new Map<number, number>();
  let week1Fp = "";

  for (const week of weeks) {
    const groupDays = buckets.get(week) || [];
    const isDeload = groupDays.some((d) => isDeloadTitle(d.title_vi));
    if (isDeload) continue;
    const fp = weekFingerprint(groupDays);
    const phase = phaseFromTitle(groupDays[0]?.title_vi);
    if (phase != null && !templateFpByPhase.has(phase)) {
      templateFpByPhase.set(phase, fp);
      templateWeekByPhase.set(phase, week);
    }
    if (!week1Fp) week1Fp = fp;
  }

  return weeks.map((week) => {
    const groupDays = buckets.get(week) || [];
    const fp = weekFingerprint(groupDays);
    const isDeload = groupDays.some((d) => isDeloadTitle(d.title_vi));
    const phase = phaseFromTitle(groupDays[0]?.title_vi);
    const templateWeek =
      phase != null ? templateWeekByPhase.get(phase) : weeks[0];
    const templateFp =
      phase != null ? templateFpByPhase.get(phase) : week1Fp;
    return {
      week,
      phase,
      isDeload,
      isRepeatOfWeek1:
        week !== templateWeek && !isDeload && !!templateFp && fp === templateFp,
      days: groupDays,
    };
  });
}
