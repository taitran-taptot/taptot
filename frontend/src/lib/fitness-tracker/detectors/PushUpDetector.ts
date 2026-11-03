import { playBeep } from "../audio/beep";
import { angleDeg, inclineFromFloorDeg } from "../math/geometry";
import { DEBOUNCE_FRAMES, FrameDebouncer } from "../pose/debounce";
import type { ExerciseProgress, Point2D } from "../types";
import { CAMERA_CUE, seenBody } from "./bodyGate";
import type { IExerciseDetector } from "./IExerciseDetector";

/** Standing is ~90°. Allow a slightly higher hip and an off-axis camera. */
export const PUSHUP_MAX_TORSO_INCLINE_DEG = 60;
/** Clear standing — drop an unfinished rep rather than count a sit-up. */
export const PUSHUP_STANDING_INCLINE_DEG = 70;
/** Top of the rep: arms mostly open; lockout to 180° is not required. */
export const PUSHUP_UP_ELBOW_DEG = 145;
/** Bottom: a modest dip, not chest-to-floor (~90°). */
export const PUSHUP_DOWN_ELBOW_DEG = 125;
/** Fast reps can be ~3/s; still ignores pose jitter. */
export const PUSHUP_MIN_REP_MS = 250;
/** Shoulder must travel down by this fraction of the torso. A small real dip still counts. */
export const PUSHUP_MIN_SHOULDER_DROP = 0.06;
/** Hip has to drop with the shoulder, not stay parked. */
export const PUSHUP_MIN_HIP_DROP = 0.03;

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
  private depthOk = false;
  private upShoulder: Point2D | null = null;
  private upHip: Point2D | null = null;
  /** Off during the prep countdown so those reps never enter the score. */
  private counting = true;
  private readonly debounce = new FrameDebouncer<PushState>(DEBOUNCE_FRAMES);

  /** Turn scoring on or off. Turning it on clears the count for the scored minute. */
  setCounting(on: boolean): void {
    this.counting = on;
    if (on) {
      this.count = 0;
      this.lastRepAt = Number.NEGATIVE_INFINITY;
      this.armed = false;
    }
  }

  constructor(private readonly now: () => number = defaultNow) {}

  process(landmarks: Point2D[]): void {
    const body = seenBody(landmarks);
    if (!body) {
      this.valid = false;
      this.armed = false;
      this.depthOk = false;
      this.upShoulder = null;
      this.upHip = null;
      this.state = this.debounce.push("OUT_OF_POSITION", this.state);
      return;
    }

    const { shoulder, elbow, wrist, hip } = body;
    const torsoIncline = inclineFromFloorDeg(shoulder, hip);
    this.angle = angleDeg(shoulder, elbow, wrist);

    if (torsoIncline > PUSHUP_STANDING_INCLINE_DEG || torsoIncline > PUSHUP_MAX_TORSO_INCLINE_DEG) {
      this.valid = false;
      this.armed = false;
      this.depthOk = false;
      this.upShoulder = null;
      this.upHip = null;
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
      const torso = this.upShoulder && this.upHip
        ? Math.hypot(this.upShoulder.x - this.upHip.x, this.upShoulder.y - this.upHip.y)
        : 0;
      const shoulderDrop = this.upShoulder && torso > 1e-4 ? (shoulder.y - this.upShoulder.y) / torso : 0;
      const hipDrop = this.upHip && torso > 1e-4 ? (hip.y - this.upHip.y) / torso : 0;
      this.depthOk = shoulderDrop >= PUSHUP_MIN_SHOULDER_DROP && hipDrop >= PUSHUP_MIN_HIP_DROP;
      this.armed = this.depthOk;
      if (this.depthOk && prev === "UP") playBeep("depth");
    }
    if (next === "UP" && this.armed) {
      const at = this.now();
      if (this.counting && at - this.lastRepAt >= PUSHUP_MIN_REP_MS) {
        this.count += 1;
        this.lastRepAt = at;
        playBeep("rep");
      }
      this.armed = false;
    }
    if (next === "UP") {
      this.upShoulder = { x: shoulder.x, y: shoulder.y };
      this.upHip = { x: hip.x, y: hip.y };
      this.depthOk = false;
    }
    this.state = next;
  }

  getProgress(): ExerciseProgress {
    const status =
      this.state === "OUT_OF_POSITION"
        ? CAMERA_CUE
        : this.state === "DOWN"
          ? this.depthOk
            ? "Hạ vừa đủ — đẩy lên để hoàn thành cái."
            : "Hạ vai và hông cùng tay."
          : "Hạ ngực xuống, vai và hông cùng hạ.";
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
    this.depthOk = false;
    this.upShoulder = null;
    this.upHip = null;
    this.counting = true;
    this.debounce.reset();
  }
}
