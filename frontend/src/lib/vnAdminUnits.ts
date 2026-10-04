/** Vietnam administrative units (63 tỉnh/thành → quận/huyện → phường/xã).

Snapshot from GSO codes via provinces.open-api.vn (depth=3), bundled so checkout
does not depend on a live third-party API.
*/

import tree from "@/data/vn-admin-units.json";

export type AdminUnit = { code: string; name: string };

type WardNode = { code: string; name: string };
type DistrictNode = { code: string; name: string; wards: WardNode[] };
type ProvinceNode = { code: string; name: string; districts: DistrictNode[] };

const PROVINCES = tree as ProvinceNode[];

const provinceByCode = new Map(PROVINCES.map((p) => [p.code, p]));
const districtByCode = new Map<string, DistrictNode>();
for (const p of PROVINCES) {
  for (const d of p.districts) {
    districtByCode.set(d.code, d);
  }
}

export async function fetchProvinces(): Promise<AdminUnit[]> {
  return PROVINCES.map(({ code, name }) => ({ code, name }));
}

export async function fetchDistricts(provinceCode: string): Promise<AdminUnit[]> {
  if (!provinceCode) return [];
  const p = provinceByCode.get(provinceCode);
  if (!p) return [];
  return p.districts.map(({ code, name }) => ({ code, name }));
}

export async function fetchWards(districtCode: string): Promise<AdminUnit[]> {
  if (!districtCode) return [];
  const d = districtByCode.get(districtCode);
  if (!d) return [];
  return d.wards.map(({ code, name }) => ({ code, name }));
}
