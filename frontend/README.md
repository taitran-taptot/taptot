# TAPTOT Frontend (Next.js)

Next.js 16 App Router + React 19 + TypeScript + Tailwind v4. Gọi FastAPI qua `/api/v1`.

## Surfaces chính

| Route | Chức năng |
|-------|-----------|
| `/` | Landing TAPTOT |
| `/batdau` | Wizard sinh lịch AI |
| `/kho-bai-tap`, `/bai-tap` | Kho bài tập |
| `/kho-thuc-pham`, `/thuc-an`, `/mon-truyen-thong` | Kho thực phẩm, quầy nguyên liệu, món truyền thống |
| `/may-tinh-calo` | Máy tính calo (client-side Mifflin–St Jeor) |
| `/mua-dung-cu` | Shop |
| `/kiemtratheluc` | Kiểm tra thể lực (MediaPipe) |
| `/thu-thach-100-ngay` | Thử thách 100 ngày |
| `/tai-khoan/*` | Account shell, lịch, đơn hàng, admin |

`/tao-lich-tap/tu-tao` — tự tạo lịch (route ẩn, không nằm trên nav chính).

## Chạy

Backend port 8000 trước:

```powershell
cd frontend
npm install
npm run dev
```

http://localhost:3000

## Cấu hình

`.env.local`:

- `NEXT_PUBLIC_API_BASE` — mặc định proxy `/api/v1`
- `NEXT_PUBLIC_REQUIRE_REDEEM_CODE` — cổng mã quà wizard
