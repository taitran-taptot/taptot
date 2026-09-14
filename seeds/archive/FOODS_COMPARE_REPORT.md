# Báo cáo đối chiếu dinh dưỡng (mẫu)

Nguồn đối chiếu: **USDA FoodData Central** (`api_key=DEMO_KEY`).
Đồ đóng gói VN: theo **nhãn sản phẩm điển hình** (Vinamilk, Acecook, Uniben…) — không phải USDA.

| Món TAPTOT | kcal VF | USDA query | kcal USDA | Δ kcal | Protein VF/USDA | Ghi chú |
|-------------|---------|------------|-----------|--------|-----------------|--------|
| Ức gà không da (nướng) | 165 | Chicken breast, grilled with sauce, skin | 202 | 37 | 31/21.15 | lệch — kiểm tra biến thể |
| Thịt bò thăn | 158 | BEEF TENDERLOIN | 152 | -6 | 26/20.7 | khớp tốt |
| Cá hồi Atlantic | 208 | Fish, salmon, Atlantic, farmed, raw | 871 | 663 | 20/20.4 | lệch — kiểm tra biến thể |
| Trứng gà cả quả | 155 | Egg, whole, raw | 143 | -12 | 13/12.4 | khớp tốt |
| Cơm trắng nấu | 130 | Rice, white, cooked, glutinous | 96 | -34 | 2.7/2.01 | lệch — kiểm tra biến thể |
| Chuối tiêu | 89 | Banana, raw | 97 | 8 | 1.1/0.74 | khớp tốt |
| Bơ | 160 | Avocado, raw | 160 | 0 | 2/2 | khớp tốt |
| Đậu phụ chắc | 144 | TOFU FIRM | 89.0 | -55.0 | 15.6/8.86 | lệch — kiểm tra biến thể |
| Yến mạch cán dẹt sống | 389 | Rolls, dinner, oat bran | 236 | -153 | 17/9.5 | lệch — kiểm tra biến thể |
| Khoai lang luộc | 86 | Sweet potato, boiled, fat added | 115 | 29 | 1.6/1.58 | lệch — kiểm tra biến thể |
| Tôm sú | 99 | `shrimp raw` | — | — | 24/— | lỗi API: HTTP Error 429: Too Many Requests |
| Sữa bò tươi 3.5% béo | 61 | `whole milk` | — | — | 3.2/— | lỗi API: HTTP Error 429: Too Many Requests |
| Cà rốt sống | 41 | `carrots raw` | — | — | 0.9/— | lỗi API: HTTP Error 429: Too Many Requests |
| Bông cải xanh luộc | 35 | `broccoli boiled` | — | — | 2.4/— | lỗi API: HTTP Error 429: Too Many Requests |
| Hạnh nhân | 579 | `almonds` | — | — | 21/— | lỗi API: HTTP Error 429: Too Many Requests |

## Nguồn dùng cho seed
- Thực phẩm tươi: USDA FDC–aligned + bảng TP phổ biến VN → `tags: ref:usda-vn-table`
- Đóng gói: nhãn SP VN điển hình → `tags: ref:nhan-sp-vn` (`is_verified: false`)
- Open Food Facts: thử lúc chạy; nếu 503 thì bỏ qua (không chặn import)
