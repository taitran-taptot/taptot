import { describe, expect, it } from "vitest";
import { clampExperienceLevel, knowledgeHref, knowledgeSlugFromPathname, refsForPhase } from "./phaseKnowledge";

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
    expect(slugs).toContain("cach-doc-lich-tap-quy-uoc-buoi-tap");
    expect(slugs).toContain("ky-thuat-tap-chuan-form-an-toan-co-xuong-khop");
    expect(slugs).not.toContain("rpe-va-rir-trong-tung-set");
  });

  it("maps all 3 levels × 3 phases", () => {
    expect(refsForPhase(1, 2).map((r) => r.slug)).toEqual([
      "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong",
      "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo",
      "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
      "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
      "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
      "cardio-cho-suc-khoe-va-giam-mo",
      "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
    ]);
    expect(refsForPhase(1, 3).map((r) => r.slug)).toContain("tuan-xa-tai-nhe-deload-cho-nguoi-moi");
    expect(refsForPhase(2, 2).map((r) => r.slug)).toEqual([
      "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
      "rpe-va-rir-trong-tung-set",
      "deload-dung-thoi-diem",
    ]);
    expect(refsForPhase(3, 1).map((r) => r.label)[0]).toBe("2.1 — RPE và RIR trong từng set");
    expect(refsForPhase(3, 3).map((r) => r.slug)).toContain("refeed-va-diet-break");
  });

  it("sorts reading lists by leading article numbers", () => {
    expect(refsForPhase(1, 1).map((r) => r.label.match(/^[\d.]+/)?.[0])).toEqual([
      "1.0",
      "1.1",
      "1.3",
      "1.4",
      "1.7",
      "1.13",
      "1.14",
      "1.16",
    ]);
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
