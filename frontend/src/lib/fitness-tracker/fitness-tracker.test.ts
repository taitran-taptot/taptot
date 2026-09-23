import { describe, expect, it } from "vitest";
import { angleDeg, haversineMeters, inclineFromFloorDeg } from "@/lib/fitness-tracker/math/geometry";
import { DEBOUNCE_FRAMES, FrameDebouncer } from "@/lib/fitness-tracker/pose/debounce";
import { PushUpDetector, PUSHUP_MIN_REP_MS } from "@/lib/fitness-tracker/detectors/PushUpDetector";
import { SquatDetector } from "@/lib/fitness-tracker/detectors/SquatDetector";
import { PullUpDetector } from "@/lib/fitness-tracker/detectors/PullUpDetector";
import { PlankDetector } from "@/lib/fitness-tracker/detectors/PlankDetector";
import { discountPercentForReps, parsePushupTicket, PUSHUP_PREP_SEC, PUSHUP_ROUND_MS, pushupRoundExpired } from "@/lib/fitness-tracker/session/discount";
import { buildProtocol, offerIncludesRun, offerStandardLevel, pullModeForGender } from "@/lib/fitness-tracker/session/protocol";
import { RunTracker } from "@/lib/fitness-tracker/gps/RunTracker";
import { LM } from "@/lib/fitness-tracker/pose/landmarks";
import type { Point2D } from "@/lib/fitness-tracker/types";

function pt(x: number, y: number, vis = 1): Point2D {
  return { x, y, visibility: vis };
}

function skeleton(patch: Partial<Record<number, Point2D>>): Point2D[] {
  const out: Point2D[] = Array.from({ length: 33 }, () => pt(0.5, 0.5, 0));
  for (const [key, value] of Object.entries(patch)) {
    if (!value) continue;
    out[Number(key)] = value;
  }
  return out;
}

function feed(detector: { process: (l: Point2D[]) => void }, pose: Point2D[], frames = 2): void {
  for (let i = 0; i < frames; i += 1) detector.process(pose);
}

const plankBody = {
  [LM.RIGHT_SHOULDER]: pt(0.25, 0.42),
  [LM.RIGHT_ELBOW]: pt(0.25, 0.58),
  [LM.RIGHT_WRIST]: pt(0.25, 0.74),
  [LM.RIGHT_HIP]: pt(0.62, 0.44),
  [LM.RIGHT_KNEE]: pt(0.78, 0.46),
  [LM.RIGHT_ANKLE]: pt(0.92, 0.48),
  [LM.LEFT_SHOULDER]: pt(0.25, 0.40),
  [LM.LEFT_ELBOW]: pt(0.25, 0.56),
  [LM.LEFT_WRIST]: pt(0.25, 0.72),
  [LM.LEFT_HIP]: pt(0.62, 0.42),
  [LM.LEFT_KNEE]: pt(0.78, 0.44),
  [LM.LEFT_ANKLE]: pt(0.92, 0.46),
};

describe("geometry", () => {
  it("computes a right angle at the vertex", () => {
    expect(angleDeg(pt(0, 1), pt(0, 0), pt(1, 0))).toBeCloseTo(90, 5);
  });

  it("treats a horizontal torso as ~0° incline", () => {
    expect(inclineFromFloorDeg(pt(0.2, 0.4), pt(0.8, 0.41))).toBeLessThan(5);
  });

  it("treats a standing torso as ~90° incline", () => {
    expect(inclineFromFloorDeg(pt(0.5, 0.2), pt(0.5, 0.8))).toBeCloseTo(90, 5);
  });

  it("haversine is 0 for identical points and ~111.2km per degree of latitude", () => {
    expect(haversineMeters(21, 105, 21, 105)).toBeCloseTo(0, 6);
    const oneDeg = haversineMeters(0, 0, 1, 0);
    expect(oneDeg).toBeGreaterThan(110_000);
    expect(oneDeg).toBeLessThan(112_000);
  });
});

describe("debounce", () => {
  it("needs 2 frames before flipping state", () => {
    const d = new FrameDebouncer<"A" | "B">(DEBOUNCE_FRAMES);
    expect(d.push("B", "A")).toBe("A");
    expect(d.push("B", "A")).toBe("B");
  });
});

