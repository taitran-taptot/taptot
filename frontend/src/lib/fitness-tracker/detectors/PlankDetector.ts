import { angleDeg, inclineFromFloorDeg } from "../math/geometry";
import type { ExerciseProgress, Point2D } from "../types";
import type { IExerciseDetector } from "./IExerciseDetector";
import { requirePoints, sidePoints } from "./landmarksUtil";

/** Shoulder–hip–ankle must stay in this band for a straight body line. */
export const PLANK_BODY_MIN_DEG = 155;
export const PLANK_BODY_MAX_DEG = 180;
/** Body line vs floor: under 20° counts as parallel. */
export const PLANK_MAX_INCLINE_DEG = 20;

export class PlankDetector implements IExerciseDetector {
  private holdSec = 0;
  private valid = false;
  private bodyAngle = 0;
  private holdStartedAt: number | null = null;
  private accumulatedMs = 0;

  constructor(private readonly now: () => number = () => Date.now()) {}

  process(landmarks: Point2D[]): void {
    const { shoulder, hip, ankle } = sidePoints(landmarks);
    if (!requirePoints([shoulder, hip, ankle])) {
      this.pause();
      this.valid = false;
      return;
    }

    this.bodyAngle = angleDeg(shoulder, hip, ankle);
    const incline = inclineFromFloorDeg(shoulder, hip);
    const straight = this.bodyAngle >= PLANK_BODY_MIN_DEG && this.bodyAngle <= PLANK_BODY_MAX_DEG;
    const parallel = incline < PLANK_MAX_INCLINE_DEG;
    this.valid = straight && parallel;

    if (this.valid) this.tick();
    else this.pause();
  }

  private tick(): void {
    const t = this.now();
    if (this.holdStartedAt == null) this.holdStartedAt = t;
    this.holdSec = (this.accumulatedMs + (t - this.holdStartedAt)) / 1000;
  }

  private pause(): void {
    if (this.holdStartedAt == null) return;
    this.accumulatedMs += this.now() - this.holdStartedAt;
    this.holdStartedAt = null;
    this.holdSec = this.accumulatedMs / 1000;
  }

  getProgress(): ExerciseProgress {
    return {
      durationSec: this.holdSec,
      statusText: this.valid
        ? "Form chuẩn — đang tích giây."
        : "Thân thẳng, hông không võng/gồ, song song sàn.",
      isValidForm: this.valid,
      currentAngle: this.bodyAngle || undefined,
      state: this.valid ? "HOLDING" : "FORM_BREAK",
    };
  }

  reset(): void {
    this.holdSec = 0;
    this.valid = false;
    this.bodyAngle = 0;
    this.holdStartedAt = null;
    this.accumulatedMs = 0;
  }
}
