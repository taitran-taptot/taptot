import { describe, expect, it } from "vitest";
import { angleDeg, haversineMeters, inclineFromFloorDeg, isVisible } from "@/lib/fitness-tracker/math/geometry";
import { DEBOUNCE_FRAMES, FrameDebouncer } from "@/lib/fitness-tracker/pose/debounce";
import { PushUpDetector, PUSHUP_MIN_REP_MS } from "@/lib/fitness-tracker/detectors/PushUpDetector";
import { SquatDetector } from "@/lib/fitness-tracker/detectors/SquatDetector";
import { PullUpDetector } from "@/lib/fitness-tracker/detectors/PullUpDetector";
import { PlankDetector } from "@/lib/fitness-tracker/detectors/PlankDetector";
import { discountPercentForReps, formatDiscountPercent, parsePushupTicket, plankFormBreakDue, priceAfterDiscount, PUSHUP_IDLE_MS, PUSHUP_PREP_SEC, PUSHUP_ROUND_MS, pushupIdleCountdownDue, pushupRoundExpired } from "@/lib/fitness-tracker/session/discount";
import { buildProtocol, offerIncludesRun, offerStandardLevel, pullModeForGender } from "@/lib/fitness-tracker/session/protocol";
import { RunTracker } from "@/lib/fitness-tracker/gps/RunTracker";
import { cameraErrorMessage } from "@/lib/fitness-tracker/pose/PoseEngine";
import { LM } from "@/lib/fitness-tracker/pose/landmarks";
import type { Point2D } from "@/lib/fitness-tracker/types";

function pt(x: number, y: number, vis = 1): Point2D {
  return { x, y, visibility: vis };
}

function skeleton(patch: Partial<Record<number, Point2D>>): Point2D[] {
  const out: Point2D[] = Array.from({ length: 33 }, () => pt(0.5, 0.5, 0));
  for (const [key, value] of Object.entries(patch)) {
    if (!value) continue;
    out[Number(key)] = pt(value.x, value.y, value.visibility ?? 1);
  }
  return out;
}

function feed(detector: { process: (l: Point2D[]) => void }, pose: Point2D[], frames = 2): void {
  for (let i = 0; i < frames; i += 1) detector.process(pose);
}

