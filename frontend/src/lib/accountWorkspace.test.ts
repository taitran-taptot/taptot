import { describe, expect, it } from "vitest";
import {
  accountShellHref,
  accountShellPath,
  accountTabFromLocation,
  isAccountShellPath,
  parseAccountTab,
  tabFromLegacyPath,
} from "./accountWorkspace";

describe("accountWorkspace", () => {
  it("uses quản trị shell for admin and tài khoản for HLV", () => {
    expect(accountShellPath("admin")).toBe("/tai-khoan/quan-tri");
    expect(accountShellPath("hlv")).toBe("/tai-khoan");
  });

  it("maps legacy catalog URLs to tabs", () => {
    expect(tabFromLegacyPath("/tai-khoan/quan-tri/don-hang")).toBe("don-hang");
    expect(tabFromLegacyPath("/tai-khoan/don-hang")).toBeNull();
    expect(tabFromLegacyPath("/tai-khoan/ke-hoach")).toBe("ke-hoach");
    expect(tabFromLegacyPath("/tai-khoan/quan-tri")).toBeNull();
    expect(tabFromLegacyPath("/tai-khoan")).toBeNull();
  });

  it("falls back to role default when tab is missing or forbidden", () => {
    expect(parseAccountTab(null, "admin")).toBe("thong-ke");
    expect(parseAccountTab("bai-tap", "hlv")).toBe("bai-tap");
    expect(parseAccountTab("thong-ke", "hlv")).toBe("ke-hoach");
    expect(accountShellHref("admin", "don-hang")).toBe("/tai-khoan/quan-tri?tab=don-hang");
  });

  it("keeps lịch editor on the ke-hoach tab", () => {
    expect(accountTabFromLocation("/tai-khoan/lich/abc", "thong-ke", "admin")).toBe("ke-hoach");
    expect(isAccountShellPath("/tai-khoan/quan-tri/")).toBe(true);
  });
});
