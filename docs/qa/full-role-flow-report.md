# Báo cáo kiểm thử full luồng khách, admin, HLV, CTV

Ngày chạy: 2026-11-07. Bộ case: [docs/qa/full-role-flow-testcases.md](full-role-flow-testcases.md).

Không có case nào được ghi Pass chỉ vì đã đọc code. Pass dưới đây gắn với một lần chạy pytest, Playwright, hoặc thao tác trên app local.

## Môi trường

- API local `http://127.0.0.1:8000`, `app_env=development`, database `localhost/taptot`.
- Frontend local `http://localhost:3000`.
- `SEPAY_WEBHOOK_API_KEY` trống. `TURNSTILE_SECRET_KEY` trống. `REQUIRE_REDEEM_CODE_FOR_GENERATE` đang tắt trên process đang chạy.
- STK local đang là giá trị mặc định trong code `0000000000`, chủ tài khoản `TAPTOT`, ngân hàng hiển thị MB Bank. QR VietQR vẫn được dựng.
- Pytest dùng SQLite trong bộ nhớ, không đụng database local.
- Playwright mock API, tái sử dụng frontend đang chạy.

Dữ liệu tạo trên database local rồi thu hồi phần đơn:

- Tài khoản `qa-flow-admin@example.com`, `qa-flow-hlv@example.com`, `qa-flow-ctv@example.com` (mã `QAFLOW`, 10%). Email `.local` bị API từ chối vì validator email, nên đã đổi sang `example.com`.
- Đơn `TAPTOT-KZHO5` (id 44), sản phẩm Tạ đơn id 24, giá 500.000đ. Sau khi kiểm tra đã hủy: tồn 12 về 13, mã tem từ `unused` thành `void`.
- Lịch HLV id 91, tiêu đề `QA Flow HLV 20261107`, share token `qP8L-6FcW7gCE0YCxqLDEQ`, còn trên database.

## Kết quả tự động

| Nguồn | Kết quả |
|---|---|
| `python -m pytest` các file four-role, shop, promo, redeem, auth cookies, admin stats, main-flow regression, pushup | **104 passed, 1 xfailed**, 288.88s, exit 0 |
| Playwright `public`, `content`, `shop-cod`, `shop-guest`, `plan`, `plan-guest`, `contact-feedback`, `staff` | **40 passed**, 1.8 phút, exit 0 |

Xfail đúng một test: `test_admin_cannot_skip_or_reverse_fulfillment_states`, `strict=True`, lý do `KNOWN-ADM-008`. Test này kỳ vọng `BadRequestError` khi nhảy `awaiting_confirm` thẳng `completed`. Xfail có nghĩa assertion đó vẫn thất bại. Đây là lỗi đã biết, ghi ở BUG-001, không tính là Pass.

## Đối chiếu case

### Pass bằng pytest

Các file đã chạy khóa các expected sau. Chi tiết assert nằm trong từng file test.

- KH-AUTH-01, KH-AUTH-03, KH-AUTH-04: đăng ký 403, role `user` 403, sai mật khẩu 401.
- KH-SHOP-03 đến KH-SHOP-08, KH-SHOP-10 đến KH-SHOP-17: COD, biên SĐT và địa chỉ, tồn, idempotency replay và conflict.
- KH-PAY-03, KH-PAY-04, KH-PAY-05, KH-PAY-06: tra cứu đúng, sai, hai đơn một số, chuẩn hóa `84`.
- KH-PAY-07, KH-PAY-08 trên SQLite test: SePay khớp tiền thì `paid`, sai tiền hoặc thiếu mã hoặc chiều ra thì không khớp, thiếu API key thì 401. Môi trường local không lặp lại được nhánh khớp vì webhook chưa cấu hình.
- KH-PROMO-01 đến KH-PROMO-05 phía API: promo 10% ra 450.000đ, cộng vé, sàn 0đ, vé giả hoặc đã dùng, biên rep và plank.
- KH-REDEEM-01 đến KH-REDEEM-04: lookup, đốt mã, dùng lại 403, mã `1`, hủy đơn void mã và không đụng đơn kia.
- KH-PLAN-04, KH-PLAN-05, KH-PLAN-06: challenge qua `POST /plans` khi chưa login là 401, export PDF 200, sửa share khi chưa login là 401.
- KH-CONTENT-02, KH-CONTENT-03, KH-CONTENT-04: lead, góp ý thiếu link, bài tập riêng không ra search.
- AD-AUTH-02, AD-AUTH-04, AD-STAFF-01 đến AD-STAFF-06, AD-ORDER-01, AD-ORDER-02, AD-ORDER-04 đến AD-ORDER-09, AD-PRINT-01, AD-CAT-02, AD-CAT-03, AD-STATS-01 đến AD-STATS-04, AD-LEAD-01, AD-PLAN-01.
- HLV-ISO-01, HLV-EX-01, HLV-EX-02, HLV-DENY-01.
- CTV-STATS-01, CTV-STATS-02, CTV-STATS-03, CTV-REDACT-01, CTV-DENY-01, CTV-DENY-02.
- XR-01 đến XR-08 trong `test_four_role_full_flow.py`. XR-09 tạo đơn `awaiting_transfer` có trong cùng test. Nhánh SePay `paid` của XR-09 nằm ở `test_shop_checkout.py`, không chạy trên webhook local.

