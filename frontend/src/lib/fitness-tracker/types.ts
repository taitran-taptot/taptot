/** Shared types for the client-side pose/GPS fitness tracker. */

export type Point2D = {
  x: number;
  y: number;
  z?: number;
  visibility?: number;
};

export type ExerciseProgress = {
  count?: number;
  durationSec?: number;
  statusText: string;
  isValidForm: boolean;
  currentAngle?: number;
  state?: string;
};

export type DetectorMode = "reps" | "hang";

export type BeepKind = "depth" | "rep";

export type ChallengeOfferKey =
  | "challenge_100"
  | "fitness_advanced"
  | "fitness_soldier"
  | "advanced_foundation";

export type GenderKey = "male" | "female";

export type StandardLevel = "basic" | "advanced";
