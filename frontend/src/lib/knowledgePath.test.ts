import { describe, expect, it } from "vitest";
import { articleSlugsInOrder, displayCodeForSlug, pathForSlug } from "./knowledgePath";

describe("knowledge path order", () => {
  it("numbers lessons from 1.0 in learning order", () => {
    const slugs = articleSlugsInOrder();
    expect(slugs).toHaveLength(33);
    expect(new Set(slugs).size).toBe(33);
    expect(displayCodeForSlug(slugs[0])).toBe("1.0");
    expect(displayCodeForSlug(slugs[1])).toBe("1.1");
    expect(displayCodeForSlug(slugs[2])).toBe("1.2");
    expect(displayCodeForSlug("tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi")).toBe("1.2");
    expect(displayCodeForSlug(slugs[32])).toBe("1.32");
    expect(slugs.indexOf("hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap")).toBeLessThan(
      slugs.indexOf("ky-thuat-tap-chuan-form-an-toan-co-xuong-khop"),
    );
    expect(slugs.slice(-2)).toEqual(["carb-cycling-co-ban", "refeed-va-diet-break"]);
  });

  it("maps the four learning paths", () => {
    expect(pathForSlug("tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi")?.index).toBe("01");
    expect(pathForSlug("theo-doi-tien-bo-va-nhat-ky-tap-luyen")?.index).toBe("02");
    expect(pathForSlug("cach-tinh-tdee-theo-muc-van-dong-thuc-te")?.index).toBe("03");
    expect(pathForSlug("refeed-va-diet-break")?.readWhen).toBe("experienced");
  });
});