### Pass bằng Playwright (UI mock)

- KH-AUTH-02 và staff signup: `/dang-ky` có chữ đăng ký đã đóng.
- KH-SHOP-01, KH-SHOP-02, KH-SHOP-09, KH-SHOP-12 trên form: ba kit và alias, giỏ tăng rồi xóa, promo sai, COD 450.000đ không mở trang chuyển khoản.
- KH-PAY-03, KH-PAY-04 trên UI mock: tra cứu thấy mã và trạng thái chờ xác nhận; mã lạ báo không tìm thấy.
- KH-PLAN-01, KH-PLAN-02, KH-PLAN-05: wizard tới `/lich/{token}` và không vào thanh toán; mã sai ở lại cổng; xuất PDF không báo thất bại.
- KH-CONTENT-01: các trang công khai, calo, bài tập, món, nấu, kiến thức, sự kiện không tự bật camera.
- KH-CONTENT-02 form liên hệ và góp ý có xác nhận đã gửi.
- AD-AUTH-01, HLV-AUTH-01, HLV-AUTH-02, CTV-AUTH-01 trên mock: admin vào thống kê và đơn; HLV chỉ ba tab; CTV chỉ mã và mật khẩu.

### Pass trên app local đang chạy

- KH-AUTH-02: `/dang-ky` heading `Đăng ký đã đóng`. Không có ô email hay mật khẩu. Nội dung nói HLV và cộng tác viên do admin thêm.
- KH-PAY-02: `/don-hang/thanh-toan?code=TAPTOT-KZHO5&phone=0901999001` hiện mã đơn, số tiền `450.000 ₫`, nội dung `SEVQR TAPTOTKZHO5`, QR `img` alt `QR chuyển khoản`. Không có nút khách tự xác nhận đã trả.
- KH-SHOP-03 và KH-PROMO-01 trên API đang chạy: HTTP 201, `awaiting_confirm`, `awaiting_transfer`, `promo_discount_vnd=50000`, `total_vnd=450000`, `Idempotency-Replayed: false`.
- KH-SHOP-04 và KH-TRACK-02: response đặt hàng và `POST /shop/orders/track` không có `gift_codes`. Database có đúng 1 mã tem `unused` cho đơn quantity 1.
- KH-PAY-01: `payment_status` giữ `awaiting_transfer` cho đến lúc hủy. Không có API khách đánh dấu `paid`.
- AD-PRINT-01: admin cookie sau confirm-password tải PDF `application/pdf` 404624 byte và PNG `image/png` 77384 byte. Không cookie: 401.
- AD-ORDER-04 trên đơn local còn `awaiting_confirm`: hủy xong `cancelled`, tồn Tạ đơn 12 về 13, mã tem `void`.
- HLV-AUTH-01 và HLV-AUTH-02: login HLV vào `/tai-khoan`, chỉ `Lịch của tôi`, `Bài tập của tôi`, `Đổi mật khẩu`. `/tai-khoan/quan-tri` bị đưa về `/tai-khoan?tab=ke-hoach`.
- HLV-PLAN-01: form tạo lịch với cao 170, nặng 70, giới Nam, ghi chú `Ghi chu rieng`. App mở `/tai-khoan/lich/91`. `GET /plans/share/qP8L-6FcW7gCE0YCxqLDEQ` không cần cookie và body có chuỗi ghi chú.
- HLV-DENY-01 một điểm: `GET /admin/stats` bằng cookie HLV trả 403.
- CTV-AUTH-01 và CTV-STATS-01 trên UI thật: chỉ tab mã và đổi mật khẩu, mã `QAFLOW`, mức 10%, chữ `1 đơn đã dùng mã · tổng đã giảm 0 ₫`. Khối thống kê ngày 07/11/2026: số đơn 1, tổng giá đơn `0 ₫`, tổng đã giảm `0 ₫`, trong khi dòng đơn vẫn hiện `450.000 ₫` và `Chờ xác nhận`.
- CTV-REDACT-01: JSON `GET /collaborator/promo/stats?period=month&on=2026-11` có tên người nhận và tỉnh, không có phone, ward, address line.
- AD-AUTH-01 trên app thật: login admin vào `/tai-khoan/quan-tri`. Có đủ 13 mục, tab đang mở là thống kê shop.
- KH-PLAN-03 một phần: `/tao-lich-tap/tu-tao` mở được khi chưa login, heading `Tự tạo lịch tập`, bốn bước Thông tin, Thực đơn, Bài tập, Hoàn tất. Chưa bấm hết bốn bước để lưu share.
- KH-CONTENT-01 một phần trên app thật: trang chống đẩy mở, có nút `Bật camera`, chưa tự bật camera. Quy tắc trên trang khớp 0,2% mỗi cái và trần 100 cái = 20%.

