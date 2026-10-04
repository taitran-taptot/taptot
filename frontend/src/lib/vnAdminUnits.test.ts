import { describe, expect, it } from "vitest";
import { fetchDistricts, fetchProvinces, fetchWards } from "./vnAdminUnits";

describe("vnAdminUnits local snapshot", () => {
  it("loads 63 provinces including Ha Noi and HCM", async () => {
    const provinces = await fetchProvinces();
    expect(provinces).toHaveLength(63);
    const names = provinces.map((p) => p.name);
    expect(names.some((n) => n.includes("Hà Nội"))).toBe(true);
    expect(names.some((n) => n.includes("Hồ Chí Minh"))).toBe(true);
  });

  it("lists districts and wards for Ha Noi", async () => {
    const provinces = await fetchProvinces();
    const hn = provinces.find((p) => p.name.includes("Hà Nội"));
    expect(hn).toBeTruthy();
    const districts = await fetchDistricts(hn!.code);
    expect(districts.length).toBeGreaterThan(5);
    const baDinh = districts.find((d) => d.name.includes("Ba Đình"));
    expect(baDinh).toBeTruthy();
    const wards = await fetchWards(baDinh!.code);
    expect(wards.length).toBeGreaterThan(0);
    expect(wards.some((w) => w.name.includes("Phúc Xá"))).toBe(true);
  });
});
