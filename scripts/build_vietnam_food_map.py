"""Build simplified SVG-path map JSON for /thuc-an Vietnam food map."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "public" / "maps" / "vietnam-provinces.json"
OUT = ROOT / "frontend" / "public" / "maps" / "vietnam-food-map.json"

# Culinary / geographic regions for the 34 post-merger provinces.
PROVINCE_REGION: dict[str, str] = {
    "Lai Châu": "mien-bac",
    "Điện Biên": "mien-bac",
    "Sơn La": "mien-bac",
    "Lào Cai": "mien-bac",
    "Cao Bằng": "mien-bac",
    "Lạng Sơn": "mien-bac",
    "Quảng Ninh": "mien-bac",
    "Tuyên Quang": "mien-bac",
    "Thái Nguyên": "mien-bac",
    "Phú Thọ": "mien-bac",
    "Bắc Ninh": "mien-bac",
    "Hà Nội": "mien-bac",
    "Hải Phòng": "mien-bac",
    "Hưng Yên": "mien-bac",
    "Ninh Bình": "mien-bac",
    "Thanh Hóa": "mien-bac",
    "Nghệ An": "mien-trung",
    "Hà Tĩnh": "mien-trung",
    "Quảng Trị": "mien-trung",
    "Huế": "mien-trung",
    "Đà Nẵng": "mien-trung",
    "Quảng Ngãi": "mien-trung",
    "Gia Lai": "mien-trung",
    "Đắk Lắk": "mien-trung",
    "Khánh Hòa": "mien-trung",
    "Lâm Đồng": "mien-trung",
    "Đồng Nai": "mien-nam",
    "Tây Ninh": "mien-nam",
    "TP. Hồ Chí Minh": "mien-nam",
    "Cần Thơ": "mien-nam",
    "Đồng Tháp": "mien-nam",
    "An Giang": "mien-nam",
    "Vĩnh Long": "mien-nam",
    "Cà Mau": "mien-nam",
}

# Lon threshold: Paracel / Spratly clusters sit east of mainland Vietnam.
ISLAND_LON = 111.0

VIEW_W = 420
VIEW_H = 560


def project(lon: float, lat: float, b: dict) -> tuple[float, float]:
    x = (lon - b["minLon"]) / (b["maxLon"] - b["minLon"]) * VIEW_W
    y = (b["maxLat"] - lat) / (b["maxLat"] - b["minLat"]) * VIEW_H
    return round(x, 2), round(y, 2)


def ring_to_path(ring: list, b: dict) -> str:
    if len(ring) < 3:
        return ""
    parts: list[str] = []
    for i, pt in enumerate(ring):
        x, y = project(float(pt[0]), float(pt[1]), b)
        parts.append(f"{'M' if i == 0 else 'L'}{x} {y}")
    parts.append("Z")
    return "".join(parts)


def ring_center(ring: list) -> tuple[float, float]:
    xs = [float(p[0]) for p in ring]
    ys = [float(p[1]) for p in ring]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def ring_area(ring: list) -> float:
    if len(ring) < 3:
        return 0.0
    area = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = float(ring[i][0]), float(ring[i][1])
        x2, y2 = float(ring[(i + 1) % n][0]), float(ring[(i + 1) % n][1])
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def significant_rings(rings: list, frac: float = 0.015) -> list:
    """Drop Ha Long-style specks that wash out a province fill."""
    scored = [(ring_area(r), r) for r in rings if len(r) >= 3]
    if not scored:
        return []
    mx = max(a for a, _ in scored)
    thresh = mx * frac
    return [r for a, r in scored if a >= thresh]


def main() -> None:
    raw = json.loads(SRC.read_text(encoding="utf-8"))
    bounds = raw["bounds"]
    features: list[dict] = []

    for prov in raw["provinces"]:
        name = prov["name"]
        base_region = PROVINCE_REGION.get(name, "mien-nam")
        mainland_rings: list = []
        island_rings: list = []
        for ring in prov["polygons"]:
            if len(ring) < 3:
                continue
            cx, _cy = ring_center(ring)
            if name in {"Đà Nẵng", "Khánh Hòa"} and cx >= ISLAND_LON:
                island_rings.append(ring)
            else:
                mainland_rings.append(ring)

        mainland = [d for r in significant_rings(mainland_rings) if (d := ring_to_path(r, bounds))]
        islands = [d for r in island_rings if (d := ring_to_path(r, bounds))]

        if mainland:
            features.append(
                {
                    "id": str(prov["id"]),
                    "name": name,
                    "region": base_region,
                    "d": " ".join(mainland),
                }
            )

        if islands and name == "Đà Nẵng":
            features.append(
                {
                    "id": "hoang-sa",
                    "name": "Quần đảo Hoàng Sa",
                    "region": "hoang-sa",
                    "d": " ".join(islands),
                }
            )
        elif islands and name == "Khánh Hòa":
            features.append(
                {
                    "id": "truong-sa",
                    "name": "Quần đảo Trường Sa",
                    "region": "truong-sa",
                    "d": " ".join(islands),
                }
            )

    missing = [p["name"] for p in raw["provinces"] if p["name"] not in PROVINCE_REGION]
    if missing:
        raise SystemExit(f"Missing region assignment: {missing}")

    out = {
        "viewBox": f"0 0 {VIEW_W} {VIEW_H}",
        "features": features,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {len(features)} features)")


if __name__ == "__main__":
    main()
