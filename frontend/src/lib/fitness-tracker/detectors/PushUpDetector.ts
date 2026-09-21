import { playBeep } from "../audio/beep";
import { angleDeg, inclineFromFloorDeg } from "../math/geometry";
import { DEBOUNCE_FRAMES, FrameDebouncer } from "../pose/debounce";
import type { ExerciseProgress, Point2D } from "../types";
import type { IExerciseDetector } from "./IExerciseDetector";
import { requirePoints, sidePoints } from "./landmarksUtil";

/** Max torso incline vs floor while in plank. Standing (~90°) pauses counting. */
export const PUSHUP_MAX_TORSO_INCLINE_DEG = 40;
/** Lockout: shoulder–elbow–wrist nearly straight (not a hard 180). */
export const PUSHUP_UP_ELBOW_DEG = 150;
/** Bottom of the rep: elbow at or below 110° (chest-near-floor, not a full 90). */
export const PUSHUP_DOWN_ELBOW_DEG = 110;
/** Ignore UP→DOWN→UP cycles faster than this (filters pose jitter). */
export const PUSHUP_MIN_REP_MS = 400;

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
  private readonly debounce = new FrameDebouncer<PushState>(DEBOUNCE_FRAMES);

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

    if (torsoIncline > PUSHUP_MAX_TORSO_INCLINE_DEG) {
      this.valid = false;
      this.state = this.debounce.push("OUT_OF_POSITION", this.state);
      return;
    }

    this.valid = true;
    let raw: PushState = this.state === "OUT_OF_POSITION" ? "UP" : this.state;
    if (this.angle <= PUSHUP_DOWN_ELBOW_DEG) raw = "DOWN";
    else if (this.angle > PUSHUP_UP_ELBOW_DEG) raw = "UP";

    const prev = this.state;
    const next = this.debounce.push(raw, this.state);
    if (next === prev) return;

    if (next === "DOWN" && prev === "UP") {
      playBeep("depth");
    }
    if (next === "UP" && prev === "DOWN") {
      const at = this.now();
      if (at - this.lastRepAt >= PUSHUP_MIN_REP_MS) {
        this.count += 1;
        this.lastRepAt = at;
        playBeep("rep");
      }
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
    this.debounce.reset();
  }
}
