import { inclineFromFloorDeg } from "../math/geometry";
import type { ExerciseProgress, Point2D } from "../types";
import { CAMERA_CUE, PLANK_MAX_HIP_SAG, hipOffsetRatio, seenBody } from "./bodyGate";
import type { IExerciseDetector } from "./IExerciseDetector";

/** Shoulder–hip vs floor. A plank stays low without demanding a straight line. */
export const PLANK_MAX_INCLINE_DEG = 30;
/** Upper arm vs floor. A real plank props the shoulders up; lying flat is ~0°. */
export const PLANK_UPPER_ARM_MIN_DEG = 45;

export class PlankDetector implements IExerciseDetector {
  private holdSec = 0;
  private valid = false;
  private seen = false;
  private bodyAngle = 0;
  private holdStartedAt: number | null = null;
  private accumulatedMs = 0;

  constructor(private readonly now: () => number = () => Date.now()) {}

  process(landmarks: Point2D[]): void {
    const body = seenBody(landmarks);
    this.seen = body != null;
    if (!body) {
      this.pause();
      this.valid = false;
      return;
    }

    const { shoulder, elbow, hip, ankle } = body;
    const incline = inclineFromFloorDeg(shoulder, hip);
    const upperArm = inclineFromFloorDeg(shoulder, elbow);
    this.bodyAngle = incline;
    const low = incline < PLANK_MAX_INCLINE_DEG;
    const propped = upperArm >= PLANK_UPPER_ARM_MIN_DEG;
    const hipOk = hipOffsetRatio(shoulder, hip, ankle) <= PLANK_MAX_HIP_SAG;
    this.valid = low && propped && hipOk;

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
        : this.seen
          ? "Chống người lên, hông đừng võng sâu — không nằm áp sàn."
          : CAMERA_CUE,
      isValidForm: this.valid,
      currentAngle: this.bodyAngle || undefined,
      state: this.valid ? "HOLDING" : "FORM_BREAK",
    };
  }

  reset(): void {
    this.holdSec = 0;
    this.valid = false;
    this.seen = false;
    this.bodyAngle = 0;
    this.holdStartedAt = null;
    this.accumulatedMs = 0;
  }
}
