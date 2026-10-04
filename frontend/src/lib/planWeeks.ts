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

export type MonthCluster = {
  key: string;
  month: number;
  weeks: WeekGroup[];
};

export const DAYS_PER_WEEK = 7;
export const WEEKS_PER_MONTH = 4;

export function formatWeekRange(weeks: number[]): string {
  if (!weeks.length) return "";
  if (weeks.length === 1) return `Tuần ${weeks[0]}`;
  return `Tuần ${weeks[0]}–${weeks[weeks.length - 1]}`;
}

export function monthOfWeek(week: number): number {
  return Math.max(1, Math.ceil(week / WEEKS_PER_MONTH));
}

/** Tuần 1–4 trong tháng (tuần toàn cục 5 → Tuần 1 của tháng 2). */
export function weekIndexInMonth(week: number): number {
  return ((Math.max(1, week) - 1) % WEEKS_PER_MONTH) + 1;
}

export function weekFromDayNumber(dayNumber: number): number {
  return Math.max(1, Math.ceil(dayNumber / DAYS_PER_WEEK));
}

export function weekGroupForDay(
  weekGroups: WeekGroup[],
  dayNumber: number,
): WeekGroup | undefined {
  return weekGroups.find((g) => g.days.some((d) => d.day_number === dayNumber));
}

/** Gom tuần thành tháng (4 tuần / tháng). */
export function clusterWeeksByMonth(weekGroups: WeekGroup[]): MonthCluster[] {
  const clusters: MonthCluster[] = [];
  for (const group of weekGroups) {
    const month = monthOfWeek(group.week);
    const last = clusters[clusters.length - 1];
    if (last && last.month === month) {
      last.weeks.push(group);
      continue;
    }
    clusters.push({
      key: `month-${month}`,
      month,
      weeks: [group],
    });
  }
  return clusters;
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

/** Coach-facing short label for home-foundation weeks (8–9 tuần / 2 giai đoạn). */
export function foundationWeekCoachLabel(week: number, isDeload = false): string {
  if (isDeload || week === 4 || week === 8) return "Nhẹ hơn";
  if (week <= 2) return "Làm quen";
  if (week === 3) return "Tăng nhẹ";
  if (week === 5) return "Tập chắc hơn";
  if (week === 6) return "Dày hơn";
  if (week === 7) return "Mạnh nhất";
  if (week === 9) return "Kiểm tra";
  return "";
}

/** One-line HLV banner for foundation challenge by week. */
export function foundationWeekCoachBlurb(week: number): { title: string; body: string } {
  if (week <= 2) {
    return {
      title: "Tháng đầu · làm quen với chính mình",
      body: "Mục tiêu tuần này bạn làm quen với các động tác cơ bản, hãy cảm nhận các nhóm cơ trên cơ thể hoạt động.",
    };
  }
  if (week === 3) {
    return {
      title: "Tăng nhẹ một nhịp",
      body: "Tuần này cường độ sẽ dày hơn chút. Tuy nhiên vẫn đừng ép sức đến kiệt, hãy nhận thấy mỏi đủ là ổn.",
    };
  }
  if (week === 4) {
    return {
      title: "Tuần nhẹ hơn có chủ đích",
      body: "Tuần này giảm cường độ không phải bạn tụt tiến bộ. Giống chạy marathon có đoạn đi bộ — để cơ thể kịp hồi phục.",
    };
  }
  if (week === 5) {
    return {
      title: "Sang tháng hai · tập chắc hơn",
      body: "Cùng khung lịch tháng trước, nhưng cường độ sẽ dày hơn một chút.",
    };
  }
  if (week === 6) {
    return {
      title: "Dày hơn một chút",
      body: "Hãy cố gắng giữ đều 3 buổi. Cảm giác buổi tập đỡ “lạ” hơn — đó là tín hiệu tốt rằng bạn đã làm quen. Tuần này hãy cố bung hết sức.",
    };
  }
  if (week === 7) {
    return {
      title: "Tuần mạnh nhất trong 8 tuần",
      body: "Tuần khó khăn nhất trong lộ trình. Tuần này không giữ sức, bạn hãy cố gắng hết sức để biết bản thân đến được đâu.",
    };
  }
  if (week === 8) {
    return {
      title: "Tuần nhẹ hơn có chủ đích",
      body: "Tuần này giảm cường độ vì 2 tuần vừa qua bạn đã rất cố gắng rồi.",
    };
  }
  return {
    title: "Kiểm tra thành quả",
    body: "Chúc mừng bạn đã hoàn thành khóa Nhập môn của TAPTOT. Hãy kiểm tra bản thân và cùng nhìn lại quãng đường đã đi nhé.",
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
    const sorted = [...days].sort((a, b) => a.day_number - b.day_number);
    for (const day of sorted) {
      const w = weekFromDayNumber(day.day_number);
      const list = buckets.get(w) || [];
      list.push(day);
      buckets.set(w, list);
    }
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
      days: [...groupDays].sort((a, b) => a.day_number - b.day_number),
    };
  });
}
