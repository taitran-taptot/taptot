import { describe, expect, it } from "vitest";
import {
  clampExperienceLevel,
  knowledgeHref,
  knowledgeSlugFromPathname,
  refsForChallengePhases,
  refsForPhase,
} from "./phaseKnowledge";

describe("clampExperienceLevel", () => {
  it("defaults missing or invalid values to beginner", () => {
    expect(clampExperienceLevel(undefined)).toBe(1);
    expect(clampExperienceLevel(null)).toBe(1);
    expect(clampExperienceLevel(0)).toBe(1);
    expect(clampExperienceLevel(Number.NaN)).toBe(1);
  });

  it("clamps to 1–3", () => {
    expect(clampExperienceLevel(1)).toBe(1);
    expect(clampExperienceLevel(2)).toBe(2);
    expect(clampExperienceLevel(3)).toBe(3);
    expect(clampExperienceLevel(4)).toBe(3);
  });
});

describe("refsForPhase", () => {
  it("returns three-to-four beginner articles for missing level", () => {
    const slugs = refsForPhase(undefined, 1).map((r) => r.slug);
    expect(slugs.length).toBeGreaterThanOrEqual(3);
    expect(slugs.length).toBeLessThanOrEqual(4);
    expect(slugs[0]).toBe("cach-doc-lich-tap-quy-uoc-buoi-tap");
    expect(slugs).not.toContain("rpe-va-rir-trong-tung-set");
  });

  it("varies by goal and daily job and does not repeat across phases", () => {
    const sedentary = refsForChallengePhases(1, { goal: "lose_weight", activity: "sedentary" });
    const labor = refsForChallengePhases(1, { goal: "gain_weight", activity: "very_active" });
    expect(sedentary[0].slice(0, 3).map((r) => r.slug)).toEqual([
      "cach-doc-lich-tap-quy-uoc-buoi-tap",
      "xac-dinh-muc-tieu-tap-luyen",
      "khoi-dong-warm-up-van-dong-khop-mobility",
    ]);
    expect(labor[0].slice(0, 3).map((r) => r.slug)).toEqual([
      "cach-doc-lich-tap-quy-uoc-buoi-tap",
      "xac-dinh-muc-tieu-tap-luyen",
      "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
    ]);
    const slugs = sedentary.flatMap((month) => month.map((r) => r.slug));
    expect(new Set(slugs).size).toBe(slugs.length);
    expect(refsForPhase(1, 3, { goal: "lose_weight", activity: "sedentary" }).map((r) => r.slug)).toContain(
      "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
    );
    expect(refsForPhase(3, 1)[0].label).toBe("2.8 — Periodization cơ bản");
    expect(
      refsForPhase(3, 3, { goal: "lose_weight", activity: "moderate" }).map((r) => r.slug),
    ).toContain("refeed-va-diet-break");
  });

  it("returns nothing for unknown phase months", () => {
    expect(refsForPhase(2, 0)).toEqual([]);
    expect(refsForPhase(2, 4)).toEqual([]);
  });

  it("builds knowledge article path URLs", () => {
    expect(knowledgeHref("")).toBe("/kien-thuc");
    expect(knowledgeHref("10-xc-nh-mc-tiu-tp-luyn")).toBe(
      "/kien-thuc/xac-dinh-muc-tieu-tap-luyen",
    );
    expect(knowledgeSlugFromPathname("/kien-thuc/10-xc-nh-mc-tiu-tp-luyn")).toBe(
      "xac-dinh-muc-tieu-tap-luyen",
    );
    expect(knowledgeSlugFromPathname("/kien-thuc/cach-doc-lich-tap-quy-uoc-buoi-tap")).toBe("cach-doc-lich-tap-quy-uoc-buoi-tap");
    expect(knowledgeSlugFromPathname("/kien-thuc")).toBe("");
  });
});
