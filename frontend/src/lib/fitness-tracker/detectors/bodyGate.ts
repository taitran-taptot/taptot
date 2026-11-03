import { angleDeg } from "../math/geometry";
import type { Point2D } from "../types";
import { LM, SIDE, type PoseSide } from "../pose/landmarks";
import { pickSide } from "./landmarksUtil";

/** Joints must sit inside the frame, not on the cropped edge. */
export const FRAME_MARGIN = 0.04;
/** Challenge joints below this are treated as unseen. Visibility 0 does not count. */
export const BODY_MIN_VIS = 0.5;
/** A folded knee is a kneel. A slightly soft leg still passes. */
export const BODY_MIN_KNEE_DEG = 150;
/** Shoulder–ankle must clearly extend past the torso, so the legs are in frame. */
export const BODY_MIN_LEG_SPAN = 1.6;
/** In profile the two shoulders sit closer than this fraction of the torso length. */
export const BODY_MAX_SHOULDER_SPAN = 0.75;
/** Hip may leave the shoulder–ankle line by this fraction of the torso. */
export const PLANK_MAX_HIP_SAG = 0.2;

export const CAMERA_CUE = "Đưa cả người vào khung, quay nghiêng.";

export function inFrame(point: Point2D | undefined): point is Point2D {
  if (!point) return false;
  if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) return false;
  if (point.visibility == null || point.visibility < BODY_MIN_VIS) return false;
  const edge = FRAME_MARGIN;
  return point.x >= edge && point.x <= 1 - edge && point.y >= edge && point.y <= 1 - edge;
}

export function isSideOn(left: Point2D, right: Point2D, shoulder: Point2D, hip: Point2D): boolean {
  const span = Math.hypot(left.x - right.x, left.y - right.y);
  const torso = Math.hypot(shoulder.x - hip.x, shoulder.y - hip.y);
  if (torso < 0.05) return false;
  return span < torso * BODY_MAX_SHOULDER_SPAN;
}

export function legExtended(shoulder: Point2D, hip: Point2D, knee: Point2D, ankle: Point2D): boolean {
  const torso = Math.hypot(shoulder.x - hip.x, shoulder.y - hip.y);
  const reach = Math.hypot(shoulder.x - ankle.x, shoulder.y - ankle.y);
  if (torso < 1e-4) return false;
  return angleDeg(hip, knee, ankle) >= BODY_MIN_KNEE_DEG && reach >= torso * BODY_MIN_LEG_SPAN;
}

/** Perpendicular distance of the hip from the shoulder–ankle line, divided by torso length. */
export function hipOffsetRatio(shoulder: Point2D, hip: Point2D, ankle: Point2D): number {
  const abx = ankle.x - shoulder.x;
  const aby = ankle.y - shoulder.y;
  const span = Math.hypot(abx, aby);
  const torso = Math.hypot(hip.x - shoulder.x, hip.y - shoulder.y);
  if (span < 1e-4 || torso < 1e-4) return Number.POSITIVE_INFINITY;
  const cross = Math.abs((hip.x - shoulder.x) * aby - (hip.y - shoulder.y) * abx);
  return cross / span / torso;
}

export type SeenBody = {
  side: PoseSide;
  ear: Point2D;
  shoulder: Point2D;
  elbow: Point2D;
  wrist: Point2D;
  hip: Point2D;
  knee: Point2D;
  ankle: Point2D;
};

/** Side view of one full body: ear through ankle, inside the frame, leg extended. */
export function seenBody(landmarks: Point2D[]): SeenBody | null {
  const side = pickSide(landmarks);
  const joints = SIDE[side];
  const ear = landmarks[side === "left" ? LM.LEFT_EAR : LM.RIGHT_EAR];
  const shoulder = landmarks[joints.shoulder];
  const elbow = landmarks[joints.elbow];
  const wrist = landmarks[joints.wrist];
  const hip = landmarks[joints.hip];
  const knee = landmarks[joints.knee];
  const ankle = landmarks[joints.ankle];
  const leftShoulder = landmarks[LM.LEFT_SHOULDER];
  const rightShoulder = landmarks[LM.RIGHT_SHOULDER];
  if (!inFrame(ear) || !inFrame(shoulder) || !inFrame(elbow) || !inFrame(wrist)) return null;
  if (!inFrame(hip) || !inFrame(knee) || !inFrame(ankle)) return null;
  if (!inFrame(leftShoulder) || !inFrame(rightShoulder)) return null;
  if (!isSideOn(leftShoulder, rightShoulder, shoulder, hip)) return null;
  if (!legExtended(shoulder, hip, knee, ankle)) return null;
  return { side, ear, shoulder, elbow, wrist, hip, knee, ankle };
}
