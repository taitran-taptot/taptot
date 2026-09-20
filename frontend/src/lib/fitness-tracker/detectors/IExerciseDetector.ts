import type { ExerciseProgress, Point2D } from "../types";

export interface IExerciseDetector {
  process(landmarks: Point2D[]): void;
  getProgress(): ExerciseProgress;
  reset(): void;
}
