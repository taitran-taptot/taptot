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
  it("returns four beginner articles for missing level", () => {
    const slugs = refsForPhase(undefined, 1).map((r) => r.slug);
    expect(slugs).toEqual([
      "cach-doc-lich-tap-quy-uoc-buoi-tap",
      "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
      "khoi-dong-warm-up-van-dong-khop-mobility",
      "hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap",
    ]);
    expect(slugs).not.toContain("rpe-va-rir-trong-tung-set");
  });

  it("varies by goal, daily job, and home training without repeating articles", () => {
    const sedentary = refsForChallengePhases(1, { goal: "lose_weight", activity: "sedentary" });
    const labor = refsForChallengePhases(1, { goal: "gain_weight", activity: "very_active" });
    const home = refsForChallengePhases(1, { goal: "lose_weight", activity: "sedentary", location: "home" });
    expect(sedentary[0].map((r) => r.slug)).toEqual([
      "cach-doc-lich-tap-quy-uoc-buoi-tap",
      "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
      "khoi-dong-warm-up-van-dong-khop-mobility",
      "hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap",
    ]);
    expect(labor[0].map((r) => r.slug)).toEqual([
      "cach-doc-lich-tap-quy-uoc-buoi-tap",
      "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
      "theo-doi-dau-va-dau-hieu-can-kham",
      "hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap",
    ]);
    expect(home[0][3].slug).toBe("tap-tai-nha-chon-va-su-dung-dung-cu-an-toan");
    expect(labor[1].map((r) => r.slug)).toContain("tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi");
    expect(sedentary[1].map((r) => r.slug)).toContain("nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo");
    expect(labor[1].map((r) => r.slug)).toContain(
      "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
    );
    const slugs = sedentary.flatMap((month) => month.map((r) => r.slug));
    expect(new Set(slugs).size).toBe(slugs.length);
    expect(refsForPhase(1, 3, { goal: "lose_weight", activity: "sedentary" }).map((r) => r.slug)).toEqual([
      "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
      "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
      "theo-doi-tien-bo-va-nhat-ky-tap-luyen",
      "cardio-cho-suc-khoe-va-giam-mo",
    ]);
    expect(refsForPhase(3, 1).map((r) => r.slug)[1]).toBe("periodization-co-ban");
    expect(refsForPhase(3, 3, { goal: "lose_weight" }).map((r) => r.slug)).toContain("refeed-va-diet-break");
    expect(refsForPhase(2, 3, { goal: "lose_weight" }).map((r) => r.slug)).toContain("carb-cycling-co-ban");
    expect(refsForPhase(2, 3, { goal: "maintain" }).map((r) => r.slug)).toContain(
      "uoc-luong-khau-phan-va-an-uong-thuc-te",
    );
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
