# TAPTOT Database

Nền tảng fitness Việt Nam: catalog bài tập / thực phẩm, sinh lịch AI, shop, trainer, admin.

**Runtime DB: PostgreSQL.** SQLite chỉ còn dual-dialect trong `schema/sqlite/` và nhánh startup migrations.

## Cấu trúc

```
taptot-db/
├── schema/postgresql/   # Schema chính (001–031)
├── schema/sqlite/       # Mirror (không đủ file so với PG)
├── seeds/               # Catalog JSON/CSV
├── api/                 # FastAPI
└── frontend/            # Next.js
```

Schema sống được áp dụng lúc API start (`ensure_*` trong `api/app/core/migrations`). Alembic chỉ là marker.

## Yêu cầu

- Python 3.10+
- PostgreSQL
- Node.js (frontend)

## Setup

Đặt `DATABASE_URL` trong `api/.env`:

```
DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@localhost:5432/taptot
```

```powershell
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Lần đầu, startup thread tạo schema + seed catalog. Docs: http://localhost:8000/docs

## Catalog (ước lượng)

| Bảng | Mô tả |
|------|--------|
| `exercises` | Bài tập + copy tiếng Việt |
| `foods` + `food_aliases` + `food_portions` | Catalog v2 nguyên liệu / món |
| `knowledge_articles` | Kho kiến thức |
| `user_daily_plans` | Lịch tập (AI / thủ công) |
| shop / redeem | Sản phẩm và mã quà tặng |

Programs / enrollments / schedule frames đã drop (`031_drop_unused_legacy.sql`).

## REST API

Xem [`api/README.md`](api/README.md).

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

http://localhost:3000 — landing TAPTOT, `/batdau` sinh lịch, `/kho-thuc-pham` kho thức ăn.