describe("PushUpDetector", () => {
  it("counts a UP → DOWN → UP cycle and ignores standing", () => {
    const det = new PushUpDetector();
    const upElbow = { ...plankBody, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const downElbow = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.40),
    };
    const standing = {
      [LM.RIGHT_SHOULDER]: pt(0.5, 0.2),
      [LM.RIGHT_HIP]: pt(0.5, 0.55),
      [LM.RIGHT_ELBOW]: pt(0.5, 0.38),
      [LM.RIGHT_WRIST]: pt(0.5, 0.5),
      [LM.RIGHT_KNEE]: pt(0.5, 0.75),
      [LM.RIGHT_ANKLE]: pt(0.5, 0.9),
      [LM.LEFT_SHOULDER]: pt(0.48, 0.2),
      [LM.LEFT_HIP]: pt(0.48, 0.55),
      [LM.LEFT_ELBOW]: pt(0.48, 0.38),
      [LM.LEFT_WRIST]: pt(0.48, 0.5),
    };
    feed(det, skeleton(upElbow));
    expect(det.getProgress().state).toBe("UP");
    feed(det, skeleton(downElbow));
    expect(det.getProgress().state).toBe("DOWN");
    feed(det, skeleton(upElbow));
    expect(det.getProgress().count).toBe(1);
    feed(det, skeleton(standing));
    expect(det.getProgress().state).toBe("OUT_OF_POSITION");
  });

  it("ignores a second cycle faster than 0.4s", () => {
    let t = 0;
    const det = new PushUpDetector(() => t);
    const upElbow = { ...plankBody, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const downElbow = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.40),
    };
    const cycle = () => {
      feed(det, skeleton(upElbow));
      feed(det, skeleton(downElbow));
      feed(det, skeleton(upElbow));
    };
    cycle();
    expect(det.getProgress().count).toBe(1);
    t = PUSHUP_MIN_REP_MS - 1;
    cycle();
    expect(det.getProgress().count).toBe(1);
    t = PUSHUP_MIN_REP_MS;
    cycle();
    expect(det.getProgress().count).toBe(2);
  });
});

describe("SquatDetector", () => {
  it("counts standing → squat → standing", () => {
    const det = new SquatDetector();
    const stand = skeleton({
      [LM.RIGHT_HIP]: pt(0.5, 0.35),
      [LM.RIGHT_KNEE]: pt(0.5, 0.58),
      [LM.RIGHT_ANKLE]: pt(0.5, 0.82),
      [LM.RIGHT_SHOULDER]: pt(0.5, 0.15),
    });
    const squat = skeleton({
      [LM.RIGHT_HIP]: pt(0.55, 0.62),
      [LM.RIGHT_KNEE]: pt(0.5, 0.58),
      [LM.RIGHT_ANKLE]: pt(0.48, 0.82),
      [LM.RIGHT_SHOULDER]: pt(0.52, 0.32),
    });
    feed(det, stand);
    expect(det.getProgress().state).toBe("STANDING");
    feed(det, squat);
    expect(det.getProgress().state).toBe("SQUATTING");
    feed(det, stand);
    expect(det.getProgress().count).toBe(1);
  });
});

describe("PullUpDetector", () => {
  it("counts hang → pull → hang as one rep", () => {
    const det = new PullUpDetector("reps");
    const hang = skeleton({
      [LM.RIGHT_WRIST]: pt(0.5, 0.12),
      [LM.RIGHT_ELBOW]: pt(0.5, 0.28),
      [LM.RIGHT_SHOULDER]: pt(0.5, 0.44),
      [LM.MOUTH_LEFT]: pt(0.48, 0.22),
      [LM.MOUTH_RIGHT]: pt(0.52, 0.22),
    });
    const pull = skeleton({
      [LM.RIGHT_WRIST]: pt(0.5, 0.12),
      [LM.RIGHT_ELBOW]: pt(0.62, 0.22),
      [LM.RIGHT_SHOULDER]: pt(0.5, 0.28),
      [LM.MOUTH_LEFT]: pt(0.48, 0.08),
      [LM.MOUTH_RIGHT]: pt(0.52, 0.08),
    });
    feed(det, hang);
    expect(det.getProgress().state).toBe("HANG");
    feed(det, pull);
    expect(det.getProgress().state).toBe("PULL");
    feed(det, hang);
    expect(det.getProgress().count).toBe(1);
  });

  it("accumulates hang seconds in female mode", () => {
    let t = 1_000;
    const det = new PullUpDetector("hang", () => t);
    const hang = skeleton({
      [LM.RIGHT_WRIST]: pt(0.5, 0.1),
      [LM.RIGHT_ELBOW]: pt(0.5, 0.28),
      [LM.RIGHT_SHOULDER]: pt(0.5, 0.46),
    });
    feed(det, hang, 1);
    t = 4_000;
    feed(det, hang, 1);
    expect(det.getProgress().durationSec).toBeGreaterThan(2.5);
  });
});