const plankBody = {
  [LM.RIGHT_EAR]: pt(0.14, 0.32),
  [LM.LEFT_EAR]: pt(0.14, 0.3),
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

function descend(body: Record<number, Point2D>): Record<number, Point2D> {
  const out = { ...body };
  for (const id of [
    LM.LEFT_EAR,
    LM.RIGHT_EAR,
    LM.LEFT_SHOULDER,
    LM.RIGHT_SHOULDER,
    LM.LEFT_HIP,
    LM.RIGHT_HIP,
    LM.LEFT_KNEE,
    LM.RIGHT_KNEE,
    LM.LEFT_ANKLE,
    LM.RIGHT_ANKLE,
  ]) {
    const joint = out[id];
    if (!joint) continue;
    out[id] = pt(joint.x, joint.y + 0.06, joint.visibility ?? 1);
  }
  return out;
}

describe("geometry", () => {
  it("computes a right angle at the vertex", () => {
    expect(angleDeg(pt(0, 1), pt(0, 0), pt(1, 0))).toBeCloseTo(90, 5);
  });

  it("treats visibility 0 as visible for Pose Landmarker", () => {
    expect(isVisible(pt(0.3, 0.4, 0))).toBe(true);
    expect(isVisible(pt(0.3, 0.4, 0.2))).toBe(false);
    expect(isVisible(pt(0.3, 0.4, 0.9))).toBe(true);
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

describe("cameraErrorMessage", () => {
  it("maps permission and in-use errors", () => {
    expect(cameraErrorMessage(new DOMException("denied", "NotAllowedError"))).toMatch(/chặn camera/);
    expect(cameraErrorMessage(new DOMException("busy", "NotReadableError"))).toMatch(/app khác/);
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
    feed(det, skeleton(descend(downElbow)));
    expect(det.getProgress().state).toBe("DOWN");
    feed(det, skeleton(upElbow));
    expect(det.getProgress().count).toBe(1);
    feed(det, skeleton(standing));
    expect(det.getProgress().state).toBe("OUT_OF_POSITION");
  });

  it("does not count an arm bend that leaves the shoulder and hip in place", () => {
    const det = new PushUpDetector();
    const upElbow = { ...plankBody, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const downElbow = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.4),
    };
    feed(det, skeleton(upElbow));
    feed(det, skeleton(downElbow));
    feed(det, skeleton(upElbow));
    expect(det.getProgress().count).toBe(0);
  });

  it("counts when the top is not a full lockout", () => {
    const det = new PushUpDetector();
    const softUp = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.25, 0.56),
      [LM.RIGHT_WRIST]: pt(0.25, 0.72),
      [LM.LEFT_ELBOW]: pt(0.25, 0.54),
      [LM.LEFT_WRIST]: pt(0.25, 0.70),
    };
    const downElbow = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.40),
    };
    feed(det, skeleton(softUp));
    feed(det, skeleton(descend(downElbow)));
    feed(det, skeleton(softUp));
    expect(det.getProgress().count).toBe(1);
  });

  it("does not count when the hips pike off the body line", () => {
    const det = new PushUpDetector();
    const upElbow = { ...plankBody, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const downElbow = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.40),
    };
    const piky = {
      ...downElbow,
      [LM.RIGHT_HIP]: pt(0.40, 0.68),
      [LM.LEFT_HIP]: pt(0.40, 0.66),
    };
    feed(det, skeleton(upElbow));
    feed(det, skeleton(descend(downElbow)));
    feed(det, skeleton(piky));
    expect(det.getProgress().isValidForm).toBe(false);
    feed(det, skeleton(upElbow));
    expect(det.getProgress().count).toBe(0);
  });

  it("does not register DOWN on a shallow elbow dip around 130°", () => {
    const det = new PushUpDetector();
    const upElbow = { ...plankBody, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const shallow = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.20, 0.55),
      [LM.RIGHT_WRIST]: pt(0.27, 0.68),
      [LM.LEFT_ELBOW]: pt(0.20, 0.53),
      [LM.LEFT_WRIST]: pt(0.27, 0.66),
    };
    feed(det, skeleton(upElbow));
    expect(det.getProgress().state).toBe("UP");
    feed(det, skeleton(shallow));
    expect(det.getProgress().state).toBe("UP");
    feed(det, skeleton(upElbow));
    expect(det.getProgress().count).toBe(0);
  });

  it("does not count when the joints are reported with visibility 0", () => {
    const det = new PushUpDetector();
    const zeroVis = (body: Record<number, Point2D>) => {
      const pose = skeleton(body);
      for (const p of pose) p.visibility = 0;
      return pose;
    };
    const upElbow = { ...plankBody, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const downElbow = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.40),
    };
    feed(det, zeroVis(upElbow));
    feed(det, zeroVis(descend(downElbow)));
    feed(det, zeroVis(upElbow));
    expect(det.getProgress().count).toBe(0);
    expect(det.getProgress().isValidForm).toBe(false);
  });

  it("ignores a second cycle faster than the minimum gap", () => {
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
      feed(det, skeleton(descend(downElbow)));
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

  it("does not count while scoring is off, and starting the minute clears the count", () => {
    const det = new PushUpDetector();
    const upElbow = { ...plankBody, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const downElbow = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.40),
    };
    det.setCounting(false);
    feed(det, skeleton(upElbow));
    feed(det, skeleton(descend(downElbow)));
    feed(det, skeleton(upElbow));
    expect(det.getProgress().count).toBe(0);
    det.setCounting(true);
    expect(det.getProgress().count).toBe(0);
    feed(det, skeleton(upElbow));
    feed(det, skeleton(descend(downElbow)));
    feed(det, skeleton(upElbow));
    expect(det.getProgress().count).toBe(1);
  });

  it("counts a side-view push-up when the leg is not one straight line", () => {
    const softLeg = {
      ...plankBody,
      [LM.RIGHT_KNEE]: pt(0.78, 0.47),
      [LM.RIGHT_ANKLE]: pt(0.93, 0.43),
      [LM.LEFT_KNEE]: pt(0.78, 0.45),
      [LM.LEFT_ANKLE]: pt(0.93, 0.41),
    };
    const upElbow = { ...softLeg, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const downElbow = {
      ...softLeg,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.4),
    };
    const det = new PushUpDetector();
    feed(det, skeleton(upElbow));
    feed(det, skeleton(descend(downElbow)));
    feed(det, skeleton(upElbow));
    expect(det.getProgress().count).toBe(1);
  });

  it("does not count a kneeling push-up or a front-facing body", () => {
    const kneeling = {
      ...plankBody,
      [LM.RIGHT_KNEE]: pt(0.7, 0.58),
      [LM.RIGHT_ANKLE]: pt(0.55, 0.55),
      [LM.LEFT_KNEE]: pt(0.7, 0.56),
      [LM.LEFT_ANKLE]: pt(0.55, 0.53),
    };
    const upElbow = { ...kneeling, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const downElbow = {
      ...kneeling,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.4),
    };
    const det = new PushUpDetector();
    feed(det, skeleton(upElbow));
    feed(det, skeleton(descend(downElbow)));
    feed(det, skeleton(upElbow));
    expect(det.getProgress().count).toBe(0);
    expect(det.getProgress().isValidForm).toBe(false);

    const facing = {
      [LM.LEFT_SHOULDER]: pt(0.32, 0.4),
      [LM.RIGHT_SHOULDER]: pt(0.68, 0.4),
      [LM.LEFT_ELBOW]: pt(0.28, 0.55),
      [LM.RIGHT_ELBOW]: pt(0.72, 0.55),
      [LM.LEFT_WRIST]: pt(0.3, 0.7),
      [LM.RIGHT_WRIST]: pt(0.7, 0.7),
      [LM.LEFT_HIP]: pt(0.4, 0.48),
      [LM.RIGHT_HIP]: pt(0.6, 0.48),
      [LM.LEFT_KNEE]: pt(0.42, 0.62),
      [LM.RIGHT_KNEE]: pt(0.58, 0.62),
      [LM.LEFT_ANKLE]: pt(0.44, 0.78),
      [LM.RIGHT_ANKLE]: pt(0.56, 0.78),
    };
    const front = new PushUpDetector();
    feed(front, skeleton(facing));
    expect(front.getProgress().isValidForm).toBe(false);
    expect(front.getProgress().count).toBe(0);
  });

  it("does not count when the knee is missing", () => {
    const det = new PushUpDetector();
    const hideKnees = (body: Record<number, Point2D>) => {
      const pose = skeleton(body);
      for (const id of [LM.RIGHT_KNEE, LM.LEFT_KNEE]) {
        const joint = pose[id];
        pose[id] = pt(joint.x, joint.y, 0.1);
      }
      return pose;
    };
    const upElbow = { ...plankBody, [LM.RIGHT_ELBOW]: pt(0.25, 0.58), [LM.RIGHT_WRIST]: pt(0.25, 0.74) };
    const downElbow = {
      ...plankBody,
      [LM.RIGHT_ELBOW]: pt(0.12, 0.55),
      [LM.RIGHT_WRIST]: pt(0.25, 0.42),
      [LM.LEFT_ELBOW]: pt(0.12, 0.53),
      [LM.LEFT_WRIST]: pt(0.25, 0.4),
    };
    feed(det, hideKnees(upElbow));
    feed(det, hideKnees(downElbow));
    feed(det, hideKnees(upElbow));
    expect(det.getProgress().count).toBe(0);
    expect(det.getProgress().isValidForm).toBe(false);
  });
});

