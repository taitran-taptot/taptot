# TAPTOT Frontend (Next.js)

Frontend cho TAPTOT — **Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS v4**. Gọi REST API FastAPI ở backend.

## Chức năng hiện có

| Route | Chức năng | API |
|-------|-----------|-----|
| `/` | **Kho bài tập** — tìm kiếm, lọc theo nhóm cơ / dụng cụ / người mới, modal chi tiết | `/search/exercises`, `/exercises/{id}`, `/body-part-labels`, `/equipment-labels`, `/muscle-labels` |
| `/thuc-an` | **Kho thức ăn** — tra cứu calo & macro món Việt, lọc theo nhóm, modal dinh dưỡng | `/search/foods`, `/foods/{id}`, `/food-categories` |
| `/may-tinh-calo` | **Máy tính calo** — BMI, BMR, TDEE, macro. Tính client-side (công thức Mifflin–St Jeor giống backend) | — |

## Chạy

Cần backend chạy trước (xem `../api/README.md`):

```powershell
cd ..\api
uvicorn app.main:app --reload --port 8000
```

Rồi chạy frontend:

```powershell
cd frontend
npm install   # lần đầu
npm run dev
```

Mở http://localhost:3000

> Frontend phải chạy ở **port 3000** vì backend chỉ cho phép origin này qua CORS. Muốn đổi port, thêm origin vào `CORS_ORIGINS` trong `api/.env`.

## Cấu hình

Sửa `.env.local`:

- `NEXT_PUBLIC_API_BASE` — URL backend (mặc định `http://localhost:8000/api/v1`).
- `NEXT_PUBLIC_GIF_BASE` — nơi host GIF bài tập. DB lưu đường dẫn tương đối `videos/xxx.gif`. Trỏ base vào đây nếu bạn có media của exercises-dataset; để trống thì hiện icon minh họa thay ảnh vỡ.

## Cấu trúc

```
frontend/src/
├── app/
│   ├── layout.tsx              # RootLayout + AppShell (nav)
│   ├── globals.css             # Tailwind v4 + theme màu brand/accent
│   ├── page.tsx                # / → Kho bài tập
│   ├── thuc-an/page.tsx        # Kho thức ăn
│   └── may-tinh-calo/page.tsx  # Máy tính calo
├── components/
│   ├── AppShell.tsx            # header + bottom nav + trạng thái API
│   ├── Modal.tsx
│   ├── ExerciseThumb.tsx       # ảnh GIF + fallback emoji
│   ├── MacroBar.tsx
│   ├── ExerciseLibrary.tsx
│   ├── FoodLibrary.tsx
│   └── Calculator.tsx
└── lib/
    ├── config.ts               # API_BASE, GIF_BASE, PAGE_SIZE
    ├── api.ts                  # fetch client có type
    ├── types.ts                # interface dữ liệu
    └── labels.ts               # difficulty, emoji, gifUrl, viNum
```

## Build production

```powershell
npm run build
npm run start
```

## Ghi chú

- Thiết kế mobile-first, tiếng Việt, nút chạm lớn, giải thích đời thường — hướng người mới/ít kinh nghiệm.
- Font **Be Vietnam Pro** nạp qua `next/font` (self-host tự động khi build).
- Các trang chức năng là Client Component (dùng state cho tìm kiếm/lọc/phân trang).
