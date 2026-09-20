import { playBeep } from "../audio/beep";
import { angleDeg } from "../math/geometry";
import { DEBOUNCE_FRAMES, FrameDebouncer } from "../pose/debounce";
import type { ExerciseProgress, Point2D } from "../types";
import type { IExerciseDetector } from "./IExerciseDetector";
import { requirePoints, sidePoints } from "./landmarksUtil";

/** Standing lockout at the knee (hip–knee–ankle). */
export const SQUAT_STANDING_KNEE_DEG = 155;
/** Near-parallel squat depth (or hip at/below knee on screen). */
export const SQUAT_DEPTH_KNEE_DEG = 105;

type SquatState = "STANDING" | "SQUATTING" | "UNKNOWN";

export class SquatDetector implements IExerciseDetector {
  private state: SquatState = "UNKNOWN";
  private count = 0;
  private angle = 0;
  private valid = false;
  private readonly debounce = new FrameDebouncer<SquatState>(DEBOUNCE_FRAMES);

  process(landmarks: Point2D[]): void {
    const { hip, knee, ankle } = sidePoints(landmarks);
    if (!requirePoints([hip, knee, ankle])) {
      this.valid = false;
      this.state = this.debounce.push("UNKNOWN", this.state);
      return;
    }

    this.angle = angleDeg(hip, knee, ankle);
    // Image Y grows downward: hip at or below the knee on screen means a deep squat.
    const hipAtOrBelowKnee = hip.y >= knee.y;
    const deep = this.angle <= SQUAT_DEPTH_KNEE_DEG || hipAtOrBelowKnee;
    const standing = this.angle > SQUAT_STANDING_KNEE_DEG && !hipAtOrBelowKnee;

    this.valid = true;
    let raw: SquatState = this.state === "UNKNOWN" ? (standing ? "STANDING" : "UNKNOWN") : this.state;
    if (deep) raw = "SQUATTING";
    else if (standing) raw = "STANDING";

    const prev = this.state;
    const next = this.debounce.push(raw, this.state);
    if (next === prev) return;

    if (next === "SQUATTING" && prev === "STANDING") {
      playBeep("depth");
    }
    if (next === "STANDING" && prev === "SQUATTING") {
      this.count += 1;
      playBeep("rep");
    }
    this.state = next;
  }

  getProgress(): ExerciseProgress {
    const status =
      this.state === "SQUATTING"
        ? "Đủ sâu — đứng thẳng lên để hoàn thành rep."
        : this.state === "STANDING"
          ? "Đứng thẳng. Hạ hông xuống ngang/thấp hơn gối."
          : "Đưa toàn thân vào khung hình.";
    return {
      count: this.count,
      statusText: status,
      isValidForm: this.valid,
      currentAngle: this.angle || undefined,
      state: this.state,
    };
  }

  reset(): void {
    this.state = "UNKNOWN";
    this.count = 0;
    this.angle = 0;
    this.valid = false;
    this.debounce.reset();
  }
}
