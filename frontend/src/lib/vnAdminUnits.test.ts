import { describe, expect, it } from "vitest";
import { fetchProvinces, fetchWards } from "./vnAdminUnits";

describe("vnAdminUnits local snapshot", () => {
  it("loads the 34 provinces in effect from July 2025", async () => {
    const provinces = await fetchProvinces();
    expect(provinces).toHaveLength(34);
    const names = provinces.map((p) => p.name);
    expect(names).toContain("Thành phố Hà Nội");
    expect(names).toContain("Thành phố Hồ Chí Minh");
    expect(names).toContain("Thành phố Quảng Ninh");
    expect(names.some((n) => n.includes("Hà Giang"))).toBe(false);
    expect(names.some((n) => n.includes("Bình Dương"))).toBe(false);
  });

  it("lists Hanoi wards directly, without a district", async () => {
    const provinces = await fetchProvinces();
    const hn = provinces.find((p) => p.name === "Thành phố Hà Nội");
    expect(hn).toBeTruthy();
    const wards = await fetchWards(hn!.code);
    expect(wards).toHaveLength(126);
    expect(wards.some((w) => w.name === "Phường Ba Đình")).toBe(true);
    expect(wards.some((w) => w.name === "Phường Phúc Xá")).toBe(false);
    expect(await fetchWards("")).toEqual([]);
    expect(await fetchWards("99")).toEqual([]);
  });
});
