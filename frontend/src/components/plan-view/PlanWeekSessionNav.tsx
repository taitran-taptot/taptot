"use client";

import type { MonthCluster, WeekGroup } from "@/lib/planWeeks";
import {
  clusterWeeksByMonth,
  foundationWeekCoachLabel,
  weekGroupForDay,
  weekIndexInMonth,
} from "@/lib/planWeeks";
import { planDayNavLabel } from "@/lib/planLabels";

function chipClass(active: boolean): string {
  return `shrink-0 rounded-full px-3 py-1.5 text-xs font-bold transition ${
    active
      ? "bg-brand-500 text-white shadow-soft"
      : "bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-brand-300"
  }`;
}

const chipRowClass =
  "flex gap-1.5 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden";

function weekChipLabel(g: WeekGroup, plain: boolean): string {
  const n = weekIndexInMonth(g.week);
  if (!plain) {
    if (g.isDeload) return `Tuần ${n} · Nhẹ`;
    if (g.isRepeatOfWeek1) return `Tuần ${n} · Lặp`;
  }
  return `Tuần ${n}`;
}

export default function PlanWeekSessionNav({
  weekGroups,
  activeWeek,
  activeDayNumber,
  onWeekChange,
  onDayChange,
  homeFoundation = false,
  plainWeekLabels = false,
}: {
  weekGroups: WeekGroup[];
  activeWeek: number;
  activeDayNumber: number;
  onWeekChange: (week: number, firstDayNumber: number) => void;
  onDayChange: (dayNumber: number) => void;
  homeFoundation?: boolean;
  /** Lịch HLV thủ công: không hiện Lặp / Nhẹ. */
  plainWeekLabels?: boolean;
}) {
  const resolvedWeek =
    weekGroupForDay(weekGroups, activeDayNumber)?.week ?? activeWeek;
  const activeGroup =
    weekGroups.find((g) => g.week === resolvedWeek) ?? weekGroups[0];
  if (!activeGroup) return null;

  const months = clusterWeeksByMonth(weekGroups);
  const activeMonth =
    months.find((m) => m.weeks.some((w) => w.week === activeGroup.week)) ?? months[0];
  const showMonthRow = months.length > 1;
  const showWeekRow = weekGroups.length > 1;
  const weekChips = activeMonth?.weeks ?? weekGroups;
  const showWeekLegend =
    !plainWeekLabels &&
    weekChips.some((g) => g.isDeload || g.isRepeatOfWeek1) &&
    weekGroups.length > 1;

  function selectWeek(group: WeekGroup) {
    const firstTraining = group.days.find((d) => d.exercises.length > 0);
    const first = firstTraining?.day_number ?? group.days[0]?.day_number;
    if (first != null) onWeekChange(group.week, first);
  }

  function selectMonth(cluster: MonthCluster) {
    if (cluster.weeks.some((w) => w.week === activeGroup.week)) return;
    const first = cluster.weeks[0];
    if (first) selectWeek(first);
  }

  return (
    <div className="space-y-2">
      {(showMonthRow || showWeekRow) && (
        <div className="space-y-1.5">
          {showMonthRow && (
            <div className={chipRowClass} aria-label="Chọn tháng">
              {months.map((cluster) => (
                <button
                  key={cluster.key}
                  type="button"
                  onClick={() => selectMonth(cluster)}
                  className={chipClass(cluster === activeMonth)}
                >
                  {`Tháng ${cluster.month}`}
                </button>
              ))}
            </div>
          )}

          {showWeekRow && (
            <div className={chipRowClass} aria-label="Chọn tuần">
              {weekChips.map((g) => {
                const label = weekChipLabel(g, plainWeekLabels);
                const coach =
                  !plainWeekLabels && homeFoundation
                    ? foundationWeekCoachLabel(g.week, g.isDeload)
                    : "";
                return (
                  <button
                    key={g.week}
                    type="button"
                    onClick={() => selectWeek(g)}
                    title={
                      plainWeekLabels
                        ? undefined
                        : g.isDeload
                          ? homeFoundation
                            ? "Tuần nhẹ hơn có chủ đích để cơ thể kịp theo"
                            : "Tuần tập nhẹ hơn để cơ thể hồi"
                          : g.isRepeatOfWeek1
                            ? "Lặp lại bài giống tuần mẫu của pha này"
                            : coach || undefined
                    }
                    aria-label={label}
                    className={chipClass(activeGroup.week === g.week)}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          )}

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

      <div className={chipRowClass} aria-label="Chọn buổi trong tuần">
        {[...activeGroup.days]
          .sort((a, b) => a.day_number - b.day_number)
          .map((day, i) => {
          const active = day.day_number === activeDayNumber;
          const label = planDayNavLabel(day, i, {
            sequential: plainWeekLabels,
          });
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
              <span className="block">{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
