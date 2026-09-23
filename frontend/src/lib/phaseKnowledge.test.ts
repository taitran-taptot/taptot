import { describe, expect, it } from "vitest";
import { clampExperienceLevel, knowledgeHref, refsForPhase } from "./phaseKnowledge";

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
  it("returns beginner reading list for missing level", () => {
    const slugs = refsForPhase(undefined, 1).map((r) => r.slug);
    expect(slugs).toContain("cach-doc-lich-tap");
    expect(slugs).toContain("16-k-thut-tp-chun-form");
    expect(slugs).not.toContain("21-rpe-v-rir-trong-tng-set");
  });

  it("maps all 3 levels × 3 phases", () => {
    expect(refsForPhase(1, 2).map((r) => r.slug)).toEqual([
      "13-tnh-tdee-theo-mc-vn-ng",
      "14-macronutrients-protein-carb-fat",
      "18-phc-hi-v-gic-ng",
      "11-hiu-cc-nhm-c-chnh",
    ]);
    expect(refsForPhase(1, 3).map((r) => r.slug)).toContain("tuan-nhe-cho-nguoi-moi");
    expect(refsForPhase(2, 2).map((r) => r.slug)).toEqual([
      "19-progressive-overload-c-bn",
      "21-rpe-v-rir-trong-tng-set",
      "23-deload-ng-thi-im",
    ]);
    expect(refsForPhase(3, 1).map((r) => r.slug)[0]).toBe("28-periodization-c-bn");
    expect(refsForPhase(3, 3).map((r) => r.slug)).toContain("25-refeed-v-diet-break");
  });

  it("returns nothing for unknown phase months", () => {
    expect(refsForPhase(2, 0)).toEqual([]);
    expect(refsForPhase(2, 4)).toEqual([]);
  });

  it("builds knowledge deep links", () => {
    expect(knowledgeHref("cach-doc-lich-tap")).toBe("/kien-thuc?bai=cach-doc-lich-tap");
  });
});