## Blocked

| ID | Lý do | Đã thấy |
|---|---|---|
| KH-PAY-07 nhánh khớp tiền trên server local | Webhook SePay chưa cấu hình | `POST /shop/payments/sepay` trả 401. Đơn không thành `paid` |
| KH-PAY-08 sai số tiền, thiếu mã, chiều tiền ra trên server local | Cùng 401 trước khi vào nhánh so khớp | Ma trận này Pass trên pytest, không chạy được trên process local |
| KH-FAM-01, KH-FAM-02, KH-FAM-03 | Không có Turnstile secret trên process local. Lần gọi thử còn thiếu `height_cm` và `weight_kg` nên chỉ nhận 422 schema, chưa tới captcha | Không kết luận Pass hay Fail cho trần 3/5 và các chế độ bị cấm |
| KH-PROMO-05 phần camera | Trang có nút bật camera. Không có người và camera để hoàn thành rep hoặc plank | Luật phần trăm Pass ở `test_pushup_challenge.py` |
| KH-PLAN-03 phần bấm lưu bốn bước | Wizard mở tới bước Thông tin | Chưa có share token tạo từ wizard khách trên app thật |

## Lỗi đã chứng minh

### BUG-001

- **Bug Title:** Admin đổi trạng thái giao hàng nhảy cóc và đi lùi được.
- **Environment:** Pytest SQLite, `api/tests/test_main_flow_regression.py`, 2026-11-07. Không gọi lại trên đơn local.
- **Preconditions:** Đơn vừa checkout, `order_status=awaiting_confirm`.
- **Steps to Reproduce:** `ShopService.update_order_status(order_id, "completed")`.
- **Expected Result:** `BadRequestError`. Đơn vẫn `awaiting_confirm`. Đây là expected của test `test_admin_cannot_skip_or_reverse_fulfillment_states`.
- **Actual Result:** Test xfail `strict`. Hàm không ném `BadRequestError` với bước nhảy này. `update_order_status` gán thẳng trạng thái nếu đơn chưa `cancelled` hoặc `returned`.
- **Severity:** Major.
- **Priority:** High.
- **Evidence:** Pytest `104 passed, 1 xfailed`. Marker reason `KNOWN-ADM-008: fulfillment transition matrix is not enforced`.
- **Reproducibility:** Ổn định trong suite. Chưa tái hiện bằng tay trên database local trong lần này.

Không phát hiện lỗi mới ngoài BUG-001. Các lệch dưới đây chưa đủ căn cứ để gọi là defect.

## Rủi ro, chưa phải defect

- Khách không nhận mã tem trong JSON checkout và trang thành công. Mã chỉ có ở PDF/PNG admin. Đơn local quantity 1 có đúng một mã, và track không trả mã. Đúng với code hiện tại. Rủi ro vận hành nếu tem in là đường giao mã duy nhất.
- Ghi chú hồ sơ khách của HLV có trong `GET /plans/share/{token}` không cần đăng nhập. Đã thấy chuỗi `Ghi chu rieng` của lịch 91. Test bốn vai trò đang coi đây là hành vi hiện tại. Rủi ro riêng tư nếu ghi chú được xem là dữ liệu kín.
- STK local `0000000000` là default trong `api/app/core/config.py`. QR vẫn trỏ tới số này. Không kết luận production đang dùng default.

## Chưa đủ thông tin

- Không có tài liệu nghiệp vụ ngoài repo nói khách hàng phải có tài khoản. Code đóng đăng ký và từ chối login role `user`. Bộ case bám code.
- Không có quy tắc sản phẩm viết ngoài code cho việc nhảy trạng thái BUG-001. Expected trong báo cáo lấy từ test đang xfail, không tự đổi thành “cho phép nhảy”.
- `POST /plans` với cờ challenge khi thiếu `title_vi` trả 422, chưa phải 401. Case KH-PLAN-04 cần body đủ field rồi mới kết luận 401. Pytest trong `test_four_role_full_flow.py` đã có assertion 401 cho request đủ dạng. Lần gọi local này không đủ field nên không dùng làm bằng chứng 401.
- Chưa kiểm Google hoặc Facebook login, hoa hồng CTV, và `/api/v1/payments/*`. Các mục này nằm ngoài phạm vi.

## Việc còn trên database local

Đơn `TAPTOT-KZHO5` đã hủy và tồn đã hoàn. Lịch 91 và ba tài khoản `qa-flow-*@example.com` còn lại. Mã `QAFLOW` vẫn gán cho CTV đó.
