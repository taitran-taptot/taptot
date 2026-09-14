# TAPTOT Database

Database cho nền tảng fitness Việt Nam — bài tập, thực phẩm VN (catalog v2), chương trình tập, schema MVP.

**Runtime DB: PostgreSQL** (local hoặc Supabase). SQLite không còn là đường setup mặc định.

## Cấu trúc

```
taptot-db/
├── schema/
│   ├── postgresql/         # Schema chính (dùng khi setup)
│   └── sqlite/             # Giữ cho migration dual-dialect trong API
├── seeds/                  # Dữ liệu mẫu + foods_catalog_v2.json
├── scripts/
│   ├── setup_db_postgres.py
│   ├── generate_foods_catalog_v2.py
│   └── patch_foods_catalog_v2_postgres.py
├── api/                    # FastAPI
└── frontend/               # Next.js
```

## Yêu cầu

- Python 3.10+
- PostgreSQL đang chạy
- File `exercises.json` từ [exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) (khi seed bài tập)

## Setup PostgreSQL (khuyến nghị)

```powershell
cd "C:\Users\Tran Tai\Projects\vietfit-db"
```

Đặt `DATABASE_URL` trong `api/.env`:

```
DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@localhost:5432/taptot
```

(Mã hóa ký tự đặc biệt trong password, ví dụ `@` → `%40`.)

Tạo DB + schema + seed lần đầu:

```powershell
python scripts/setup_db_postgres.py --force
```

Đồng bộ lại **chỉ catalog thực phẩm v2** (xóa catalog cũ, import curated):

```powershell
python scripts/generate_foods_catalog_v2.py
python scripts/patch_foods_catalog_v2_postgres.py
```

## Nội dung sau khi setup

| Bảng | Mô tả | Số bản ghi (ước lượng) |
|------|--------|------------------------|
| `exercises` | Bài từ dataset + difficulty | ~1.324 |
| `exercise_localizations` | Tên/hướng dẫn tiếng Việt | ~1.190+ |
| `body_part_labels` / `equipment_labels` / `muscle_labels` | Nhãn tiếng Việt | 10 + 28 + 27 |
| `foods` + `food_aliases` + `food_portions` | Catalog v2: nguyên liệu 100g + món theo tô/cái/quả | 443 foods (289 nguyên liệu / 122 món / 32 đóng gói) + 676 portions |
| `programs` + `program_day_meals` | Lộ trình + gợi ý ăn | 2 + 104 meals |
| `knowledge_articles` | Bài học SEO | 8 |
| `equipment_products` + suggestions | Affiliate dụng cụ | 6 + 182 links |
| `export_templates` | Excel free / PDF Pro | 5 |
| `subscription_plans` | Free / Pro / Pay-per-use / Trainer | 4 |

## Tra cứu mẫu

```sql
-- Catalog đang active
SELECT food_kind, COUNT(*) FROM foods WHERE status = 'active' GROUP BY food_kind;

-- Ức gà
SELECT slug, name_vi, kcal_100g, protein_100g
FROM foods
WHERE slug LIKE 'uc-ga%' AND status = 'active';

-- Calo theo khẩu phần mặc định
SELECT f.name_vi, p.label_vi, p.grams,
       ROUND(f.kcal_100g * p.grams / 100.0) AS kcal_serving
FROM foods f
JOIN food_portions p ON p.food_id = f.id AND p.is_default
WHERE f.status = 'active'
ORDER BY f.name_vi
LIMIT 20;
```

## Lưu ý bản quyền media

GIF/hình ảnh bài tập thuộc © Gym visual. Xem `NOTICE.md` trong exercises-dataset trước khi dùng thương mại.

## REST API

Backend FastAPI. Xem [`api/README.md`](api/README.md).

```powershell
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs

Ma trận QA 450 lịch (nam/nữ × buổi × phút) → Excel: xem mục **Ma trận lịch** trong [`api/README.md`](api/README.md). Chạy `python scripts/export_schedule_matrix_xlsx.py --limit 3` từ root repo.

## Frontend (Next.js)

```powershell
cd frontend
npm install
npm run dev
```

Mở http://localhost:3000 (backend port 8000). Trong **Kho thức ăn**, tìm `ức gà` hoặc `uc ga`.