describe("push-up idle countdown", () => {
  it("starts only after 10s without a rep when more than 10s remain", () => {
    const started = 0;
    expect(pushupIdleCountdownDue(0, PUSHUP_IDLE_MS, started)).toBe(true);
    expect(pushupIdleCountdownDue(0, PUSHUP_IDLE_MS - 1, started)).toBe(false);
    const lateRep = PUSHUP_ROUND_MS - PUSHUP_IDLE_MS - 5_000;
    expect(pushupIdleCountdownDue(lateRep, lateRep + PUSHUP_IDLE_MS, started)).toBe(false);
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

  it("does not count a body lying flat on the floor", () => {
    let t = 0;
    const det = new PlankDetector(() => t);
    const flat = skeleton({
      [LM.RIGHT_EAR]: pt(0.12, 0.48),
      [LM.LEFT_EAR]: pt(0.12, 0.46),
      [LM.RIGHT_SHOULDER]: pt(0.22, 0.5),
      [LM.LEFT_SHOULDER]: pt(0.22, 0.48),
      [LM.RIGHT_ELBOW]: pt(0.34, 0.51),
      [LM.LEFT_ELBOW]: pt(0.34, 0.49),
      [LM.RIGHT_WRIST]: pt(0.46, 0.52),
      [LM.LEFT_WRIST]: pt(0.46, 0.5),
      [LM.RIGHT_HIP]: pt(0.55, 0.5),
      [LM.LEFT_HIP]: pt(0.55, 0.48),
      [LM.RIGHT_KNEE]: pt(0.72, 0.51),
      [LM.LEFT_KNEE]: pt(0.72, 0.49),
      [LM.RIGHT_ANKLE]: pt(0.88, 0.52),
      [LM.LEFT_ANKLE]: pt(0.88, 0.5),
    });
    feed(det, flat, 1);
    t = 3000;
    feed(det, flat, 1);
    expect(det.getProgress().isValidForm).toBe(false);
    expect(det.getProgress().durationSec ?? 0).toBe(0);
    expect(det.getProgress().statusText).toMatch(/không nằm áp sàn/);
  });

  it("does not count a kneeling plank or a body with a missing joint", () => {
    let t = 0;
    const det = new PlankDetector(() => t);
    const kneeling = skeleton({
      ...plankBody,
      [LM.RIGHT_HIP]: pt(0.55, 0.43),
      [LM.RIGHT_KNEE]: pt(0.72, 0.6),
      [LM.RIGHT_ANKLE]: pt(0.9, 0.45),
      [LM.LEFT_HIP]: pt(0.55, 0.41),
      [LM.LEFT_KNEE]: pt(0.72, 0.58),
      [LM.LEFT_ANKLE]: pt(0.9, 0.43),
    });
    feed(det, kneeling, 1);
    t = 3000;
    feed(det, kneeling, 1);
    expect(det.getProgress().isValidForm).toBe(false);
    expect(det.getProgress().durationSec ?? 0).toBe(0);

    const missingAnkle = skeleton(plankBody);
    missingAnkle[LM.RIGHT_ANKLE] = pt(0.92, 0.48, 0.1);
    missingAnkle[LM.LEFT_ANKLE] = pt(0.92, 0.46, 0.1);
    t = 6000;
    feed(det, missingAnkle, 1);
    expect(det.getProgress().isValidForm).toBe(false);
    expect(det.getProgress().durationSec ?? 0).toBe(0);
  });

  it("counts a plank that is not one straight line", () => {
    let t = 0;
    const det = new PlankDetector(() => t);
    const sag = skeleton({
      ...plankBody,
      [LM.RIGHT_HIP]: pt(0.58, 0.5),
      [LM.RIGHT_KNEE]: pt(0.78, 0.52),
      [LM.RIGHT_ANKLE]: pt(0.93, 0.46),
      [LM.LEFT_HIP]: pt(0.58, 0.48),
      [LM.LEFT_KNEE]: pt(0.78, 0.5),
      [LM.LEFT_ANKLE]: pt(0.93, 0.44),
    });
    feed(det, sag, 1);
    t = 2000;
    feed(det, sag, 1);
    expect(det.getProgress().isValidForm).toBe(true);
    expect(det.getProgress().durationSec ?? 0).toBeGreaterThan(1.5);
  });

  it("does not count when the feet are clipped by the frame", () => {
    let t = 0;
    const det = new PlankDetector(() => t);
    const clipped = skeleton({
      ...plankBody,
      [LM.RIGHT_ANKLE]: pt(0.99, 0.48),
      [LM.LEFT_ANKLE]: pt(0.99, 0.46),
    });
    feed(det, clipped, 1);
    t = 2000;
    feed(det, clipped, 1);
    expect(det.getProgress().isValidForm).toBe(false);
    expect(det.getProgress().durationSec ?? 0).toBe(0);
    expect(det.getProgress().statusText).toMatch(/cả người vào khung/);
  });
});

describe("discount and GPS", () => {
  it("maps each push-up to 0.2 percent up to 100 reps", () => {
    expect(discountPercentForReps(0)).toBe(0);
    expect(discountPercentForReps(1)).toBe(0.2);
    expect(discountPercentForReps(8)).toBe(1.6);
    expect(discountPercentForReps(25)).toBe(5);
    expect(discountPercentForReps(100)).toBe(20);
    expect(discountPercentForReps(101)).toBe(20);
    expect(formatDiscountPercent(0.2)).toBe("0,2");
    expect(formatDiscountPercent(1.6)).toBe("1,6");
    expect(formatDiscountPercent(20)).toBe("20");
    expect(priceAfterDiscount(100_000, 0)).toBe(100_000);
    expect(priceAfterDiscount(100_000, 0.2)).toBe(99_800);
    expect(priceAfterDiscount(100_000, 1.6)).toBe(98_400);
  });

  it("fails plank after 5s of broken form", () => {
    expect(plankFormBreakDue(null, 5_000)).toBe(false);
    expect(plankFormBreakDue(0, 4_999)).toBe(false);
    expect(plankFormBreakDue(0, 5_000)).toBe(true);
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

  it("ignores an expired push-up ticket", () => {
    const payload = btoa(
      JSON.stringify({ type: "pushup_ticket", reps: 25, percent: 10, exp: 1 }),
    )
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
    expect(parsePushupTicket(`eyJhbGciOiJub25lIn0.${payload}.sig`)).toBeNull();
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
