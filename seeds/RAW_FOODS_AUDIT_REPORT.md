# Báo cáo audit thực phẩm sống / tươi

Tổng cohort: **130** món

- OK: **130**
- REVIEW: **0**
- FIX: **0**
- Staples AI trong cohort: **13**

## Quy tắc phân loại

- **OK:** Atwater/field sync ổn; đối chiếu ngoài Δkcal ≤10% và Δprotein ≤15%
- **REVIEW:** outlier category hoặc Δkcal 10–25% / thiếu nguồn ngoài
- **FIX:** Atwater fail, desync field/DB, hoặc Δkcal >25%

## Staples AI

| Slug | kcal/100g | Severity | Issues / Δkcal% |
|------|-----------|----------|-----------------|
| `ca-chua` | 18 | OK | — / — |
| `ca-hoi-atlantic-song` | 208 | OK | — / — |
| `ca-ro-phi-song` | 96 | OK | — / — |
| `cai-thao` | 16 | OK | — / — |
| `chuoi` | 89 | OK | — / — |
| `dua-leo` | 15 | OK | — / — |
| `dui-ga-khong-da-song` | 121 | OK | — / — |
| `tao` | 52 | OK | — / — |
| `thit-bo-than-song` | 150 | OK | — / — |
| `thit-lon-than-nac-song` | 120 | OK | — / — |
| `tom-the-song` | 85 | OK | — / — |
| `trung-ga-ca-qua-song` | 143 | OK | — / — |
| `uc-ga-khong-da-song` | 110 | OK | — / — |

## FIX

_Không có món FIX._

## REVIEW (top 0)

_Không có món REVIEW._

## Checklist reviewer

- Đúng trạng thái sống vs nấu chín?
- Đúng phần ăn được (fillet / có da / không da)?
- Macro hợp lý theo nhóm (rau ~15–45, thịt nạc ~100–180, cá béo ~150–250)?

Chi tiết: `RAW_FOODS_AUDIT.csv`
