import type { Point2D } from "../types";
import { isVisible } from "../math/geometry";
import { SIDE, type PoseSide } from "../pose/landmarks";

export function pickSide(landmarks: Point2D[]): PoseSide {
  const left = SIDE.left;
  const right = SIDE.right;
  const leftVis =
    (landmarks[left.shoulder]?.visibility ?? 0) +
    (landmarks[left.hip]?.visibility ?? 0) +
    (landmarks[left.elbow]?.visibility ?? 0);
  const rightVis =
    (landmarks[right.shoulder]?.visibility ?? 0) +
    (landmarks[right.hip]?.visibility ?? 0) +
    (landmarks[right.elbow]?.visibility ?? 0);
  return leftVis >= rightVis ? "left" : "right";
}

export function sidePoints(landmarks: Point2D[], side?: PoseSide) {
  const s = SIDE[side ?? pickSide(landmarks)];
  return {
    shoulder: landmarks[s.shoulder],
    elbow: landmarks[s.elbow],
    wrist: landmarks[s.wrist],
    hip: landmarks[s.hip],
    knee: landmarks[s.knee],
    ankle: landmarks[s.ankle],
  };
}

export function requirePoints(
  points: Array<Point2D | undefined>,
  minVis = 0.45,
): points is Point2D[] {
  return points.every((p) => isVisible(p, minVis));
}
