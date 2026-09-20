import type { DetectorMode } from "../types";
import type { IExerciseDetector } from "./IExerciseDetector";
import { PlankDetector } from "./PlankDetector";
import { PullUpDetector } from "./PullUpDetector";
import { PushUpDetector } from "./PushUpDetector";
import { SquatDetector } from "./SquatDetector";

export type DetectorKind = "pushup" | "pullup" | "squat" | "plank";

export function createDetector(kind: DetectorKind, pullMode: DetectorMode = "reps"): IExerciseDetector {
  switch (kind) {
    case "pushup":
      return new PushUpDetector();
    case "pullup":
      return new PullUpDetector(pullMode);
    case "squat":
      return new SquatDetector();
    case "plank":
      return new PlankDetector();
  }
}