describe("PlankDetector", () => {
  it("pauses the timer when the hips pike", () => {
    let t = 0;
    const det = new PlankDetector(() => t);
    const good = skeleton(plankBody);
    feed(det, good, 1);
    t = 2000;
    feed(det, good, 1);
    const held = det.getProgress().durationSec ?? 0;
    expect(held).toBeGreaterThan(1.5);
    const piked = skeleton({
      ...plankBody,
      [LM.RIGHT_HIP]: pt(0.5, 0.22),
      [LM.LEFT_HIP]: pt(0.5, 0.22),
    });
    t = 4000;
    feed(det, piked, 1);
    const paused = det.getProgress().durationSec ?? 0;
    expect(paused).toBeGreaterThanOrEqual(held);
    t = 8000;
    feed(det, piked, 1);
    expect(det.getProgress().durationSec ?? 0).toBeCloseTo(paused, 5);
    expect(det.getProgress().isValidForm).toBe(false);
  });
});

describe("discount and GPS", () => {
  it("maps push-up bands to percents", () => {
    expect(discountPercentForReps(0)).toBe(5);
    expect(discountPercentForReps(20)).toBe(5);
    expect(discountPercentForReps(21)).toBe(10);
    expect(discountPercentForReps(50)).toBe(10);
    expect(discountPercentForReps(51)).toBe(15);
  });

  it("ends the discount round after 60s", () => {
    expect(PUSHUP_PREP_SEC).toBe(15);
    expect(PUSHUP_ROUND_MS).toBe(60_000);
    expect(pushupRoundExpired(0, 59_999)).toBe(false);
    expect(pushupRoundExpired(0, 60_000)).toBe(true);
  });

  it("reads percent and reps from a push-up ticket payload", () => {
    const payload = btoa(JSON.stringify({ type: "pushup_ticket", reps: 25, percent: 7 }))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
    const parsed = parsePushupTicket(`eyJhbGciOiJub25lIn0.${payload}.sig`);
    expect(parsed?.reps).toBe(25);
    expect(parsed?.percent).toBe(7);
  });

  it("maps remaining test offers to standard levels", () => {
    expect(offerStandardLevel("challenge_100")).toBe("advanced");
    expect(offerIncludesRun("challenge_100")).toBe(false);
  });

  it("challenge_100 protocol is warmup, 4 exercises, stretch — no run", () => {
    const stations = buildProtocol("male", "challenge_100");
    expect(stations.some((s) => s.kind === "run")).toBe(false);
    expect(stations.filter((s) => s.kind === "warmup_work")).toHaveLength(3);
    expect(stations.filter((s) => s.kind === "exercise").map((s) => s.id)).toEqual([
      "pushup",
      "pull",
      "squat",
      "plank",
    ]);
    expect(stations.at(-1)?.kind).toBe("stretch");
  });

  it("challenge_100 uses hang for female pull and never includes GPS run", () => {
    const stations = buildProtocol("female", "challenge_100");
    expect(pullModeForGender("female", "challenge_100")).toBe("hang");
    expect(stations.find((s) => s.id === "pushup")?.durationSec).toBe(60);
    expect(stations.find((s) => s.id === "plank")?.durationSec).toBe(120);
    expect(stations.find((s) => s.id === "pushup-rest")?.durationSec).toBe(60);
    expect(stations.find((s) => s.id === "pull")?.labelVi).toBe("Treo xà");
    expect(stations.some((s) => s.kind === "run")).toBe(false);
  });

  it("filters inaccurate GPS and tiny steps", () => {
    const tracker = new RunTracker(() => 0);
    tracker.ingestForTest(21.0, 105.0, 50, 0);
    expect(tracker.getSnapshot().pointCount).toBe(0);
    tracker.ingestForTest(21.0, 105.0, 5, 1000);
    expect(tracker.getSnapshot().pointCount).toBe(1);
    tracker.ingestForTest(21.000001, 105.0, 5, 2000);
    expect(tracker.getSnapshot().distanceKm).toBe(0);
    tracker.ingestForTest(21.001, 105.0, 5, 3000);
    expect(tracker.getSnapshot().distanceKm).toBeGreaterThan(0.05);
  });
});
