# TAPTOT API

REST API FastAPI — catalog, auth, sinh lịch AI, plans, shop, trainer, admin.

## Kiến trúc

```
api/app/
├── main.py
├── core/           config, db, security, deps, migrations package
├── models/         SQLAlchemy (entities.py)
├── schemas/        auth, plans, dynamic CRUD
├── repositories/   generic CRUD + ownership
├── services/       domain services + workout_generation/
└── api/v1/
    ├── auth.py
    ├── ai.py
    ├── domain.py       health, search, plans, shop, admin, media, …
    ├── crud_factory.py
    └── registry.py     generic catalog/user CRUD
```

Payments / calculators / generic exports routers còn file nhưng **không mount** (FE không gọi). Plans export qua `/my-plans/{id}/export`.

## Chạy local

```powershell
cd api
pip install -r requirements.txt
copy .env.example .env   # set DATABASE_URL PostgreSQL
uvicorn app.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs (chỉ khi `DEBUG` và không phải production)

## Endpoints chính

| Prefix | Policy | Mô tả |
|--------|--------|-------|
| `/api/v1/auth/*` | Public / Auth | Đăng ký, đăng nhập, refresh |
| `/api/v1/exercises`, `/foods`, `/equipment` | Public read | Catalog registry |
| `/api/v1/search/*` | Public | Tìm bài tập / thực phẩm |
| `/api/v1/ai/generate-workout-schedule` | Auth optional | Sinh lịch AI |
| `/api/v1/my-plans*` | Owner | Lịch của user (kể cả restore-ai) |
| `/api/v1/shop/*` | Auth / public | Giỏ hàng, đơn, redeem |
| `/api/v1/admin/*` | Admin | Catalog admin |

## Security

- JWT access + refresh
- bcrypt
- Row-level ownership
- Role: user / trainer / admin
- Rate limit (in-memory hoặc Redis)

## Ma trận lịch

```powershell
cd api
python -m pytest tests/test_schedule_case_matrix.py -q
```
