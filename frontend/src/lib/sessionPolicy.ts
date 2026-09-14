/** Mirrors api/app/services/workout_generation/session_policy.py for wizard UX. */

/** Thử thách 100 ngày khóa ở 14 tuần; lịch thường là 1 tháng (4 tuần). */
export const CHALLENGE_WEEKS = 14;

export function maxSessionsForLevel(level: number): number {
  if (level <= 1) return 5;
  return 6;
}
