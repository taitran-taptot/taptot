import { describe, expect, it } from "vitest";
import {
  DEV_TEST_GIFT_CODE,
  formatGiftCodeInput,
  giftCodeFromPathname,
  giftCodeReady,
  giftStartHref,
  isDevTestGiftCode,
} from "./giftCode";

describe("giftCode", () => {
  it("keeps the reusable test code as 1", () => {
    expect(formatGiftCodeInput("1")).toBe(DEV_TEST_GIFT_CODE);
    expect(formatGiftCodeInput(" 1 ")).toBe("1");
    expect(isDevTestGiftCode("1")).toBe(true);
    expect(giftCodeReady("1")).toBe(true);
    expect(giftStartHref("1")).toBe("/batdau/1");
  });

  it("formats sticker codes as TT-XXXX-XXXX", () => {
    expect(formatGiftCodeInput("tt7k3mp2qx")).toBe("TT-7K3M-P2QX");
    expect(giftCodeReady("TT-7K3M-P2QX")).toBe(true);
    expect(giftStartHref("TT-7K3M-P2QX")).toBe("/batdau/TT-7K3M-P2QX");
  });

  it("reads /batdau/[ma] from the path", () => {
    expect(giftCodeFromPathname("/batdau/1")).toBe("1");
    expect(giftCodeFromPathname("/batdau/TT-7K3M-P2QX")).toBe("TT-7K3M-P2QX");
    expect(giftCodeFromPathname("/batdau")).toBe("");
  });
});
