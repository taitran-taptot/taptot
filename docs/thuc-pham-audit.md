# Audit dinh dưỡng thực phẩm sống / tươi

Script: [`scripts/audit_raw_foods_nutrition.py`](../scripts/audit_raw_foods_nutrition.py)

## Mục đích

Rà soát cohort thực phẩm **sống / tươi** trong [`seeds/foods_catalog_v2.json`](../seeds/foods_catalog_v2.json):

- `prep_state == "raw"`
- Rau củ quả tươi (`trai-cay-rau-cu`, không phải `cooked`)
- Loại trừ món nấu (`-luoc`, `-nau`, `-chien`, …)

Kiểm tra:

1. **Nội bộ** — Atwater (`4P+4C+9F`), đồng bộ `kcal_100g` ↔ `calories` khi khẩu phần 100g, macro ≤ 100g
2. **Ngoài** (tuỳ chọn) — USDA FoodData Central (FDC by ID / search) + bảng [`seeds/refs/vdd_vn_staples.json`](../seeds/refs/vdd_vn_staples.json)

## Chạy

```bash
# Chỉ kiểm tra nội bộ (nhanh, không gọi mạng)
python scripts/audit_raw_foods_nutrition.py

# Đối chiếu USDA + VDD (cần mạng; cache tại seeds/.cache/fdc/)
python scripts/audit_raw_foods_nutrition.py --external

# So sánh thêm với SQLite local (nếu có)
python scripts/audit_raw_foods_nutrition.py --db path/to/taptot.db
```

Biến môi trường:

- `USDA_API_KEY` — khuyến nghị (tránh rate-limit `DEMO_KEY`)

Output:

- `seeds/RAW_FOODS_AUDIT.csv`
- `seeds/RAW_FOODS_AUDIT_REPORT.md`

## Phân loại

| Severity | Ý nghĩa |
|----------|---------|
| **OK** | Atwater/field sync ổn; nếu có ref ngoài thì Δkcal ≤10% và Δprotein ≤15% |
| **REVIEW** | Outlier category hoặc Δkcal 10–25% / biến thể (vd. ức vịt farmed vs wild) |
| **FIX** | Atwater fail, desync field, hoặc Δkcal >25% so với ref hợp lệ |

Lỗi API / thiếu match USDA **không** tự nâng thành REVIEW/FIX (tránh nhiễu).

## Sửa dữ liệu

1. Sửa tuple trong [`scripts/generate_foods_catalog_v2.py`](../scripts/generate_foods_catalog_v2.py) nếu món còn trong generator
2. Patch [`seeds/foods_catalog_v2.json`](../seeds/foods_catalog_v2.json) (catalog đang dùng runtime)
3. Gắn `source_ref` dạng `usda:{fdc_id}` khi đã xác nhận FDC
4. Đồng bộ DB:

```bash
python scripts/patch_foods_catalog_v2_sqlite.py
# hoặc
python scripts/patch_foods_catalog_v2_postgres.py
```

5. Chạy lại audit — mục tiêu **0 FIX** trong cohort sống

## Thêm món sống mới

1. Thêm vào generator / JSON với `prep_state: "raw"`, `kcal_100g` + macro /100g
2. `serving_grams: 100` và `calories` = `kcal_100g`
3. Chạy `python scripts/audit_raw_foods_nutrition.py` — phải không FIX
4. (Tuỳ chọn) `--external` và cập nhật VDD nếu USDA không có (thực phẩm VN)

## Regression

```bash
cd api && pytest tests/test_raw_foods_audit.py -q
```

Test kiểm tra: không có FIX nội bộ, snapshot kcal staples AI, và `source_ref` đã pin cho vài cut thịt chính.

## Lưu ý

- Plan / thực đơn đã generate **không** tự cập nhật calo khi sửa foods — cần tạo lịch mới nếu muốn số liệu mới.
- Cache FDC (`seeds/.cache/`) đã gitignore.
