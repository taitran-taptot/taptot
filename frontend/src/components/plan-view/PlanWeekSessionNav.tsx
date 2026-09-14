"use client";

import { splitRoleLabel } from "@/lib/planLabels";
import type { WeekGroup } from "@/lib/planWeeks";
import {
  clusterWeeksByPhase,
  formatWeekRange,
  foundationWeekCoachLabel,
  shouldGroupWeekNav,
} from "@/lib/planWeeks";

function sessionShortLabel(day: WeekGroup["days"][0], index: number): string {
  const role = splitRoleLabel(day.split_role);
  if (role) return role;
  const m = day.title_vi?.match(/Buổi\s+(\d+)/i);
  if (m) return `Buổi ${m[1]}`;
  return `Buổi ${index + 1}`;
}

function chipClass(active: boolean, compact = false): string {
  const size = compact ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-xs";
  return `shrink-0 rounded-full ${size} font-bold transition ${
    active
      ? "bg-brand-500 text-white shadow-soft"
      : "bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-brand-300"
  }`;
}

export default function PlanWeekSessionNav({
  weekGroups,
  activeWeek,
  activeDayNumber,
  onWeekChange,
  onDayChange,
  homeFoundation = false,
}: {
  weekGroups: WeekGroup[];
  activeWeek: number;
  activeDayNumber: number;
  onWeekChange: (week: number, firstDayNumber: number) => void;
  onDayChange: (dayNumber: number) => void;
  homeFoundation?: boolean;
}) {
  const activeGroup = weekGroups.find((g) => g.week === activeWeek) ?? weekGroups[0];
  if (!activeGroup) return null;

  const grouped = shouldGroupWeekNav(weekGroups);
  const clusters = grouped ? clusterWeeksByPhase(weekGroups) : [];
  const activeCluster =
    clusters.find((c) => c.weeks.some((w) => w.week === activeWeek)) ?? clusters[0];
  const showPhaseRow = clusters.length > 1;
  const weekChips = grouped && activeCluster ? activeCluster.weeks : weekGroups;
  const showWeekLegend =
    weekChips.some((g) => g.isDeload || g.isRepeatOfWeek1) && weekGroups.length > 1;

  function selectWeek(group: WeekGroup) {
    const first = group.days[0]?.day_number;
    if (first != null) onWeekChange(group.week, first);
  }

  function selectCluster(cluster: (typeof clusters)[number]) {
    if (cluster.weeks.some((w) => w.week === activeWeek)) return;
    const first = cluster.weeks[0];
    if (first) selectWeek(first);
  }

  function weekChipLabel(g: WeekGroup, compact: boolean): string {
    if (homeFoundation) {
      const coach = foundationWeekCoachLabel(g.week, g.isDeload);
      if (compact) {
        return coach ? `${g.week} · ${coach}` : `${g.week}`;
      }
      return coach ? `Tuần ${g.week} · ${coach}` : `Tuần ${g.week}`;
    }
    if (compact) {
      return `${g.week}${g.isDeload ? " · Nhẹ" : g.isRepeatOfWeek1 ? " · Lặp" : ""}`;
    }
    return `Tuần ${g.week}${g.phase != null ? ` · Pha ${g.phase}` : ""}${g.isDeload ? " · Nhẹ" : ""}`;
  }

  return (
    <div className="space-y-2">
      {weekGroups.length > 1 && (
        <div className="space-y-1.5">
          {showPhaseRow && (
            <div
              className="flex gap-1.5 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
              aria-label={homeFoundation ? "Chọn giai đoạn" : "Chọn pha"}
            >
              {clusters.map((cluster) => {
                const active = cluster === activeCluster;
                const nums = cluster.weeks.map((w) => w.week);
                const phaseWord = homeFoundation ? "Giai đoạn" : "Pha";
                return (
                  <button
                    key={cluster.key}
                    type="button"
                    onClick={() => selectCluster(cluster)}
                    className={chipClass(active)}
                  >
                    {cluster.phase != null
                      ? `${phaseWord} ${cluster.phase}`
                      : formatWeekRange(nums)}
                    {cluster.phase != null && nums.length > 1
                      ? ` · ${formatWeekRange(nums)}`
                      : ""}
                  </button>
                );
              })}
            </div>
          )}

          <div
            className="flex gap-1.5 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            aria-label="Chọn tuần"
          >
            {weekChips.map((g) => {
              const compact = grouped;
              const label = weekChipLabel(g, compact);
              const coach = homeFoundation
                ? foundationWeekCoachLabel(g.week, g.isDeload)
                : "";
              return (
                <button
                  key={g.week}
                  type="button"
                  onClick={() => selectWeek(g)}
                  title={
                    g.isDeload
                      ? homeFoundation
                        ? "Tuần nhẹ hơn có chủ đích để cơ thể kịp theo"
                        : "Tuần tập nhẹ hơn để cơ thể hồi"
                      : g.isRepeatOfWeek1
                        ? "Lặp lại bài giống tuần mẫu của pha này"
                        : coach || undefined
                  }
                  aria-label={label}
                  className={chipClass(activeWeek === g.week, compact)}
                >
                  {compact && homeFoundation ? (
                    <>
                      <span className="font-extrabold">{g.week}</span>
                      {coach ? ` · ${coach}` : ""}
                    </>
                  ) : compact ? (
                    <>
                      <span className="font-extrabold">{g.week}</span>
                      {g.isDeload ? " · Nhẹ" : g.isRepeatOfWeek1 ? " · Lặp" : ""}
                    </>
                  ) : (
                    label
                  )}
                </button>
              );
            })}
          </div>

          {showWeekLegend && (
            <p className="text-[11px] leading-snug text-slate-500">
              {homeFoundation ? (
                <>
                  <span className="font-semibold text-slate-600">Nhẹ hơn</span> = giảm tải có chủ
                  đích · Tháng 1 làm quen · Tháng 2 tập chắc hơn
                </>
              ) : (
                <>
                  <span className="font-semibold text-slate-600">Lặp</span> = cùng bài tuần mẫu ·{" "}
                  <span className="font-semibold text-slate-600">Nhẹ</span> = tuần giảm tải, tập
                  thoải mái
                </>
              )}
            </p>
          )}
        </div>
      )}

      <div
        className="flex gap-1.5 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        aria-label="Chọn buổi tập"
      >
        {activeGroup.days.map((day, i) => {
          const active = day.day_number === activeDayNumber;
          return (
            <button
              key={day.id}
              type="button"
              onClick={() => onDayChange(day.day_number)}
              className={`shrink-0 rounded-xl px-3 py-2 text-left text-xs font-semibold transition ${
                active
                  ? "bg-brand-50 text-brand-800 ring-2 ring-brand-400"
                  : "bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-brand-200"
              }`}
            >
              <span className="block">{sessionShortLabel(day, i)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
