import { describe, expect, it } from "vitest";
import { isValidShareSlug, sanitizeShareSlugInput, shareSlugError } from "./shareSlug";

describe("shareSlug", () => {
  it("accepts empty and valid custom slugs", () => {
    expect(isValidShareSlug("")).toBe(true);
    expect(isValidShareSlug("hlv-minh")).toBe(true);
    expect(isValidShareSlug("a1b")).toBe(true);
  });

  it("rejects short, hyphen-edge, and invalid chars", () => {
    expect(isValidShareSlug("ab")).toBe(false);
    expect(isValidShareSlug("-abc")).toBe(false);
    expect(isValidShareSlug("abc-")).toBe(false);
    expect(isValidShareSlug("Hello_World")).toBe(false);
    expect(shareSlugError("ab")).toContain("3–48");
  });

  it("sanitizes typed input", () => {
    expect(sanitizeShareSlugInput(" HLV Minh ")).toBe("hlv-minh");
    expect(sanitizeShareSlugInput("A_B!")).toBe("ab");
  });
});
