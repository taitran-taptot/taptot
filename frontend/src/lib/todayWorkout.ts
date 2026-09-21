import type { PlanDay, PlanDetail } from "./plansApi";
import { estimatePlanDayMinutes } from "./planLabels";

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function parseIsoDate(raw: string | null | undefined): Date | null {
  if (!raw) return null;
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return null;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

function trainingDays(days: PlanDay[]): PlanDay[] {
  return days.filter((d) => d.exercises.length > 0);
}

/** Buổi nên xem hôm nay: theo ngày bắt đầu lịch, không dựa lịch sử buổi tập. */
export function pickTodayDay(detail: PlanDetail): PlanDay | null {
  const days = trainingDays(detail.days);
  if (!days.length) return detail.days[0] ?? null;

  const start = parseIsoDate(detail.start_date);
  if (start) {
    const diff = Math.floor(
      (startOfDay(new Date()).getTime() - startOfDay(start).getTime()) / 86_400_000,
    );
    if (diff >= 0) {
      const calendarDay = detail.days.find((d) => d.day_number === diff + 1);
      if (calendarDay?.split_role?.trim().toLowerCase() === "test") {
        return calendarDay;
      }
      const idx = Math.min(diff, days.length - 1);
      return days[idx];
    }
  }

  return days[0];
}

export function todaySessionMeta(day: PlanDay) {
  const minutes = estimatePlanDayMinutes(day.exercises);
  return {
    title: day.title_vi || "Buổi tập hôm nay",
    exerciseCount: day.exercises.length,
    minutes,
    mealCount: day.meals.length,
  };
}

export const KHO_HREFS = [
  "/tai-khoan/kho",
  "/tai-khoan/bai-tap",
  "/tai-khoan/mua-dung-cu",
  "/tai-khoan/thuc-an",
  "/tai-khoan/cach-nau",
  "/tai-khoan/kien-thuc",
  "/tai-khoan/may-tinh-calo",
  "/tai-khoan/tao-lich-tap",
  "/tai-khoan/batdau",
];

export const HOSO_HREFS = ["/tai-khoan/ho-so", "/tai-khoan/doi-mat-khau"];

export function pathStartsWithAny(pathname: string, hrefs: string[]): boolean {
  return hrefs.some((h) => pathname === h || pathname.startsWith(`${h}/`));
}
