import type { Point2D } from "../types";

const EARTH_RADIUS_M = 6_371_000;

export function isVisible(point: Point2D | undefined, min = 0.45): point is Point2D {
  if (!point) return false;
  if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) return false;
  if (point.visibility == null) return true;
  return point.visibility >= min;
}

/** Interior angle at vertex `b` formed by points a–b–c, in degrees (0–180). */
export function angleDeg(a: Point2D, b: Point2D, c: Point2D): number {
  const abx = a.x - b.x;
  const aby = a.y - b.y;
  const cbx = c.x - b.x;
  const cby = c.y - b.y;
  const mag = Math.hypot(abx, aby) * Math.hypot(cbx, cby);
  if (mag < 1e-8) return 180;
  const cos = Math.min(1, Math.max(-1, (abx * cbx + aby * cby) / mag));
  return (Math.acos(cos) * 180) / Math.PI;
}

/**
 * Acute-ish incline of a body segment vs the floor (horizontal).
 * 0° = parallel to the floor (plank), 90° = standing upright.
 */
export function inclineFromFloorDeg(from: Point2D, to: Point2D): number {
  const dx = Math.abs(to.x - from.x);
  const dy = Math.abs(to.y - from.y);
  if (dx < 1e-8 && dy < 1e-8) return 0;
  return (Math.atan2(dy, dx) * 180) / Math.PI;
}

/** Mean of two landmarks; prefers the more visible side when one is missing. */
export function midpoint(a?: Point2D, b?: Point2D, minVis = 0.45): Point2D | null {
  const aOk = isVisible(a, minVis);
  const bOk = isVisible(b, minVis);
  if (aOk && bOk) {
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, visibility: Math.min(a.visibility ?? 1, b.visibility ?? 1) };
  }
  if (aOk) return a;
  if (bOk) return b;
  return null;
}

/** Great-circle distance in metres. */
export function haversineMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(a)));
}
