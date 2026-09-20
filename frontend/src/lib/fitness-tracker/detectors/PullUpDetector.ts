import { playBeep } from "../audio/beep";
import { angleDeg, midpoint } from "../math/geometry";
import { DEBOUNCE_FRAMES, FrameDebouncer } from "../pose/debounce";
import { LM } from "../pose/landmarks";
import type { DetectorMode, ExerciseProgress, Point2D } from "../types";
import type { IExerciseDetector } from "./IExerciseDetector";
import { requirePoints, sidePoints } from "./landmarksUtil";

/** Dead-hang lockout: wrist–elbow–shoulder nearly straight. */
export const PULLUP_HANG_ARM_DEG = 150;
/** Chin-over-bar proxy: elbow closing toward the bar. */
export const PULLUP_PULL_ELBOW_DEG = 85;

type PullState = "HANG" | "PULL" | "UNKNOWN";

export class PullUpDetector implements IExerciseDetector {
  private state: PullState = "UNKNOWN";
  private count = 0;
  private holdSec = 0;
  private angle = 0;
  private valid = false;
  private holdStartedAt: number | null = null;
  private accumulatedMs = 0;
  private readonly debounce = new FrameDebouncer<PullState>(DEBOUNCE_FRAMES);

  constructor(
    private readonly mode: DetectorMode = "reps",
    private readonly now: () => number = () => Date.now(),
  ) {}

  process(landmarks: Point2D[]): void {
    const { shoulder, elbow, wrist } = sidePoints(landmarks);
    if (!requirePoints([shoulder, elbow, wrist])) {
      this.valid = false;
      this.pauseHold();
      this.state = this.debounce.push("UNKNOWN", this.state);
      return;
    }

    // Angle at the elbow along wrist–elbow–shoulder (arm extension).
    this.angle = angleDeg(wrist, elbow, shoulder);
    const face = midpoint(landmarks[LM.MOUTH_LEFT], landmarks[LM.MOUTH_RIGHT]) ?? landmarks[LM.NOSE];
    const chinAboveBar = face ? face.y < wrist.y : false;
    const pulling = this.angle < PULLUP_PULL_ELBOW_DEG || chinAboveBar;
    const hanging = this.angle > PULLUP_HANG_ARM_DEG;
    // Wrists should sit above the shoulders on screen when hanging from a bar.
    const wristsHigh = wrist.y < shoulder.y - 0.02;

    this.valid = hanging || pulling;

    if (this.mode === "hang") {
      if (hanging && wristsHigh) this.tickHold();
      else this.pauseHold();
      this.state = hanging && wristsHigh ? "HANG" : "UNKNOWN";
      return;
    }

    let raw: PullState = this.state === "UNKNOWN" ? (hanging ? "HANG" : "UNKNOWN") : this.state;
    if (pulling) raw = "PULL";
    else if (hanging) raw = "HANG";

    const prev = this.state;
    const next = this.debounce.push(raw, this.state);
    if (next !== prev) {
      if (next === "PULL" && prev === "HANG") playBeep("depth");
      if (next === "HANG" && prev === "PULL") {
        this.count += 1;
        playBeep("rep");
      }
      this.state = next;
    }
  }

  private tickHold(): void {
    const t = this.now();
    if (this.holdStartedAt == null) this.holdStartedAt = t;
    this.holdSec = (this.accumulatedMs + (t - this.holdStartedAt)) / 1000;
  }

  private pauseHold(): void {
    if (this.holdStartedAt == null) return;
    this.accumulatedMs += this.now() - this.holdStartedAt;
    this.holdStartedAt = null;
    this.holdSec = this.accumulatedMs / 1000;
  }

  getProgress(): ExerciseProgress {
    if (this.mode === "hang") {
      return {
        durationSec: this.holdSec,
        statusText: this.state === "HANG" ? "Đang treo — giữ vai siết, tay duỗi." : "Nắm xà, duỗi tay, nhấc chân khỏi đất.",
        isValidForm: this.valid,
        currentAngle: this.angle || undefined,
        state: this.state,
      };
    }
    const status =
      this.state === "PULL"
        ? "Cằm đã qua xà — hạ chậm về treo."
        : this.state === "HANG"
          ? "Treo thẳng. Kéo cằm lên trên cổ tay."
          : "Đưa xà và toàn thân vào khung.";
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
    this.holdSec = 0;
    this.angle = 0;
    this.valid = false;
    this.holdStartedAt = null;
    this.accumulatedMs = 0;
    this.debounce.reset();
  }
}
