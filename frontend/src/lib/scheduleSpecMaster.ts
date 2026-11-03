/** Session duration chips for the gen-lịch wizard (Python spec remains the source of truth). */

export const DURATION_OPTS = [45, 60] as const;

export function snapSessionMinutes(minutes: number): 45 | 60 {
  const n = Number.isFinite(minutes) ? minutes : 60;
  const clamped = Math.max(45, Math.min(60, n));
  return DURATION_OPTS.reduce((best, bucket) =>
    Math.abs(bucket - clamped) < Math.abs(best - clamped) ? bucket : best,
  );
}
