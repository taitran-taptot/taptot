/**
 * Consecutive frames required before a state change commits.
 * 2 frames ≈ 60ms at 30fps — filters a single jitter spike without forcing a slow hold.
 */
export const DEBOUNCE_FRAMES = 2;

export class FrameDebouncer<T extends string> {
  private pending: T | null = null;
  private hits = 0;

  constructor(private readonly frames = DEBOUNCE_FRAMES) {}

  push(next: T, current: T): T {
    if (next === current) {
      this.pending = null;
      this.hits = 0;
      return current;
    }
    if (this.pending === next) {
      this.hits += 1;
      if (this.hits >= this.frames) {
        this.pending = null;
        this.hits = 0;
        return next;
      }
      return current;
    }
    this.pending = next;
    this.hits = 1;
    return current;
  }

  reset(): void {
    this.pending = null;
    this.hits = 0;
  }
}
