import { describe, expect, it } from "vitest";
import { siteImageSrc, youtubeEmbedSrc } from "./sitePageMedia";

describe("sitePageMedia helpers", () => {
  it("builds nocookie embed URLs", () => {
    expect(youtubeEmbedSrc("EngW7tLk6R8")).toContain("/embed/EngW7tLk6R8");
  });

  it("keeps public homepage images as local paths", () => {
    expect(siteImageSrc("/home-lo-trinh.png")).toBe("/home-lo-trinh.png");
    expect(siteImageSrc("/hero-gym.jpg")).toBe("/hero-gym.jpg");
  });
});
