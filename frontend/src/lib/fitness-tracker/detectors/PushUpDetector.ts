import { playBeep } from "../audio/beep";
import { angleDeg, inclineFromFloorDeg } from "../math/geometry";
import { FrameDebouncer } from "../pose/debounce";
import type { ExerciseProgress, Point2D } from "../types";
import type { IExerciseDetector } from "./IExerciseDetector";
import { requirePoints, sidePoints } from "./landmarksUtil";

/** Standing is ~90°. Allow a bit of pike / off-axis camera in plank. */
export const PUSHUP_MAX_TORSO_INCLINE_DEG = 55;
/** Clear standing — drop an unfinished rep rather than count a sit-up. */
export const PUSHUP_STANDING_INCLINE_DEG = 70;
/**
 * Top of the rep: elbows need not lock out. Fast push-ups often peak ~135–145°
 * on a side camera; 150° was missing the up.
 */
export const PUSHUP_UP_ELBOW_DEG = 135;
/** Bottom: chest-near-floor. MediaPipe side view rarely reports a true 90°. */
export const PUSHUP_DOWN_ELBOW_DEG = 125;
/** Fast reps can be ~3/s; still ignores pose jitter. */
export const PUSHUP_MIN_REP_MS = 250;

type PushState = "OUT_OF_POSITION" | "UP" | "DOWN";

function defaultNow(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

export class PushUpDetector implements IExerciseDetector {
  private state: PushState = "OUT_OF_POSITION";
  private count = 0;
  private angle = 0;
  private valid = false;
  private lastRepAt = Number.NEGATIVE_INFINITY;
  /** True after a real bottom so the next UP counts even if pose flickered. */
  private armed = false;
  private readonly debounce = new FrameDebouncer<PushState>(1);

  constructor(private readonly now: () => number = defaultNow) {}

  process(landmarks: Point2D[]): void {
    const { shoulder, elbow, wrist, hip } = sidePoints(landmarks);
    if (!requirePoints([shoulder, elbow, wrist, hip])) {
      this.valid = false;
      this.state = this.debounce.push("OUT_OF_POSITION", this.state);
      return;
    }

    const torsoIncline = inclineFromFloorDeg(shoulder, hip);
    this.angle = angleDeg(shoulder, elbow, wrist);

    if (torsoIncline > PUSHUP_STANDING_INCLINE_DEG) {
      this.valid = false;
      this.armed = false;
      this.state = this.debounce.push("OUT_OF_POSITION", this.state);
      return;
    }

    if (torsoIncline > PUSHUP_MAX_TORSO_INCLINE_DEG) {
      this.valid = false;
      this.state = this.debounce.push("OUT_OF_POSITION", this.state);
      return;
    }

    this.valid = true;
    let raw: PushState = this.state === "OUT_OF_POSITION" ? "UP" : this.state;
    if (this.angle <= PUSHUP_DOWN_ELBOW_DEG) raw = "DOWN";
    else if (this.angle >= PUSHUP_UP_ELBOW_DEG) raw = "UP";

    const prev = this.state;
    const next = this.debounce.push(raw, this.state);
    if (next === prev) return;

    if (next === "DOWN") {
      this.armed = true;
      if (prev === "UP") playBeep("depth");
    }
    if (next === "UP" && this.armed) {
      const at = this.now();
      if (at - this.lastRepAt >= PUSHUP_MIN_REP_MS) {
        this.count += 1;
        this.lastRepAt = at;
        playBeep("rep");
      }
      this.armed = false;
    }
    this.state = next;
  }

  getProgress(): ExerciseProgress {
    const status =
      this.state === "OUT_OF_POSITION"
        ? "Ra khỏi tư thế plank — nằm sấp, thân thẳng."
        : this.state === "DOWN"
          ? "Xuống sâu — đẩy lên để hoàn thành rep."
          : "Giữ plank, hạ ngực xuống.";
    return {
      count: this.count,
      statusText: status,
      isValidForm: this.valid,
      currentAngle: this.angle || undefined,
      state: this.state,
    };
  }

  reset(): void {
    this.state = "OUT_OF_POSITION";
    this.count = 0;
    this.angle = 0;
    this.valid = false;
    this.lastRepAt = Number.NEGATIVE_INFINITY;
    this.armed = false;
    this.debounce.reset();
  }
}
