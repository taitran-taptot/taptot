# TAPTOT API

REST API CRUD cho toàn bộ database TAPTOT — thiết kế layered, bảo mật, scale ~10k users.

## Kiến trúc

```
api/app/
├── main.py
├── core/           config, db, security, deps, permissions, pagination
├── models/         SQLAlchemy models (entities.py)
├── schemas/        auth.py + dynamic.py (auto Pydantic)
├── repositories/   generic CRUD + row-level security
├── services/       auth, search, enrollment, calculator, email, ai, payment, export, media, admin
└── api/v1/
    ├── auth.py
    ├── domain.py       search, programs, calculators, enrollments, ai, payments, exports, media, admin, health
    ├── crud_factory.py
    └── registry.py
```

## Chạy local

```powershell
cd api
pip install -r requirements.txt
copy .env.example .env   # set DATABASE_URL PostgreSQL
uvicorn app.main:app --reload --port 8000
python ../scripts/test_api.py
```

Docs: http://localhost:8000/docs

## Endpoints

| Prefix | Policy | Mô tả |
|--------|--------|-------|
| `/api/v1/auth/*` | Public / Auth | Đăng ký, đăng nhập, refresh, logout, OAuth |
| `/api/v1/exercises`, `/foods`, `/programs`… | Public read | Catalog — ai cũng đọc được |
| `/api/v1/daily-plans`, `/workout-sessions`… | Owner | Chỉ user sở hữu |
| `/api/v1/trainer-*` | Trainer | PT quản lý client |
| `/api/v1/users` | Admin | Quản trị |

### Auth endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/auth/register` | Đăng ký |
| `POST` | `/auth/login` | Đăng nhập |
| `POST` | `/auth/refresh` | Refresh token (có rotate) |
| `POST` | `/auth/logout` | Thu hồi 1 session |
| `POST` | `/auth/logout-all` | Thu hồi tất cả session |
| `GET` | `/auth/me` | Thông tin user |
| `PATCH` | `/auth/me` | Cập nhật tên / email |
| `POST` | `/auth/change-password` | Đổi mật khẩu |
| `POST` | `/auth/forgot-password` | Gửi link reset (dev: trả token) |
| `POST` | `/auth/reset-password` | Reset mật khẩu bằng token |
| `POST` | `/auth/verify-email` | Xác thực email |
| `POST` | `/auth/resend-verification` | Gửi lại email xác thực |
| `GET` | `/auth/oauth/{provider}/authorize` | URL đăng nhập Google/Facebook |
| `POST` | `/auth/oauth/{provider}/callback` | Callback OAuth → JWT |

Mỗi resource catalog/user có: `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}` (tuỳ policy).

List catalog hỗ trợ filter query: `?body_part=`, `?category_id=`, `?equipment=`, v.v.

### Domain endpoints (v2)

| Method | Endpoint | Auth | Mô tả |
|--------|----------|------|-------|
| `GET` | `/health/deep` | Public | Health + DB ping |
| `GET` | `/search/exercises?q=` | Public | Tìm bài tập (ILIKE) |
| `GET` | `/search/foods?q=` | Public | Tìm thực phẩm |
| `GET` | `/programs/{id}/detail` | Public | Program + days + exercises nested |
| `POST` | `/calculators/bmi` | Auth | BMI |
| `POST` | `/calculators/tdee` | Auth | TDEE |
| `POST` | `/calculators/macros` | Auth | Macros |
| `POST` | `/calculators/full` | Auth | BMI + TDEE + macros + log |
| `POST` | `/enrollments` | Auth | Ghi danh program |
| `GET` | `/enrollments/active` | Auth | Enrollment đang active |
| `GET` | `/enrollments/{id}/today` | Auth | Bài tập hôm nay |
| `POST` | `/enrollments/{id}/complete-day` | Auth | Hoàn thành ngày |
| `POST` | `/enrollments/{id}/start-session` | Auth | Bắt đầu buổi tập |
| `POST` | `/ai/generate-workout-schedule` | Auth | Sinh lịch tập AI đầy đủ (mock nếu chưa có OpenAI key) |
| `POST` | `/ai/qa` | Auth | Hỏi đáp AI |
| `GET` | `/ai/usage` | Auth | Quota AI tháng này |
| `POST` | `/payments/checkout` | Auth | Tạo checkout (VNPay scaffold) |
| `POST` | `/payments/webhook/{provider}` | Public | Webhook thanh toán |
| `POST` | `/exports` | Auth | Export JSON (daily plan, v.v.) |
| `GET` | `/exports/{id}` | Auth | Trạng thái export |
| `POST` | `/media/upload` | Admin | Upload file |
| `GET` | `/admin/stats` | Admin | Dashboard thống kê |

Static files: `/media/*` phục vụ thư mục upload.

## Security

- **JWT** access (30 phút) + refresh (7 ngày)
- **bcrypt** password hashing
- **Row-level ownership** (`user_id`, `trainer_id`)
- **Role-based access**: user / trainer / admin
- **Rate limiting**: 100 req/phút/IP (in-memory; set `REDIS_URL` cho multi-instance)
- **CORS** configurable
- **Sensitive fields** (`password_hash`, `token_hash`) không bao giờ trả về API

## Scale 10k users

| Giai đoạn | Hành động |
|-----------|-----------|
| Local | PostgreSQL + `DATABASE_URL` trong `.env` |
| 10k+ MAU | Connection pool, Redis rate limit, CDN static |
| Multi-instance | Redis sessions, horizontal scaling behind load balancer |

## Alembic

```powershell
cd api
alembic upgrade head
```

Schema chính vẫn tạo qua `scripts/setup_db_postgres.py`; Alembic dùng cho migration incremental sau này.

## Thêm resource mới

1. Thêm model vào `models/entities.py`
2. Thêm `ResourceConfig` vào `api/v1/registry.py`
3. Xong — CRUD tự sinh

## Ví dụ

```bash
# Public — list exercises
curl "http://localhost:8000/api/v1/exercises?page=1&page_size=10"

# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"password123","display_name":"User"}'

# Owner — create daily plan
curl -X POST http://localhost:8000/api/v1/daily-plans \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title_vi":"Lịch tuần 1","source":"manual"}'
```

## Ma trận lịch (450 case → Excel)

Pytest **không** gọi OpenAI (90 ô split + recipe warmup):

```powershell
cd api
python -m pytest tests/test_schedule_case_matrix.py -q
```

Generate thật (cần `OPENAI_API_KEY` trong `api/.env` + DB catalog). Không ghi 450 plan vào DB. Khoảng 1.5–4 giờ cho đủ 450 case. Chạy **từ root repo**:

```powershell
# Smoke 3 case
python scripts/export_schedule_matrix_xlsx.py --limit 3

# Full 450 (tiếp tục nếu bị ngắt)
python scripts/export_schedule_matrix_xlsx.py --resume
```

Kết quả: `scripts/data/schedule_matrix_results.xlsx` (sheet Cases / Buoi / BaiTap). Checkpoint: `scripts/data/schedule_matrix_checkpoint.jsonl`.
