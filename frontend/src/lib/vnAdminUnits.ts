/** Vietnam administrative units from 1 July 2025.

Two levels: 34 tỉnh/thành, then phường / xã / đặc khu. No district level.
Snapshot from diachiviet.com open data (CC BY 4.0), documents through 20/09/2026,
bundled so checkout does not depend on a live third-party API.
*/

import tree from "@/data/vn-admin-units.json";

export type AdminUnit = { code: string; name: string };

type WardNode = { code: string; name: string };
type ProvinceNode = { code: string; name: string; wards: WardNode[] };

const PROVINCES = tree as ProvinceNode[];

const provinceByCode = new Map(PROVINCES.map((p) => [p.code, p]));

export async function fetchProvinces(): Promise<AdminUnit[]> {
  return PROVINCES.map(({ code, name }) => ({ code, name }));
}

export async function fetchWards(provinceCode: string): Promise<AdminUnit[]> {
  if (!provinceCode) return [];
  const province = provinceByCode.get(provinceCode);
  if (!province) return [];
  return province.wards.map(({ code, name }) => ({ code, name }));
}
