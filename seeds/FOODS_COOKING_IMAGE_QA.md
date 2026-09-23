# QA ảnh Gemini pantry (`gemini-folder-1`)

Map `001`–`056` theo thứ tự prompt / [`FOODS_COOKING_ADDED.md`](FOODS_COOKING_ADDED.md).

- `ok` = đúng món, chưa có Food catalog trùng → đưa lên site
- `sai` = ảnh không khớp tên món → không upload, prompt retry
- `trung` = đúng món nhưng đã có Food TapTot (không tính pantry) → ẩn + remap cách nấu

Tổng: **35 ok**, **5 sai**, **16 trùng**.

| # | Slug | Tên | Kết quả | Ghi chú |
|---|------|-----|---------|---------|
| 001 | `nuoc-mam` | Nước mắm | ok | Có đĩa (lệch prompt) nhưng nhận ra nước mắm |
| 002 | `nuoc-tuong` | Nước tương | ok | |
| 003 | `mam-tom` | Mắm tôm | ok | |
| 004 | `mam-ruoc` | Mắm ruốc | ok | |
| 005 | `dau-an` | Dầu ăn | ok | Không trùng `dau-oliu` |
| 006 | `duong-cat` | Đường cát trắng | ok | |
| 007 | `muoi` | Muối | ok | |
| 008 | `tieu-den` | Tiêu đen | ok | |
| 009 | `ot-hiem` | Ớt hiểm | ok | Không trùng ớt chuông |
| 010 | `giam-gao` | Giấm gạo | ok | |
| 011 | `toi` | Tỏi | trung | → `toi-ta-toi-tia` (Tỏi ta / Tỏi tía) |
| 012 | `hanh-tim` | Hành tím khô | trung | → `hanh-tim-kho` |
| 013 | `sa` | Sả | ok | |
| 014 | `gung` | Gừng | trung | → `gung-gia` |
| 015 | `rieng` | Riềng | trung | → `cu-rieng` |
| 016 | `nghe` | Nghệ tươi | trung | → `nghe-vang` |
| 017 | `la-lot` | Lá lốt | ok | |
| 018 | `la-chanh` | Lá chanh | ok | |
| 019 | `ngo-om` | Ngò om | **sai** | Giống thyme, không phải ngò om (lá vòng quanh thân) |
| 020 | `bac-ha-rau` | Bạc hà (rau canh chua) | trung | → `doc-mung-bac-ha` (Dọc mùng / Bạc hà) |
| 021 | `thi-la` | Thì là | ok | |
| 022 | `kinh-gioi` | Kinh giới | ok | |
| 023 | `toi-tay` | Tỏi tây | trung | → `toi-tay-poireau` |
| 024 | `can-tay` | Cần tây | trung | → `can-tay-da-lat` |
| 025 | `chanh-ta` | Chanh ta | **sai** | Quả to như bưởi/grapefruit, không phải chanh ta nhỏ |
| 026 | `sau-xanh` | Sấu xanh | ok | Không trùng sầu riêng |
| 027 | `ngo-gai` | Ngò gai | trung | → `mui-tau-ngo-gai` |
| 028 | `cua-dong` | Cua đồng | ok | Không trùng cua biển |
| 029 | `hen` | Hến | trung | → `hen-song-trung-truc` |
| 030 | `luon` | Lươn đồng | trung | → `luon-dong` |
| 031 | `ca-linh` | Cá linh | trung | → `ca-linh-mua-nuoc-noi` |
| 032 | `thit-trau` | Thịt trâu | ok | Không trùng thịt bò / món trâu gác bếp |
| 033 | `chan-gio-heo` | Chân giò heo | trung | → `bap-gio-heo-chan-gio-truoc` |
| 034 | `xuong-ong-bo` | Xương ống bò | ok | |
| 035 | `canh-ga` | Cánh gà | trung | → `canh-ga-nguyen-chiec-canh-tien` |
| 036 | `long-heo` | Lòng heo | ok | |
| 037 | `gan-heo` | Gan heo | ok | |
| 038 | `gau-bo` | Gầu bò | trung | → `gau-gion-bo-gau-pho` |
| 039 | `gio-bo` | Gìn bò / giò bò | trung | → `gan-bo-gan-chu-y-gan-trong` |
| 040 | `bi-heo` | Bì heo | ok | |
| 041 | `cha-trung` | Chả trứng hấp | **sai** | Giống bánh trứng nướng nhân thịt, không phải chả trứng hấp |
| 042 | `pate-gan` | Pate gan | ok | |
| 043 | `cha-lua` | Chả lụa | ok | |
| 044 | `trung-muoi` | Trứng muối | ok | Không trùng trứng vịt |
| 045 | `banh-mi` | Bánh mì | ok | |
| 046 | `banh-trang` | Bánh tráng | ok | |
| 047 | `hu-tieu` | Hủ tiếu tươi | ok | Không gộp bún/phở |
| 048 | `bot-gao` | Bột gạo | ok | |
| 049 | `bot-nang` | Bột năng | ok | |
| 050 | `dau-xanh` | Đậu xanh cà vỏ | ok | Không trùng giá đỗ |
| 051 | `dau-phong` | Đậu phộng rang | ok | |
| 052 | `nuoc-dua-tuoi` | Nước dừa tươi | **sai** | Cục thạch/jelly, không phải nước dừa lỏng |
| 053 | `banh-hoi` | Bánh hỏi | ok | |
| 054 | `banh-da` | Bánh đa đỏ | ok | |
| 055 | `soi-banh-canh` | Sợi bánh canh | **sai** | Mặt cắt rỗng hình sao (giống ống pasta), bánh canh đặc ruột |
| 056 | `mi-quang` | Mì Quảng sợi | ok | |

## Ảnh sai (retry)

1. `ngo-om` (019)
2. `chanh-ta` (025) — giữ ảnh cũ `foods/chanh-ta.jpg` nếu có
3. `cha-trung` (041)
4. `nuoc-dua-tuoi` (052)
5. `soi-banh-canh` (055)

Prompt retry: [`FOODS_COOKING_IMAGE_PROMPTS_RETRY.md`](FOODS_COOKING_IMAGE_PROMPTS_RETRY.md)

## Trùng catalog live

Ẩn slug pantry, remap bài cách nấu sang Food sẵn có. Không gộp món gần-nhưng-khác (hành tây, ớt chuông, dầu oliu, cua biển, ngao, trứng vịt, bún, bánh phở, giá đỗ).

| Pantry | Food đích |
|--------|-----------|
| `toi` | `toi-ta-toi-tia` |
| `toi-tay` | `toi-tay-poireau` |
| `hanh-tim` | `hanh-tim-kho` |
| `gung` | `gung-gia` |
| `rieng` | `cu-rieng` |
| `nghe` | `nghe-vang` |
| `can-tay` | `can-tay-da-lat` |
| `hen` | `hen-song-trung-truc` |
| `luon` | `luon-dong` |
| `ca-linh` | `ca-linh-mua-nuoc-noi` |
| `chan-gio-heo` | `bap-gio-heo-chan-gio-truoc` |
| `canh-ga` | `canh-ga-nguyen-chiec-canh-tien` |
| `bac-ha-rau` | `doc-mung-bac-ha` |
| `ngo-gai` | `mui-tau-ngo-gai` |
| `gau-bo` | `gau-gion-bo-gau-pho` |
| `gio-bo` | `gan-bo-gan-chu-y-gan-trong` |
