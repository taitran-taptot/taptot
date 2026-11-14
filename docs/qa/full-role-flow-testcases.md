# Bộ test case full luồng khách, admin, HLV, CTV

Căn cứ: code TAPTOT tại thời điểm lập case (API `/api/v1`, Next.js `frontend`). Khách hàng là khách vãng lai. Ba tài khoản đăng nhập được là `admin`, `hlv`, `ctv`.

Mỗi case có đủ: Test Case ID, Test Scenario, Test Objective, Precondition, Test Steps, Test Data, Expected Result, Priority, Test Type.

Kết quả thực thi không ghi trong file này. File báo cáo thực thi là `docs/qa/full-role-flow-report.md`.

## Dữ liệu chuẩn dùng chung

Sản phẩm mẫu `QA-KIT`: `price_vnd = 500000`, `stock_qty = 10`, `is_active = true`, `shipping_fee_vnd = 0`.

Công thức tiền hàng trong `merchandise_discounts`:

- `event_vnd = subtotal * round(event_percent * 10) // 1000`
- `promo_vnd = subtotal * promo_percent // 100`
- Nếu tổng giảm vượt subtotal thì cắt promo trước, rồi cắt event. Thu không âm. Phí ship không giảm.

| Tình huống | Subtotal | Event | Promo | Event VND | Promo VND | Thu |
|---|---:|---:|---:|---:|---:|---:|
| COD + CTV 10% | 500000 | 0 | 10 | 0 | 50000 | 450000 |
| 100 rep (20%) + CTV 10% | 500000 | 20 | 10 | 100000 | 50000 | 350000 |
| 1 rep (0.2%) + CTV 10% | 500000 | 0.2 | 10 | 1000 | 50000 | 449000 |
| Plank 10% + CTV 10% | 500000 | 10 | 10 | 50000 | 50000 | 400000 |
| Event 100% + CTV 10% | 500000 | 100 | 10 | 500000 | 0 | 0 |
| SL 2 + CTV 10% | 1000000 | 0 | 10 | 0 | 100000 | 900000 |

Người nhận hợp lệ: tên `Nguyen Van A`, SĐT `0901234567`, tỉnh `Hà Nội`, phường `Phường Bến Nghé`, địa chỉ `12 Le Loi`. Quận không bắt buộc. `84901234567` chuẩn hóa thành `0901234567`.

Mã CTV `CTVQA`, 10%. Idempotency-Key hợp lệ dài 16–128, chỉ `[A-Za-z0-9._:-]`. Ví dụ `qa-flow-key-0001`.

Trạng thái đơn: `awaiting_confirm` → `packing` → `shipping` → `completed`. Đóng: `cancelled`, `returned`. Hủy được từ `awaiting_confirm`, `placed`, `packing`, `shipping`. Trả được từ `shipping`, `completed`.

## KH — Khách vãng lai

### KH-AUTH-01

- **Test Scenario:** Đăng ký công khai bị đóng trên API.
- **Test Objective:** Khách không tự tạo tài khoản.
- **Precondition:** Không cần session.
- **Test Steps:** `POST /api/v1/auth/register` với email, mật khẩu có chữ và số, tên hiển thị.
- **Test Data:** `guest@example.com` / `Secret12` / `Khach`.
- **Expected Result:** HTTP 403. Thông báo chứa `Đăng ký công khai đã đóng`. Không có user mới role `user`.
- **Priority:** High
- **Test Type:** Negative, Authorization

### KH-AUTH-02

- **Test Scenario:** Trang đăng ký không có form.
- **Test Objective:** UI khớp quy tắc đóng đăng ký.
- **Precondition:** Frontend đang chạy.
- **Test Steps:** Mở `/dang-ky`.
- **Test Data:** Không.
- **Expected Result:** Thấy chữ `Đăng ký đã đóng`. Không có ô email/mật khẩu để gửi đăng ký.
- **Priority:** High
- **Test Type:** UI, Negative

### KH-AUTH-03

- **Test Scenario:** Role `user` không đăng nhập được.
- **Test Objective:** Chỉ HLV, CTV, admin vào được hệ thống tài khoản.
- **Precondition:** Có sẵn user role `user`, mật khẩu đúng.
- **Test Steps:** `POST /api/v1/auth/login`.
- **Test Data:** Email của user legacy, mật khẩu đúng.
- **Expected Result:** HTTP 403. Message `Chỉ HLV, cộng tác viên và Admin được đăng nhập.` Không set cookie `taptot_access`.
- **Priority:** High
- **Test Type:** Authorization, Negative

### KH-AUTH-04

- **Test Scenario:** Sai mật khẩu staff.
- **Test Objective:** Không lộ việc email có tồn tại hay không qua login.
- **Precondition:** Admin tồn tại.
- **Test Steps:** `POST /api/v1/auth/login` mật khẩu sai.
- **Test Data:** Email admin đúng, password `WrongPass1`.
- **Expected Result:** HTTP 401. Message `Invalid email or password`.
- **Priority:** High
- **Test Type:** Negative, Security

### KH-AUTH-05

- **Test Scenario:** Quên mật khẩu không tiết lộ email.
- **Test Objective:** Email không tồn tại và email tồn tại cùng một câu trả lời.
- **Precondition:** Một email staff tồn tại. `debug` không bật kèm `email_provider=console` trên môi trường cần giữ bí mật (nếu bật, response được phép có `reset_url` — ghi nhận môi trường, không coi là lộ ở production).
- **Test Steps:** `POST /api/v1/auth/forgot-password` hai lần: email không có và email staff.
- **Test Data:** `khong-co@example.com`, email admin.
- **Expected Result:** Cả hai cùng thông điệp thành công, không nói email có hay không. Token reset sống 1 giờ. Token mới làm token cũ hết hiệu lực.
- **Priority:** Medium
- **Test Type:** Security, Negative

### KH-SHOP-01

- **Test Scenario:** Khách xem ba bộ dụng cụ.
- **Test Objective:** Catalog công khai chỉ sản phẩm đang bán, slug Việt và alias tiếng Anh cùng một sản phẩm.
- **Precondition:** Ba kit active: `day-khang-luc`, `ta-don`, `xa-don-va-vong-treo`.
- **Test Steps:** Mở `/mua-dung-cu`. Gọi `GET /api/v1/shop/products`. Mở alias `/mua-dung-cu/dumbbell`.
- **Test Data:** Slug alias `dumbbell`, `resistance-band`, `bar-and-rings`.
- **Expected Result:** Danh sách chỉ sản phẩm `is_active`. Alias điều hướng tới slug Việt tương ứng. Sản phẩm inactive không có trong list khách. Admin vẫn xem được inactive qua API chi tiết.
- **Priority:** High
- **Test Type:** Functional, UI

### KH-SHOP-02

- **Test Scenario:** Giỏ khách trên trình duyệt.
- **Test Objective:** Giỏ không cần tài khoản và không gọi giỏ server.
- **Precondition:** Chưa đăng nhập. `localStorage` key `taptot.guest_cart.v1` trống.
- **Test Steps:** Thêm dây kháng lực. Tăng số lượng. Xóa hết giỏ. Mở `/gio-hang`.
- **Test Data:** Một sản phẩm active.
- **Expected Result:** Giỏ lưu local. Tăng số lượng cập nhật dòng. Giỏ trống không gửi `POST /shop/orders`. Không có request thành công tới `GET/POST /shop/cart`.
- **Priority:** High
- **Test Type:** Functional, UI

### KH-SHOP-03

- **Test Scenario:** Đặt COD đủ dữ liệu.
- **Test Objective:** Happy path thanh toán khi nhận hàng.
- **Precondition:** `QA-KIT` tồn 10. Khách chưa login. Header `Idempotency-Key` hợp lệ.
- **Test Steps:** `POST /api/v1/shop/orders` với người nhận hợp lệ, `payment_method=cod`, 1 sản phẩm, không promo.
- **Test Data:** Người nhận chuẩn. Giá 500000. Key `qa-flow-key-0001`.
- **Expected Result:** HTTP 201. `order_status=awaiting_confirm`. `payment_status=cod`. `shipping_fee_vnd=0`. `total_vnd=500000`. `public_code` khớp `TAPTOT-` + 5 ký tự `A-Z0-9`. UI COD chuyển `/don-hang/thanh-cong` và hiện mã, không mở `/don-hang/thanh-toan`.
- **Priority:** Critical
- **Test Type:** Functional, Happy path

### KH-SHOP-04

- **Test Scenario:** Tồn và mã kích hoạt theo số lượng.
- **Test Objective:** Trừ tồn lúc tạo đơn và phát một mã `TT-` cho mỗi đơn vị.
- **Precondition:** Tồn 10. Checkout SL 2.
- **Test Steps:** Đặt COD SL 2. Admin xem đơn kèm gift codes.
- **Test Data:** `quantity=2`, giá 500000.
- **Expected Result:** Tồn còn 8. Đúng 2 mã dạng `TT-XXXX-XXXX`, alphabet không có I, L, O, 0, 1. Response checkout của khách không chứa các mã tem này. `gifts` trên URL thành công là tổng số lượng (2), không phải danh sách mã.
- **Priority:** Critical
- **Test Type:** Data, Integration

### KH-SHOP-05

- **Test Scenario:** Số điện thoại không hợp lệ.
- **Test Objective:** Chặn SĐT sai trước khi tạo đơn và trừ tồn.
- **Precondition:** Tồn 10.
- **Test Steps:** Checkout lần lượt SĐT rỗng, `090123456` (9 số), `09012345678` (11 số), `abcdefghij`.
- **Test Data:** Các giá trị trên. Các field khác hợp lệ.
- **Expected Result:** Mỗi lần HTTP 400, message `Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0`. Tồn vẫn 10. Không có `public_code` mới. UI chặn trước submit với thông báo 10 chữ số và không gọi POST đơn.
- **Priority:** High
- **Test Type:** Negative, Boundary

### KH-SHOP-06

- **Test Scenario:** Tên người nhận quá ngắn.
- **Test Objective:** Tên sau trim phải từ 2 ký tự.
- **Precondition:** Tồn 10.
- **Test Steps:** Checkout tên `A`, tên chỉ khoảng trắng, tên rỗng.
- **Test Data:** `recipient_name` như trên.
- **Expected Result:** HTTP 400 `Họ và tên người nhận bắt buộc`. Tồn không đổi.
- **Priority:** High
- **Test Type:** Negative, Boundary

### KH-SHOP-07

- **Test Scenario:** Thiếu tỉnh hoặc phường.
- **Test Objective:** Tỉnh và phường bắt buộc. Quận được bỏ trống.
- **Precondition:** Tồn 10.
- **Test Steps:** Checkout thiếu `province_name`. Lần khác thiếu `ward_name`. Lần khác đủ tỉnh và phường, `district_name` rỗng.
- **Test Data:** `Tỉnh/Thành phố` trống hoặc `Phường/Xã` trống.
- **Expected Result:** Thiếu tỉnh: 400 `Tỉnh/Thành phố bắt buộc`. Thiếu phường: 400 `Phường/Xã bắt buộc`. Quận trống và phần còn lại hợp lệ: 201, đơn được tạo.
- **Priority:** High
- **Test Type:** Negative, Boundary

### KH-SHOP-08

- **Test Scenario:** Địa chỉ quá ngắn.
- **Test Objective:** Địa chỉ sau trim ít nhất 3 ký tự.
- **Precondition:** Tồn 10.
- **Test Steps:** Checkout `address_line` = `12` và `   `.
- **Test Data:** Độ dài 2 và rỗng.
- **Expected Result:** HTTP 400 `Địa chỉ số nhà / đường bắt buộc`. Tồn không đổi.
- **Priority:** Medium
- **Test Type:** Negative, Boundary

### KH-SHOP-09

- **Test Scenario:** Chưa đồng ý điều khoản trên UI.
- **Test Objective:** Form không gửi đơn khi chưa tick.
- **Precondition:** Giỏ có hàng, dữ liệu nhận hợp lệ, chưa tick điều khoản.
- **Test Steps:** Bấm đặt hàng trên `/gio-hang`.
- **Test Data:** Người nhận chuẩn.
- **Expected Result:** Không có `POST /shop/orders`. Người dùng ở lại giỏ. Không có mã đơn.
- **Priority:** High
- **Test Type:** UI, Negative

### KH-SHOP-10

- **Test Scenario:** Sản phẩm ngừng bán hoặc không tồn tại.
- **Test Objective:** Không bán sản phẩm inactive hoặc id lạ.
- **Precondition:** Một sản phẩm `is_active=false`, tồn > 0.
- **Test Steps:** Checkout product id inactive và một id không có.
- **Test Data:** Id inactive, id `999999`.
- **Expected Result:** HTTP 409. Message chứa `Một sản phẩm không còn bán`. Tồn sản phẩm inactive không giảm.
- **Priority:** High
- **Test Type:** Negative

### KH-SHOP-11

- **Test Scenario:** Số lượng vượt tồn.
- **Test Objective:** Không bán âm kho.
- **Precondition:** `QA-KIT` tồn 10.
- **Test Steps:** Checkout quantity 11.
- **Test Data:** `quantity=11`.
- **Expected Result:** HTTP 409. Message chứa `QA-KIT: chỉ còn 10` (đúng tên sản phẩm). Tồn vẫn 10. Không phát mã `TT-`.
- **Priority:** Critical
- **Test Type:** Negative, Boundary

### KH-SHOP-12

- **Test Scenario:** Mã giảm giá không tồn tại.
- **Test Objective:** Promo sai không tạo đơn và không đụng tồn.
- **Precondition:** Tồn 10. Không có mã `SAI`.
- **Test Steps:** `GET /api/v1/shop/promo-codes/SAI`. Checkout với `promo_code=SAI`.
- **Test Data:** `SAI`, và mã ngắn hơn 4 ký tự `AB`.
- **Expected Result:** HTTP 400 `Mã giảm giá không hợp lệ`. Tồn vẫn 10.
- **Priority:** High
- **Test Type:** Negative

### KH-SHOP-13

- **Test Scenario:** Hai dòng cùng sản phẩm trong một request.
- **Test Objective:** Số lượng được cộng trước khi so tồn.
- **Precondition:** Tồn đúng 3.
- **Test Steps:** Checkout hai dòng cùng product id, mỗi dòng quantity 2.
- **Test Data:** `[{qty:2},{qty:2}]`, tồn 3.
- **Expected Result:** HTTP 409 vì tổng 4 > 3. Message còn 3. Tồn không đổi. Nếu tồn là 4, một đơn duy nhất quantity 4, một lần trừ tồn, 4 mã `TT-`.
- **Priority:** High
- **Test Type:** Data, Boundary

### KH-SHOP-14

- **Test Scenario:** Biên số lượng 1 và bằng đúng tồn.
- **Test Objective:** Hai biên hợp lệ đều đặt được.
- **Precondition:** Tồn 10.
- **Test Steps:** Đơn A quantity 1. Đơn B quantity đúng bằng tồn còn lại sau đơn A (9), hoặc một sản phẩm khác tồn đúng bằng quantity.
- **Test Data:** quantity 1 và quantity = stock.
- **Expected Result:** Cả hai 201. Sau đơn bằng tồn, `stock_qty=0`. Đơn tiếp theo 409 `chỉ còn 0` hoặc hết hàng tùy đường giỏ. Quantity 0 bị 400 `quantity phải ≥ 1` trước khi tạo đơn.
- **Priority:** High
- **Test Type:** Boundary

### KH-SHOP-15

- **Test Scenario:** Gửi lại cùng Idempotency-Key và cùng nội dung.
- **Test Objective:** Không tạo đơn thứ hai, không trừ tồn lần hai, không đốt vé sự kiện lần hai.
- **Precondition:** Đơn COD đã thành công với key `qa-flow-key-0001`.
- **Test Steps:** Gửi đúng body và đúng key lần nữa.
- **Test Data:** Cùng người nhận, sản phẩm, promo, vé.
- **Expected Result:** Trả lại đúng `public_code`. Header `Idempotency-Replayed: true`. Tồn không giảm thêm. Vé push-up vẫn chỉ `entry_used_at` một lần.
- **Priority:** Critical
- **Test Type:** Exception, Data

### KH-SHOP-16

- **Test Scenario:** Cùng Idempotency-Key nhưng body khác.
- **Test Objective:** Chặn ghi đè một key cho hai đơn khác nhau.
- **Precondition:** Key đã dùng cho đơn SL 1.
- **Test Steps:** Gửi lại key với quantity 2 hoặc SĐT khác.
- **Test Data:** Key cũ, fingerprint khác.
- **Expected Result:** HTTP 409, code `idempotency_conflict`. Không có đơn mới.
- **Priority:** High
- **Test Type:** Negative

### KH-SHOP-17

- **Test Scenario:** Idempotency-Key thiếu hoặc sai dạng.
- **Test Objective:** Checkout bắt buộc key đúng định dạng.
- **Precondition:** Giỏ hợp lệ.
- **Test Steps:** Thiếu header. Key 15 ký tự. Key có khoảng trắng hoặc ký tự lạ. Key 128 ký tự hợp lệ. Key 129 ký tự.
- **Test Data:** `short-key-15ch`, key 128 `[A-Za-z0-9._:-]`, key 129.
- **Expected Result:** Thiếu hoặc sai dạng: 400, code `idempotency_key_invalid`, message nói 16–128 ký tự. Key đúng 128 ký tự được chấp nhận nếu phần còn lại hợp lệ. Key 129 bị từ chối. Tồn không đổi ở các lần từ chối.
- **Priority:** High
- **Test Type:** Boundary, Negative

### KH-PAY-01

- **Test Scenario:** COD không có nút xác nhận đã trả tiền.
- **Test Objective:** `payment_status` COD nằm ở `cod`, không phải `paid`.
- **Precondition:** Đơn COD đã tạo.
- **Test Steps:** Đọc đơn qua tra cứu. Tìm trên UI thành công một hành động khách tự đánh dấu đã thanh toán.
- **Test Data:** Đơn KH-SHOP-03.
- **Expected Result:** `payment_method=cod`, `payment_status=cod`. Không có API khách để chuyển `paid`. `order_status` vẫn `awaiting_confirm` cho đến khi admin đổi.
- **Priority:** High
- **Test Type:** Functional

### KH-PAY-02

- **Test Scenario:** Trang chuyển khoản hiện đúng số tiền và nội dung.
- **Test Objective:** Memo ngân hàng là `SEVQR` + mã không gạch nối.
- **Precondition:** Checkout `payment_method=bank_transfer`, total đã tính.
- **Test Steps:** Đọc `bank_transfer` trong response. Mở `/don-hang/thanh-toan?code&phone`.
- **Test Data:** Đơn 450000 sau promo 10%. `public_code` ví dụ `TAPTOT-AB12C`.
- **Expected Result:** `payment_status=awaiting_transfer`. `bank_transfer.amount_vnd=450000`. Nội dung `SEVQR TAPTOTAB12C` (không có dấu `-`). UI không hiện vé push-up. Không có nút khách tự xác nhận đã chuyển.
- **Priority:** Critical
- **Test Type:** Functional, UI

### KH-PAY-03

- **Test Scenario:** Tra cứu đúng SĐT và mã.
- **Test Objective:** Chủ đơn xem được trạng thái.
- **Precondition:** Đơn COD của `0901234567`.
- **Test Steps:** `POST /api/v1/shop/orders/track`. Mở `/tra-cuu-don` với cùng cặp.
- **Test Data:** Phone và `public_code` đúng.
- **Expected Result:** HTTP 200. Đúng mã, trạng thái hiển thị `Chờ xác nhận` khi `awaiting_confirm`. Đơn chuyển khoản kèm chi tiết ngân hàng. Đơn COD không bắt buộc khối QR.
- **Priority:** Critical
- **Test Type:** Functional

### KH-PAY-04

- **Test Scenario:** Tra cứu sai một trong hai khóa.
- **Test Objective:** Không lộ đơn khi lệch SĐT hoặc lệch mã.
- **Precondition:** Đơn của `0901234567` / `TAPTOT-AB12C`.
- **Test Steps:** Đúng mã sai SĐT `0900000000`. Đúng SĐT sai mã `TAPTOT-ZZZZZ`. Mã không prefix `TAPTOT-`.
- **Test Data:** Các cặp trên.
- **Expected Result:** HTTP 404. UI nói không tìm thấy đơn. Không trả tên, địa chỉ, hay tổng tiền của đơn thật.
- **Priority:** Critical
- **Test Type:** Security, Negative

### KH-PAY-05

- **Test Scenario:** Một số điện thoại có hai đơn.
- **Test Objective:** Mã công khai tách đơn.
- **Precondition:** Hai checkout cùng SĐT, hai key idempotency khác nhau.
- **Test Steps:** Track từng mã.
- **Test Data:** Cùng `0901234567`, hai `public_code`.
- **Expected Result:** Mỗi mã trả đúng đơn của mã đó, không trả đơn kia.
- **Priority:** High
- **Test Type:** Functional

### KH-PAY-06

- **Test Scenario:** Chuẩn hóa đầu số 84.
- **Test Objective:** `84` + 9 chữ số thành `0` + 9 chữ số.
- **Precondition:** Tồn đủ.
- **Test Steps:** Checkout phone `84901234567`. Track bằng `0901234567` và bằng chính chuỗi đã gửi.
- **Test Data:** `84901234567`.
- **Expected Result:** Đơn lưu `phone=0901234567`. Track bằng `0901234567` thành công. `84` + số không đủ 9 chữ số sau đó bị 400.
- **Priority:** Medium
- **Test Type:** Boundary, Data

### KH-PAY-07

- **Test Scenario:** SePay khớp tiền và memo thì đánh dấu đã trả.
- **Test Objective:** Chỉ webhook, không phải admin, chuyển `awaiting_transfer` sang `paid`.
- **Precondition:** Đơn chuyển khoản total 450000, mã `TAPTOT-AB12C`. `SEPAY_WEBHOOK_API_KEY` đã cấu hình trên môi trường test.
- **Test Steps:** `POST /api/v1/shop/payments/sepay` header `Apikey`, `transferType=in`, số tiền 450000, content `SEVQR TAPTOTAB12C`. Gửi lại cùng `id` giao dịch.
- **Test Data:** Amount đúng. Lần hai cùng transaction id.
- **Expected Result:** Lần một `payment_status=paid`, lưu `sepay_transaction_id`. `order_status` không tự thành `completed`. Lần hai không tạo thanh toán thứ hai. Response dạng thành công đã khớp.
- **Priority:** Critical
- **Test Type:** Integration

### KH-PAY-08

- **Test Scenario:** SePay không khớp thì không đánh dấu đã trả.
- **Test Objective:** Sai tiền, thiếu mã, tiền ra, thiếu API key không đổi đơn.
- **Precondition:** Đơn đang `awaiting_transfer`.
- **Test Steps:** Gửi amount lệch 1 đồng. Content không có mã. `transferType` khác `in`. Thiếu hoặc sai `Apikey`.
- **Test Data:** 449999; content `chuyen tien`; type `out`.
- **Expected Result:** Sai key: 401 `Invalid SePay API key` (hoặc webhook chưa cấu hình). Ba trường hợp còn lại trả `{success: true, matched: false}` và `payment_status` vẫn `awaiting_transfer`.
- **Priority:** Critical
- **Test Type:** Negative, Security

### KH-PROMO-01

- **Test Scenario:** Mã CTV 10% trên một kit.
- **Test Objective:** Số tiền khớp công thức, snapshot mã trên đơn.
- **Precondition:** CTV đã được gán `CTVQA` 10%. Tồn 10.
- **Test Steps:** `GET /shop/promo-codes/CTVQA`. Checkout COD kèm mã, SL 1.
- **Test Data:** Giá 500000.
- **Expected Result:** Preview `discount_percent=10`. Đơn `promo_code=CTVQA`, `promo_percent=10`, `promo_discount_vnd=50000`, `discount_vnd=0`, `total_vnd=450000`, `shipping_fee_vnd=0`. Tồn còn 9. `order_status=awaiting_confirm`, `payment_status=cod`.
- **Priority:** Critical
- **Test Type:** Functional, Data

### KH-PROMO-02

- **Test Scenario:** Vé sự kiện cộng với promo, không giảm ship.
- **Test Objective:** Cả hai phần trăm tính trên tiền hàng.
- **Precondition:** Vé 100 rep = 20% còn hạn, chưa dùng. Promo 10%.
- **Test Steps:** Checkout vừa `pushup_ticket` vừa `promo_code`.
- **Test Data:** Subtotal 500000.
- **Expected Result:** `discount_vnd=100000`, `promo_discount_vnd=50000`, `total_vnd=350000`. Ship vẫn 0 và không bị trừ thêm. Vé bị đánh dấu đã dùng.
- **Priority:** High
- **Test Type:** Integration, Data

### KH-PROMO-03

- **Test Scenario:** Tổng giảm không vượt tiền hàng.
- **Test Objective:** Sàn thu về 0.
- **Precondition:** Vé 100% và promo 10% trên subtotal 500000.
- **Test Steps:** Checkout cả hai.
- **Test Data:** Event 100, promo 10.
- **Expected Result:** `discount_vnd=500000`, `promo_discount_vnd=0`, `total_vnd=0`. Không âm.
- **Priority:** Medium
- **Test Type:** Boundary

### KH-PROMO-04

- **Test Scenario:** Vé giả, vé hết hạn, vé đã dùng.
- **Test Objective:** Checkout từ chối và không trừ tồn.
- **Precondition:** Tồn biết trước. Một vé đã `entry_used_at`. Một JWT hết hạn hoặc sai chữ ký.
- **Test Steps:** Checkout từng vé.
- **Test Data:** Chuỗi `not-a-ticket`, vé đã dùng, vé quá 1 ngày.
- **Expected Result:** HTTP 400. Tồn không đổi. Không có đơn.
- **Priority:** High
- **Test Type:** Negative, Security

### KH-PROMO-05

- **Test Scenario:** Biên rep chống đẩy và plank.
- **Test Objective:** Phần trăm vé khớp quy tắc thời gian.
- **Precondition:** `POST /pushup-challenge/sessions` còn trong 30 phút.
- **Test Steps:** Finish 0 rep. Finish 1 rep trong cửa sổ thời gian. Finish 100 rep trong 75 giây. Finish quá số rep đồng hồ cho phép. Finish plank dưới 55 giây. Finish plank từ 55 giây.
- **Test Data:** `kind` push-up và `plank`.
- **Expected Result:** 0 rep: không có ticket, percent 0. 1 rep: percent 0.2. 100 rep: percent 20. Vượt trần thời gian: 400. Plank < 55 giây: không vé hoặc bị từ chối theo response finish. Plank ≥ 55 giây: percent 10, reps 0. TTL vé 1 ngày.
- **Priority:** High
- **Test Type:** Boundary

### KH-REDEEM-01

- **Test Scenario:** Tra cứu mã tem.
- **Test Objective:** Trạng thái lookup đúng với unused, void, rác, mã thử.
- **Precondition:** Có một mã unused và một mã void. Mã `1` là mã thử.
- **Test Steps:** `GET /api/v1/shop/redeem-codes/lookup?code=` cho từng mã.
- **Test Data:** Mã unused, mã void, `TT-NOPE-NOPE`, `1`.
- **Expected Result:** Unused: `valid=true`. Void và mã rác: `valid=false`. `1`: `valid=true`, `status=test`, không bị ghi vào bảng mã.
- **Priority:** High
- **Test Type:** Functional

### KH-REDEEM-02

- **Test Scenario:** Đổi mã lấy lịch 100 ngày.
- **Test Objective:** Generate thành công thì mã thành `redeemed` và lịch mở bằng chính mã.
- **Precondition:** Mã unused. `REQUIRE_REDEEM_CODE_FOR_GENERATE` bật.
- **Test Steps:** `POST /api/v1/ai/generate-workout-schedule` với `redeem_code`, chế độ 100 ngày, tuổi 16–150, dụng cụ là một trong ba kit nhà.
- **Test Data:** Mã unused. Tuổi 30. Kit nhà.
- **Expected Result:** Thành công. `code_applied=true`. `view_path=/lich/{mã canonical}`. Lookup sau đó là `redeemed`. Share bằng mã mở được lịch.
- **Priority:** Critical
- **Test Type:** Integration

### KH-REDEEM-03

- **Test Scenario:** Dùng lại mã đã đổi.
- **Test Objective:** Mỗi mã thật chỉ tạo một lịch.
- **Precondition:** Mã đã `redeemed` ở KH-REDEEM-02.
- **Test Steps:** Generate lần hai với cùng mã.
- **Test Data:** Mã đã redeemed.
- **Expected Result:** HTTP 403. Không có lịch thứ hai. Mã thử `1` thì lần hai vẫn thành công và không đổi share token thành `1`.
- **Priority:** Critical
- **Test Type:** Negative

### KH-REDEEM-04

- **Test Scenario:** Hủy hoặc trả đơn thì thu hồi mã và lịch đã đổi từ đơn đó.
- **Test Objective:** Đơn A không làm hỏng mã của đơn B.
- **Precondition:** Hai đơn. Đơn A có mã unused, mã đang reserve, và một mã đã redeem gắn `plan_id`. Đơn B có mã unused riêng.
- **Test Steps:** Admin hủy đơn A khi đang `packing` hoặc `shipping`. Với đơn completed, dùng trả hàng thay vì hủy.
- **Test Data:** Hai đơn, tồn ghi nhận trước khi hủy.
- **Expected Result:** Tồn đơn A được cộng lại. Mọi mã đơn A thành void hoặc bị thu. Plan đã tạo từ mã redeemed của A bị xóa. Mã và plan của B giữ nguyên. Hủy đơn `completed` bị 400 `Chỉ hủy được đơn chưa hoàn thành`.
- **Priority:** Critical
- **Test Type:** Data, Integration

### KH-PLAN-01

- **Test Scenario:** Wizard 100 ngày trên UI.
- **Test Objective:** Nhận lịch mà không rơi vào trang thanh toán.
- **Precondition:** Mã quà hợp lệ hoặc mã thử được môi trường e2e chấp nhận.
- **Test Steps:** `/batdau`: chọn chương trình, nhập mã, cơ thể, kit, bài test, món, tuổi, điều khoản, bấm nhận lịch.
- **Test Data:** Theo `frontend/e2e/plan.spec.ts`.
- **Expected Result:** URL dạng `/lich/{token}`. Không chứa `thanh-toan`. Trang share hiện tiêu đề lịch.
- **Priority:** Critical
- **Test Type:** UI, Happy path

### KH-PLAN-02

- **Test Scenario:** Mã sai ở cổng tạo lịch.
- **Test Objective:** Không tạo lịch khi mã không hợp lệ.
- **Precondition:** Ở bước nhập mã.
- **Test Steps:** Nhập `TT00000000` và tiếp tục.
- **Test Data:** `TT00000000`.
- **Expected Result:** Ở lại cổng. Thông báo mã không đúng. Không điều hướng `/lich/`.
- **Priority:** High
- **Test Type:** UI, Negative

### KH-PLAN-03

- **Test Scenario:** Tự tạo lịch không cần đăng nhập.
- **Test Objective:** `POST /plans` nguồn manual cho khách, rồi mở share.
- **Precondition:** Chưa login.
- **Test Steps:** Mở `/tao-lich-tap/tu-tao`, lưu lịch. Hoặc `POST /api/v1/plans` source `manual`.
- **Test Data:** Tiêu đề lịch, nội dung buổi tập tối thiểu mà API chấp nhận.
- **Expected Result:** HTTP 201, `user_id` null, có share token. Khách được đưa tới `/lich/{token}`. Token có thể nằm trong `localStorage` `taptot_guest_plan_tokens` (tối đa 50).
- **Priority:** High
- **Test Type:** Functional

### KH-PLAN-04

- **Test Scenario:** Tạo lịch 100 ngày qua `POST /plans` khi chưa login.
- **Test Objective:** Endpoint này khác generate AI: challenge bắt buộc đăng nhập.
- **Precondition:** Không cookie.
- **Test Steps:** `POST /api/v1/plans` với cờ `challenge_100_days`.
- **Test Data:** Body challenge không kèm session staff.
- **Expected Result:** HTTP 401. Không có plan mới từ request này.
- **Priority:** High
- **Test Type:** Negative, Authorization

### KH-PLAN-05

- **Test Scenario:** Xuất PDF lịch chia sẻ.
- **Test Objective:** Khách xuất được file mà không cần tài khoản.
- **Precondition:** Có share token hợp lệ.
- **Test Steps:** `POST /api/v1/plans/share/{token}/export` body format pdf. Trên UI bấm Xuất PDF.
- **Test Data:** Token của lịch manual hoặc lịch HLV.
- **Expected Result:** HTTP 200, nội dung PDF. UI không hiện `Xuất file thất bại.`
- **Priority:** High
- **Test Type:** Functional

### KH-PLAN-06

- **Test Scenario:** Khách sửa lịch share.
- **Test Objective:** Sửa nội dung cần staff.
- **Precondition:** Plan đã share. Không cookie.
- **Test Steps:** `PUT /api/v1/my-plans/{id}/content`.
- **Test Data:** Id lịch vừa tạo.
- **Expected Result:** HTTP 401.
- **Priority:** High
- **Test Type:** Authorization, Negative

### KH-FAM-01

- **Test Scenario:** Lịch làm quen không cần mã tem.
- **Test Objective:** Nhánh familiarization tách khỏi challenge.
- **Precondition:** Generate bật yêu cầu mã cho nhánh thường.
- **Test Steps:** `POST /ai/generate-workout-schedule` `generation_mode=familiarization` không mã, không captcha. Lần hai có `captcha_token` và header `x-device-id` là UUID.
- **Test Data:** UUID v4. Token captcha môi trường test chấp nhận.
- **Expected Result:** Thiếu captcha hoặc device id thì bị từ chối. Đủ cả hai thì được tạo lịch làm quen, không đốt mã `TT-`. Tuần, số buổi và 45 phút bị khóa theo curriculum.
- **Priority:** High
- **Test Type:** Functional

### KH-FAM-02

- **Test Scenario:** Trần lượt làm quen theo ngày Việt Nam.
- **Test Objective:** 3 lần mỗi device, 5 lần mỗi IP.
- **Precondition:** `FAM_GEN_DAILY_CAP_ENABLED` bật. Đếm từ 0 sau nửa đêm Asia/Ho_Chi_Minh.
- **Test Steps:** Cùng device gọi lần 4. Đủ device nhưng cùng IP lần 6 bằng device khác.
- **Test Data:** Một UUID dùng 4 lần. Sáu UUID trên một IP.
- **Expected Result:** Lần 1–3 của device thành công. Lần 4 bị từ chối. Lần IP thứ 6 bị từ chối dù device còn hạn. Sau nửa đêm VN bộ đếm mở lại.
- **Priority:** Medium
- **Test Type:** Boundary

### KH-FAM-03

- **Test Scenario:** Chế độ bị cấm ở lịch làm quen.
- **Test Objective:** Không biến nhánh miễn phí thành giáo án nâng cao hoặc gym.
- **Precondition:** Request familiarization hợp lệ về captcha.
- **Test Steps:** Gửi `free_home`, `fitness_advanced`, `fitness_soldier`, `location=gym`, `no_equipment`.
- **Test Data:** Từng giá trị một.
- **Expected Result:** Mỗi request bị từ chối. Không tạo plan.
- **Priority:** High
- **Test Type:** Negative

### KH-CONTENT-01

- **Test Scenario:** Trang công khai mở được.
- **Test Objective:** Smoke các route khách không cần tài khoản.
- **Precondition:** Frontend chạy.
- **Test Steps:** Mở `/`, `/bai-tap`, `/thuc-an`, `/cach-nau`, `/kien-thuc`, `/may-tinh-calo`, `/ve-taptot`, `/sukien`, `/thu-thach-100-ngay`, `/sukien/chongday-giamgia`, `/sukien/plank-giamgia`.
- **Test Data:** Không.
- **Expected Result:** Mỗi trang có heading, không `pageerror`. Calo hiện `kcal / ngày`. Bài tập có `Chống đẩy`, thực phẩm có `Ức gà` khi catalog e2e/seed đúng. `/mon-truyen-thong` về `/thuc-an`. Trang sự kiện camera không tự bật camera.
- **Priority:** Medium
- **Test Type:** Smoke, UI

### KH-CONTENT-02

- **Test Scenario:** Form đăng ký tư vấn.
- **Test Objective:** Lead tạo ở trạng thái `new`, goal chỉ hai giá trị.
- **Precondition:** Không login.
- **Test Steps:** `POST /api/v1/contact/trainer` goal `lose_fat`. Lần khác goal `tang-can`. UI `/lien-he` gửi form hợp lệ.
- **Test Data:** Tên 2–120, phone/Zalo 8–30, goal `lose_fat` hoặc `gain`, message ≤ 2000.
- **Expected Result:** Hợp lệ: 201, status `new`. Goal lạ: 400. UI hiện xác nhận đã gửi tư vấn.
- **Priority:** High
- **Test Type:** Functional, Negative

### KH-CONTENT-03

- **Test Scenario:** Góp ý thiếu link lịch.
- **Test Objective:** `workout_plan` và `meal_plan` bắt buộc `plan_url`.
- **Precondition:** Không login.
- **Test Steps:** `POST /feedback` category `workout_plan` không URL. Lần khác category `other`, nội dung 5–4000 ký tự. Nội dung 4 ký tự.
- **Test Data:** Content `abc` và content đủ dài.
- **Expected Result:** Thiếu link lịch: 400. `other` hợp lệ: 201, email khách trên webhook để trống. Content ngắn hơn 5 hoặc dài hơn 4000: 400.
- **Priority:** Medium
- **Test Type:** Negative, Boundary

### KH-CONTENT-04

- **Test Scenario:** Search bài tập của khách.
- **Test Objective:** Bài `owner_user_id` của HLV không lọt ra ngoài.
- **Precondition:** HLV đã tạo bài riêng.
- **Test Steps:** `GET /api/v1/search/exercises` không cookie, tìm đúng tên bài riêng.
- **Test Data:** Tên bài private duy nhất.
- **Expected Result:** Kết quả không chứa bài đó. Bài public `owner_user_id` null vẫn thấy.
- **Priority:** High
- **Test Type:** Authorization

### KH-TRACK-01

- **Test Scenario:** Mất mã hoặc mất số điện thoại.
- **Test Objective:** Không có đường tra cứu thay thế.
- **Precondition:** Đơn đã tồn tại.
- **Test Steps:** Track chỉ với SĐT, bỏ mã. Track chỉ với mã, SĐT rỗng. Tìm trên UI một mục “đơn của tôi” khi chưa login.
- **Test Data:** Một nửa khóa.
- **Expected Result:** Request thiếu field bị 4xx. Không có danh sách đơn theo mỗi SĐT. Khách không xem được đơn.
- **Priority:** High
- **Test Type:** Negative

### KH-TRACK-02

- **Test Scenario:** Khách không nhận mã tem trong response đặt hàng.
- **Test Objective:** Ghi nhận đúng hành vi hiện tại, không đoán là lỗi cho đến khi có yêu cầu nghiệp vụ khác.
- **Precondition:** Checkout SL 1 thành công.
- **Test Steps:** Đọc JSON đơn và trang thành công.
- **Test Data:** Đơn vừa tạo.
- **Expected Result:** JSON khách không có chuỗi `TT-XXXX-XXXX`. Trang thành công chỉ có số lượng quà. Mã tem chỉ có ở bản in admin. Đây là rủi ro vận hành, expected theo code là không trả mã cho khách.
- **Priority:** High
- **Test Type:** Data

## AD — Admin

Ghi bằng cookie cần `POST /api/v1/auth/confirm-password` trước. Cookie `taptot_admin` sống 10 phút. Bearer token trong pytest bỏ qua bước này; case UI phải dùng cookie.

### AD-AUTH-01

- **Test Scenario:** Admin vào shell quản trị.
- **Test Objective:** Đúng tab mặc định và đủ menu.
- **Precondition:** Tài khoản admin, mật khẩu đúng.
- **Test Steps:** Login. Mở `/tai-khoan/quan-tri`.
- **Test Data:** `admin@example.com` trên e2e, hoặc admin local.
- **Expected Result:** URL shell admin. Tab mặc định `thong-ke` nhãn `Thống kê`. Menu có đủ 13 tab: lịch, mật khẩu, tạo HLV, cộng tác viên, thống kê, bài tập, dụng cụ, thức ăn, bài nấu, sản phẩm, đơn hàng, tư vấn, nội dung. Có mục `Quản trị đơn hàng`.
- **Priority:** Critical
- **Test Type:** UI, Smoke

### AD-AUTH-02

- **Test Scenario:** Ghi admin khi chưa xác nhận mật khẩu.
- **Test Objective:** Cookie session không ghi được nếu thiếu step-up.
- **Precondition:** Login cookie, chưa confirm-password.
- **Test Steps:** `POST /api/v1/admin/staff` tạo HLV.
- **Test Data:** Email mới, password `Secret12`, role `hlv`.
- **Expected Result:** HTTP 403, code `admin_step_up`, message `Nhập lại mật khẩu để thao tác quản trị.` Không tạo user.
- **Priority:** Critical
- **Test Type:** Security

### AD-AUTH-03

- **Test Scenario:** Xác nhận mật khẩu sai.
- **Test Objective:** Step-up không cấp khi sai mật khẩu hiện tại.
- **Precondition:** Đang login admin.
- **Test Steps:** `POST /auth/confirm-password` với mật khẩu sai rồi gọi tạo HLV.
- **Test Data:** `WrongPass1`.
- **Expected Result:** Confirm trả 401. Tạo HLV vẫn 403 `admin_step_up`.
- **Priority:** High
- **Test Type:** Negative, Security

### AD-AUTH-04

- **Test Scenario:** Đổi mật khẩu thu hồi session.
- **Test Objective:** Cookie cũ chết sau khi đổi.
- **Precondition:** Admin đang có cookie access.
- **Test Steps:** `POST /auth/change-password` mật khẩu hiện đúng, mật khẩu mới có chữ và số. Gọi `GET /auth/me` bằng cookie cũ. Login bằng mật khẩu cũ rồi bằng mật khẩu mới.
- **Test Data:** Mật khẩu mới `NewSecret12`.
- **Expected Result:** Đổi thành công. Cookie cũ 401. Mật khẩu cũ 401. Mật khẩu mới login được. Mọi session refresh bị revoke.
- **Priority:** High
- **Test Type:** Security

### AD-STAFF-01

- **Test Scenario:** Tạo HLV hợp lệ.
- **Test Objective:** Chỉ role `hlv`, email được xác thực sẵn.
- **Precondition:** Admin đã step-up.
- **Test Steps:** `POST /api/v1/admin/staff`.
- **Test Data:** Email chưa dùng, `Secret12`, tên, `role=hlv`.
- **Expected Result:** 201. `role=hlv`. `email_verified_at` có giá trị. Login HLV thành công không cần verify thêm.
- **Priority:** Critical
- **Test Type:** Functional

### AD-STAFF-02

- **Test Scenario:** Không tạo được admin và không nhận mật khẩu yếu.
- **Test Objective:** Chặn leo quyền và mật khẩu chỉ toàn số.
- **Precondition:** Admin đã step-up.
- **Test Steps:** Body `role=admin`. Body khác password `12345678`. Password 7 ký tự `Abc1234`.
- **Test Data:** Như trên.
- **Expected Result:** Role khác `hlv`: 422, hoặc 400 `Chỉ có thể tạo tài khoản HLV` nếu lọt schema. `12345678`: 422 vì thiếu chữ. Dưới 8 ký tự: 422. Không có user mới.
- **Priority:** Critical
- **Test Type:** Negative, Security

### AD-STAFF-03

- **Test Scenario:** Tạo CTV và gán mã một lần.
- **Test Objective:** Mã là duy nhất theo tài khoản.
- **Precondition:** Admin step-up.
- **Test Steps:** `POST /admin/collaborators` percent 10. `POST /admin/collaborators/{id}/code` body `CTVQA`. Gọi lần hai cùng user.
- **Test Data:** Email CTV mới. Code `ctvqa` (chữ thường). Percent 10.
- **Expected Result:** User `role=ctv`, promo percent 10, code ban đầu null cho đến khi gán. Sau gán, code lưu `CTVQA`. Lần hai HTTP 409 `Cộng tác viên này đã có mã giảm giá`.
- **Priority:** Critical
- **Test Type:** Functional, Negative

### AD-STAFF-04

- **Test Scenario:** Trùng mã giữa hai CTV.
- **Test Objective:** Một chuỗi mã chỉ thuộc một người.
- **Precondition:** `CTVQA` đã gán cho CTV A.
- **Test Steps:** Gán `CTVQA` cho CTV B.
- **Test Data:** Cùng code.
- **Expected Result:** HTTP 409. CTV B vẫn chưa có mã. Preview `CTVQA` vẫn là percent của A.
- **Priority:** High
- **Test Type:** Negative

### AD-STAFF-05

- **Test Scenario:** Sửa CTV.
- **Test Objective:** Đổi tên, email, phần trăm, mật khẩu.
- **Precondition:** CTV đang login.
- **Test Steps:** `PATCH /admin/collaborators/{id}` đổi tên, percent 0, rồi percent 100, rồi password mới. CTV gọi API bằng cookie cũ.
- **Test Data:** Percent 0, 100, 101, -1. Password mới `Other12ab`.
- **Expected Result:** 0 và 100 được lưu. 101 và -1: 400 `Mức giảm phải từ 0 đến 100`. Đổi mật khẩu revoke session: cookie cũ 401, mật khẩu mới login được.
- **Priority:** High
- **Test Type:** Functional, Boundary

### AD-STAFF-06

- **Test Scenario:** Xóa CTV khi còn đơn gắn mã.
- **Test Objective:** Không xóa đứt đơn đã snapshot.
- **Precondition:** Có đơn `promo_owner_user_id` trỏ CTV này.
- **Test Steps:** `DELETE /admin/collaborators/{id}`.
- **Test Data:** CTV đã có đơn.
- **Expected Result:** HTTP 409. Đơn cũ vẫn giữ `promo_code` và số tiền đã snapshot. UI nói mã ngừng dùng, đơn đã đặt vẫn giữ, khi xóa được phép.
- **Priority:** High
- **Test Type:** Data, Negative

### AD-ORDER-01

- **Test Scenario:** Lọc danh sách đơn.
- **Test Objective:** Admin lọc theo trạng thái, cách trả, ngày.
- **Precondition:** Có đơn COD và đơn chuyển khoản ở các ngày khác nhau.
- **Test Steps:** `GET /admin/shop/orders` với `payment_method=cod`, `bank_transfer`, `order_status=awaiting_confirm`, khoảng `created_from`/`created_to`, `sort=asc`.
- **Test Data:** Method lạ `momo`.
- **Expected Result:** Mỗi lọc chỉ trả đơn khớp. Method lạ: 400 `Phương thức thanh toán không hợp lệ`. Ngày tính theo biên ngày Việt Nam. Khách và CTV gọi endpoint này: 403.
- **Priority:** High
- **Test Type:** Functional, Authorization

### AD-ORDER-02

- **Test Scenario:** Luồng giao hàng tuần tự.
- **Test Objective:** Admin đẩy đơn tới hoàn thành.
- **Precondition:** Đơn `awaiting_confirm`.
- **Test Steps:** PATCH lần lượt `packing`, `shipping`, `completed`.
- **Test Data:** Id đơn COD promo.
- **Expected Result:** Mỗi lần 200 và `order_status` đúng giá trị vừa gửi. `payment_status` COD vẫn `cod`. Không hoàn tồn ở các bước này.
- **Priority:** Critical
- **Test Type:** Functional

### AD-ORDER-03

- **Test Scenario:** Nhảy và đi lùi trạng thái giao hàng.
- **Test Objective:** Kiểm chứng lỗi đã biết `KNOWN-ADM-008`.
- **Precondition:** Đơn `awaiting_confirm`.
- **Test Steps:** PATCH thẳng `completed`. Đơn khác đang `shipping` PATCH về `packing`.
- **Test Data:** Hai đơn.
- **Expected Result:** Theo kỳ vọng nghiệp vụ trong test `test_admin_cannot_skip_or_reverse_fulfillment_states`: phải bị từ chối. Hiện test đang `xfail` vì API chấp nhận nhảy cóc. Nếu vẫn 200, ghi bug Major, không đổi expected của case này thành Pass.
- **Priority:** High
- **Test Type:** Negative

### AD-ORDER-04

- **Test Scenario:** Hủy đơn đang xử lý.
- **Test Objective:** Hoàn tồn và thu mã.
- **Precondition:** Đơn `packing` hoặc `shipping`, tồn đã trừ, có mã unused.
- **Test Steps:** PATCH `cancelled` hoặc đường cancel.
- **Test Data:** Tồn trước hủy = tồn sau checkout.
- **Expected Result:** `order_status=cancelled`. Tồn cộng lại đúng quantity. Mã unused thành void. Đơn `completed` không đi qua case này.
- **Priority:** Critical
- **Test Type:** Data

### AD-ORDER-05

- **Test Scenario:** Hủy đơn đã hoàn thành.
- **Test Objective:** Hoàn thành không phải đường hủy.
- **Precondition:** Đơn `completed`.
- **Test Steps:** PATCH `cancelled`.
- **Test Data:** Id đơn completed.
- **Expected Result:** HTTP 400 `Chỉ hủy được đơn chưa hoàn thành`. Tồn không cộng. Mã không bị void thêm.
- **Priority:** High
- **Test Type:** Negative

### AD-ORDER-06

- **Test Scenario:** Khách trả hàng.
- **Test Objective:** Trả từ đang giao hoặc đã hoàn thành thì hoàn tồn và thu mã.
- **Precondition:** Một đơn `shipping`, một đơn `completed`, một đơn `packing`.
- **Test Steps:** PATCH `returned` từng đơn.
- **Test Data:** Ba trạng thái.
- **Expected Result:** `shipping` và `completed`: 200, `returned`, tồn hoàn, mã void, plan đã redeem từ đơn đó bị xóa. `packing`: 400 `Chỉ nhận trả hàng khi đơn đang giao hoặc đã hoàn thành`. Tồn đơn packing không đổi.
- **Priority:** Critical
- **Test Type:** Functional, Negative

### AD-ORDER-07

- **Test Scenario:** Hủy hoặc trả lần hai.
- **Test Objective:** Đơn đóng không xử lý lại.
- **Precondition:** Đơn đã `cancelled`. Đơn khác đã `returned`.
- **Test Steps:** Hủy lại. Trả lại. PATCH `completed` trên đơn đã hủy.
- **Test Data:** Hai đơn đóng.
- **Expected Result:** Lần hai bị 400. Đơn đã hủy không sang `completed`: `Đơn đã đóng, không đổi trạng thái` hoặc lỗi hủy tương đương. Tồn không cộng thêm lần hai.
- **Priority:** High
- **Test Type:** Negative

### AD-ORDER-08

- **Test Scenario:** Cập nhật hàng loạt.
- **Test Objective:** Bulk áp cùng luật từng đơn.
- **Precondition:** Ba id: một đang mở, một đã completed, một id không tồn tại.
- **Test Steps:** `POST /admin/shop/orders/bulk-status` sang `shipping`.
- **Test Data:** Danh sách id, có id trùng lặp.
- **Expected Result:** Id mở nằm trong `updated_ids`. Id completed nằm trong `errors` và không đổi. Id lạ có message not found. Id trùng chỉ xử lý một lần. `updated_count` khớp số id thực sự đổi.
- **Priority:** Medium
- **Test Type:** Functional, Negative

### AD-ORDER-09

- **Test Scenario:** Admin không tự gán đã thanh toán.
- **Test Objective:** `paid` không phải trạng thái admin chọn trên dropdown giao hàng.
- **Precondition:** Đơn `awaiting_transfer`.
- **Test Steps:** PATCH order status `paid`. Xem dropdown `CatalogShopOrderAdmin`.
- **Test Data:** Status `paid`.
- **Expected Result:** 400 `Trạng thái đơn không hợp lệ`. Dropdown chỉ có trạng thái giao/hủy/trả. `payment_status` vẫn `awaiting_transfer` cho đến KH-PAY-07.
- **Priority:** High
- **Test Type:** Negative

### AD-PRINT-01

- **Test Scenario:** In bìa kích hoạt.
- **Test Objective:** Số tem bằng số đơn vị trên đơn.
- **Precondition:** Đơn SL 2 đã có 2 mã. Admin step-up nếu gọi bằng cookie.
- **Test Steps:** `GET /admin/shop/orders/{id}/activation-covers.pdf` và PNG một mã `GET /admin/shop/redeem-codes/{code_id}/cover.png`.
- **Test Data:** Đơn quantity 2.
- **Expected Result:** PDF và PNG trả file hợp lệ. PDF chứa đủ 2 mã của đơn, không chứa mã đơn khác. Khách gọi các URL này: 401 hoặc 403.
- **Priority:** High
- **Test Type:** Functional, Authorization

### AD-CAT-01

- **Test Scenario:** Ẩn bài tập và sản phẩm.
- **Test Objective:** Ẩn là `is_active=false`, không xóa cứng bài public.
- **Precondition:** Admin step-up. Một bài public, một sản phẩm không phải kit chuẩn.
- **Test Steps:** PATCH bài `is_active=false`. PATCH sản phẩm inactive. Khách search và `GET /shop/products`.
- **Test Data:** Id bài và sản phẩm.
- **Expected Result:** Khách không thấy bản ghi đã ẩn. Bản ghi vẫn còn trong admin. Không có API xóa cứng bài public trong luồng này.
- **Priority:** High
- **Test Type:** Functional

### AD-CAT-02

- **Test Scenario:** Ngừng dùng món ăn.
- **Test Objective:** `deprecated` biến mất khỏi search công khai.
- **Precondition:** Món catalog `active`, không phải món custom của user.
- **Test Steps:** PATCH status `deprecated`. `GET /search/foods` không login.
- **Test Data:** Id món.
- **Expected Result:** Search không trả món đó. Admin list vẫn thấy khi lọc status. Món custom của user không nằm trong list admin foods.
- **Priority:** Medium
- **Test Type:** Data

### AD-CAT-03

- **Test Scenario:** Sửa giá sản phẩm sau khi có đơn.
- **Test Objective:** Dòng đơn giữ giá tại thời điểm mua.
- **Precondition:** Đơn đã lưu `unit_price_vnd=500000`.
- **Test Steps:** PATCH sản phẩm giá 111. Đọc lại đơn.
- **Test Data:** Giá mới 111.
- **Expected Result:** `unit_price_vnd` trên đơn vẫn 500000. `total_vnd` đơn không tính lại. Giá mới chỉ áp đơn sau.
- **Priority:** Critical
- **Test Type:** Data

### AD-CAT-04

- **Test Scenario:** Xóa bộ dụng cụ chuẩn.
- **Test Objective:** Ba kit cửa hàng không bị xóa.
- **Precondition:** Admin step-up.
- **Test Steps:** `DELETE` sản phẩm kit chuẩn.
- **Test Data:** Id `day-khang-luc` hoặc kit chuẩn tương đương.
- **Expected Result:** 400 `Không xóa bộ dụng cụ chuẩn của cửa hàng.` Sản phẩm còn.
- **Priority:** High
- **Test Type:** Negative

### AD-STATS-01

- **Test Scenario:** GMV bỏ đơn hủy.
- **Test Objective:** KPI năm không cộng cancelled.
- **Precondition:** Một đơn completed 450000 và một đơn cancelled 450000 trong cùng năm.
- **Test Steps:** `GET /admin/stats?year=` năm đó.
- **Test Data:** Hai đơn.
- **Expected Result:** `orders_gmv_vnd` và `orders_count` gồm đơn completed, không gồm cancelled. Đơn returned vẫn nằm trong GMV này theo service hiện tại, nhưng không nằm trong lợi nhuận shop (AD-STATS-02).
- **Priority:** High
- **Test Type:** Data

### AD-STATS-02

- **Test Scenario:** Lợi nhuận shop bỏ đơn trả hàng.
- **Test Objective:** Returned không còn trong profit.
- **Precondition:** Một đơn returned có doanh thu và giá vốn biết trước.
- **Test Steps:** Đọc khối shop profit của `GET /admin/stats`.
- **Test Data:** Đơn returned.
- **Expected Result:** Profit không cộng đơn returned. Đơn completed vẫn được tính.
- **Priority:** High
- **Test Type:** Data

### AD-STATS-03

- **Test Scenario:** Đơn mở trên dashboard.
- **Test Objective:** Đếm chờ xác nhận và chờ chuyển khoản.
- **Precondition:** Ít nhất một `awaiting_confirm` và một `awaiting_transfer`.
- **Test Steps:** `GET /admin/stats`.
- **Test Data:** Hai đơn mở.
- **Expected Result:** Nhóm đơn mở gồm cả hai trạng thái đó. Đơn `completed` không nằm trong nhóm mở.
- **Priority:** Medium
- **Test Type:** Functional

### AD-STATS-04

- **Test Scenario:** HLV và CTV không xem thống kê admin.
- **Test Objective:** `GET /admin/stats` chỉ admin.
- **Precondition:** Cookie HLV và cookie CTV.
- **Test Steps:** Mỗi role gọi endpoint.
- **Test Data:** Không query đặc biệt.
- **Expected Result:** HTTP 403. HLV: `Chỉ HLV và Admin được dùng chức năng này.` không áp dụng vì route yêu cầu admin, message là `Admin access required`. CTV cùng 403.
- **Priority:** High
- **Test Type:** Authorization

### AD-LEAD-01

- **Test Scenario:** Xử lý lead tư vấn.
- **Test Objective:** Admin đổi trạng thái và giữ ghi chú.
- **Precondition:** Lead `new` từ KH-CONTENT-02.
- **Test Steps:** PATCH `contacted` kèm `admin_note`. Rồi `won`. Một lead khác thẳng `lost`.
- **Test Data:** Note `Đã gọi`.
- **Expected Result:** Mỗi trạng thái `new`, `contacted`, `won`, `lost` lưu được trực tiếp. Note còn sau lần PATCH sau. Khách không gọi được endpoint admin.
- **Priority:** Medium
- **Test Type:** Functional

### AD-PLAN-01

- **Test Scenario:** Admin thấy lịch của HLV.
- **Test Objective:** Admin không bị lọc theo owner.
- **Precondition:** HLV A có một lịch. HLV B không có lịch đó.
- **Test Steps:** Admin `GET /my-plans` và `GET /my-plans/{id}`. HLV B gọi cùng id.
- **Test Data:** Id lịch của A.
- **Expected Result:** Admin thấy lịch trong danh sách và đọc được chi tiết. HLV B: 403 `Not your plan`, danh sách của B không có lịch đó.
- **Priority:** High
- **Test Type:** Authorization

## HLV — Huấn luyện viên

### HLV-AUTH-01

- **Test Scenario:** Shell HLV chỉ ba tab.
- **Test Objective:** Không lộ menu admin.
- **Precondition:** Login `hlv`.
- **Test Steps:** Mở `/tai-khoan`. Đọc các tab.
- **Test Data:** `hlv@example.com` trên e2e.
- **Expected Result:** Chỉ `Lịch của tôi`, `Bài tập của tôi`, `Đổi mật khẩu`. Không có Thống kê, đơn hàng, CTV, tạo HLV.
- **Priority:** Critical
- **Test Type:** UI, Authorization

### HLV-AUTH-02

- **Test Scenario:** HLV mở URL admin.
- **Test Objective:** Bị đưa về shell của mình.
- **Precondition:** Login HLV.
- **Test Steps:** Mở `/tai-khoan/quan-tri` và `/tai-khoan?tab=thong-ke`.
- **Test Data:** Không.
- **Expected Result:** `/tai-khoan/quan-tri` về `/tai-khoan`. Tab lạ về `ke-hoach`.
- **Priority:** High
- **Test Type:** Authorization, UI

### HLV-PLAN-01

- **Test Scenario:** HLV tạo lịch cho một khách.
- **Test Objective:** Khách là hồ sơ trên lịch, không phải user.
- **Precondition:** Login HLV A.
- **Test Steps:** `POST /my-plans` với title và `client`.
- **Test Data:** `height_cm` hợp lệ, `weight_kg`, `gender=male`, `notes=Ghi chu rieng`. Title chưa dùng.
- **Expected Result:** 201. Lịch thuộc A. Share token có. `GET /plans/share/{token}` không cần login và có notes. Ghi chú xuất hiện trên payload công khai: ghi rủi ro riêng tư, expected hiện tại là có notes.
- **Priority:** Critical
- **Test Type:** Functional

### HLV-PLAN-02

- **Test Scenario:** Trùng tiêu đề trong lịch của cùng HLV.
- **Test Objective:** Title unique theo owner, không theo toàn hệ thống.
- **Precondition:** A đã có title `Giao an A`. B chưa có title đó.
- **Test Steps:** A tạo lại `Giao an A`. B tạo `Giao an A`.
- **Test Data:** Cùng chuỗi title.
- **Expected Result:** A bị từ chối vì trùng title của mình. B tạo được.
- **Priority:** Medium
- **Test Type:** Negative

### HLV-PLAN-03

- **Test Scenario:** Sửa, xóa, xuất PDF lịch của mình.
- **Test Objective:** Chủ lịch thao tác được. Khách chỉ xem và xuất.
- **Precondition:** Lịch của A.
- **Test Steps:** A PUT content, POST export, DELETE. Khách export cùng token.
- **Test Data:** Nội dung mới.
- **Expected Result:** A được sửa và xóa. Export của khách 200 PDF. Sau khi xóa, share không còn lịch.
- **Priority:** High
- **Test Type:** Functional

### HLV-ISO-01

- **Test Scenario:** HLV B đọc và sửa lịch A.
- **Test Objective:** Cách ly dữ liệu giữa HLV.
- **Precondition:** Hai HLV. Lịch thuộc A.
- **Test Steps:** B GET và PUT `/my-plans/{id}` của A.
- **Test Data:** Id của A, cookie của B.
- **Expected Result:** HTTP 403 `Not your plan`. Nội dung lịch không đổi.
- **Priority:** Critical
- **Test Type:** Authorization

### HLV-ISO-02

- **Test Scenario:** Nhận lịch khách vào tài khoản HLV.
- **Test Objective:** Claim gắn token guest cho đúng người đang login.
- **Precondition:** Khách đã `POST /plans` và có share token. HLV đang login.
- **Test Steps:** `POST /my-plans/claim` với token đó. CTV gọi cùng API.
- **Test Data:** Token guest. Token ghim `nhapmon`.
- **Expected Result:** HLV claim thành công, lịch có owner là HLV đó. CTV: 403 `Chỉ HLV và Admin được dùng chức năng này.` Token `nhapmon` không claim được.
- **Priority:** High
- **Test Type:** Functional, Negative

### HLV-EX-01

- **Test Scenario:** Bài tập riêng của HLV.
- **Test Objective:** CRUD `/my-exercises` và không ra search khách.
- **Precondition:** Login HLV.
- **Test Steps:** POST bài riêng. GET search không cookie. Gắn bài vào lịch của chính HLV và thử gắn vào lịch HLV khác.
- **Test Data:** Tên bài `HLV-PRIVATE-QA`.
- **Expected Result:** Chủ tạo, sửa, xóa được. Search khách không có bài. Bài chỉ đặt được lên lịch của HLV đó.
- **Priority:** High
- **Test Type:** Authorization, Functional

### HLV-EX-02

- **Test Scenario:** HLV tạo bài tập public.
- **Test Objective:** `POST /admin/exercises` chỉ admin.
- **Precondition:** Cookie HLV. Có thể đã step-up hay không đều không đủ quyền.
- **Test Steps:** POST tạo bài catalog public.
- **Test Data:** Payload bài hợp lệ.
- **Expected Result:** HTTP 403. Không có bài public mới.
- **Priority:** High
- **Test Type:** Authorization

### HLV-EX-03

- **Test Scenario:** HLV tạo món và chỉ ẩn món mình tạo.
- **Test Objective:** Ẩn catalog theo `created_by`.
- **Precondition:** HLV A tạo một món qua `POST /admin/foods`. Món khác do admin tạo.
- **Test Steps:** A PATCH status món của A sang deprecated. A PATCH `is_active` hoặc status món của admin.
- **Test Data:** Hai food id.
- **Expected Result:** Món của A đổi được và biến khỏi search. Món của admin: bị cấm đổi trạng thái ẩn. A không tạo được bài public (HLV-EX-02) nhưng tạo food được.
- **Priority:** Medium
- **Test Type:** Authorization

### HLV-DENY-01

- **Test Scenario:** HLV gọi chức năng admin.
- **Test Objective:** Một ma trận từ chối.
- **Precondition:** Cookie HLV, không phải admin.
- **Test Steps:** Gọi stats, trainer-contacts, PATCH đơn, gán mã CTV, tạo staff, PATCH site media, POST cooking admin, POST shop product.
- **Test Data:** Id bất kỳ.
- **Expected Result:** Mỗi call HTTP 403. Không đổi đơn, không tạo user, không đổi nội dung web.
- **Priority:** Critical
- **Test Type:** Authorization

### HLV-AUTH-03

- **Test Scenario:** HLV đổi mật khẩu không cần step-up admin.
- **Test Objective:** Step-up chỉ áp admin cookie.
- **Precondition:** HLV login cookie, chưa có `taptot_admin`.
- **Test Steps:** Tạo bài riêng hoặc tạo food. Đổi mật khẩu.
- **Test Data:** Password mới có chữ và số.
- **Expected Result:** Ghi của HLV không bị 403 `admin_step_up`. Sau đổi mật khẩu cookie cũ 401.
- **Priority:** Medium
- **Test Type:** Security

## CTV — Cộng tác viên

### CTV-AUTH-01

- **Test Scenario:** Shell CTV và mã chưa được gán.
- **Test Objective:** CTV chỉ thấy mã của mình.
- **Precondition:** Admin tạo CTV, chưa POST code. Login CTV.
- **Test Steps:** Mở `/tai-khoan`. `GET /collaborator/promo`.
- **Test Data:** `ctv@example.com` trên e2e cho UI có mã mock. API dùng CTV code null.
- **Expected Result:** UI chỉ `Mã giảm giá` và `Đổi mật khẩu`. API khi code null: UI `Admin chưa tạo mã cho tài khoản này.` Không có nút tự tạo mã.
- **Priority:** Critical
- **Test Type:** UI, Functional

### CTV-STATS-01

- **Test Scenario:** Doanh thu CTV chỉ tính đơn hoàn thành.
- **Test Objective:** Đơn mở không cộng tiền.
- **Precondition:** Đơn COD 450000, promo 50000, đang `awaiting_confirm`, thuộc CTV.
- **Test Steps:** `GET /collaborator/promo/stats` khi đơn mở, khi `packing`, khi `shipping`, sau khi admin chuyển `completed`.
- **Test Data:** Đơn XR hoặc KH-PROMO-01. `period=month`, `on` đúng tháng VN của `created_at`.
- **Expected Result:** Trước completed: đơn có thể được đếm trong `order_count` nếu không cancelled, nhưng `total_vnd=0` và `discount_vnd=0`. Sau completed: `total_vnd=450000`, `discount_vnd=50000`. `discount_vnd` là tiền giảm của khách, không phải hoa hồng.
- **Priority:** Critical
- **Test Type:** Data

### CTV-STATS-02

- **Test Scenario:** Đơn hủy trong thống kê CTV.
- **Test Objective:** Hủy không vào tổng tiền nhưng vẫn lọc được.
- **Precondition:** Một đơn cancelled có mã CTV. Một đơn completed khác.
- **Test Steps:** Stats không lọc. Stats `status=cancelled`.
- **Test Data:** Hai đơn.
- **Expected Result:** `order_count` không gồm cancelled. `total_vnd` không gồm cancelled. Lọc `status=cancelled` vẫn trả đơn hủy. Đơn cancelled không PATCH được sang `completed`.
- **Priority:** High
- **Test Type:** Data, Negative

### CTV-STATS-03

- **Test Scenario:** Biên ngày theo giờ Việt Nam.
- **Test Objective:** Đơn 00:30 ICT thuộc ngày VN đó, không thuộc ngày UTC trước.
- **Precondition:** Một đơn tạo tại 17:30 UTC hôm trước, tức 00:30 ngày D theo Asia/Ho_Chi_Minh.
- **Test Steps:** Stats `period=day&on=D` và `on` ngày UTC.
- **Test Data:** Mốc thời gian trên. `period=week` để kiểm tra giá trị lạ.
- **Expected Result:** Đơn nằm trong ngày D. `period` không phải day/month/year: 400 `Chọn ngày, tháng hoặc năm`. `on` sai định dạng: 400 `Mốc thời gian không hợp lệ`.
- **Priority:** Medium
- **Test Type:** Boundary

### CTV-REDACT-01

- **Test Scenario:** CTV không thấy SĐT và địa chỉ.
- **Test Objective:** Cùng đơn, admin thấy đủ, CTV bị che.
- **Precondition:** Đơn promo có phone `0901234567`, phường và đường đã lưu.
- **Test Steps:** CTV `GET /collaborator/promo/stats` hoặc danh sách đơn. Admin `GET /admin/collaborators/{id}/orders`.
- **Test Data:** Đơn KH-PROMO-01.
- **Expected Result:** Payload CTV không có phone, ward, address line. Payload admin có đủ `0901234567` và địa chỉ. Tổng tiền admin và CTV cùng một snapshot promo.
- **Priority:** Critical
- **Test Type:** Security

### CTV-DENY-01

- **Test Scenario:** CTV gọi API staff và admin.
- **Test Objective:** CTV không phải staff.
- **Precondition:** Cookie CTV.
- **Test Steps:** `GET /my-plans`, `GET /admin/stats`, `GET /admin/shop/orders`, `POST /admin/exercises`, `POST /plans` không thuộc scope ctv nếu route yêu cầu staff.
- **Test Data:** Không body đặc biệt ngoài login.
- **Expected Result:** HTTP 403. My-plans: `Chỉ HLV và Admin được dùng chức năng này.` Admin routes: `Admin access required`.
- **Priority:** Critical
- **Test Type:** Authorization

### CTV-DENY-02

- **Test Scenario:** Admin và HLV gọi API cộng tác viên.
- **Test Objective:** `/collaborator/*` chỉ role `ctv`.
- **Precondition:** Cookie admin và cookie HLV.
- **Test Steps:** `GET /collaborator/promo` và `GET /collaborator/promo/stats`.
- **Test Data:** Không.
- **Expected Result:** HTTP 403 `Chỉ cộng tác viên được dùng chức năng này.`
- **Priority:** High
- **Test Type:** Authorization

### CTV-DENY-03

- **Test Scenario:** CTV tự đổi mã hoặc phần trăm.
- **Test Objective:** Chỉ admin gán mã.
- **Precondition:** CTV đã có mã.
- **Test Steps:** Tìm request từ UI đổi code. Gọi PATCH collaborator bằng cookie CTV.
- **Test Data:** Code mới `CTVNEW`.
- **Expected Result:** 403. Mã và percent không đổi. UI không có form sửa mã.
- **Priority:** High
- **Test Type:** Authorization, UI

## XR — Một dữ liệu, bốn vai

Chạy tuần tự. Dùng một sản phẩm 500000 tồn 10, một CTV `CTVQA` 10%, hai HLV.

### XR-01

- **Test Scenario:** Admin lập nhân sự cho câu chuyện.
- **Test Objective:** Step-up, hai HLV, một CTV, một mã.
- **Precondition:** Admin login cookie.
- **Test Steps:** Confirm password. Tạo HLV A, HLV B. Tạo CTV. Gán `CTVQA`. Gán lần hai.
- **Test Data:** Password `Secret12`. Percent 10.
- **Expected Result:** Ba user tạo được. Email đã verify. Lần gán mã thứ hai 409. HLV login được. CTV login được và thấy mã `CTVQA`.
- **Priority:** Critical
- **Test Type:** Integration

### XR-02

- **Test Scenario:** Khách mua COD bằng mã CTV.
- **Test Objective:** Tiền, tồn, tra cứu, replay.
- **Precondition:** XR-01 xong. Tồn 10.
- **Test Steps:** Preview mã. Checkout COD SL 1 key `qa-xr-cod-00001`. Track đúng và sai. Replay cùng key.
- **Test Data:** Phone `0901234567`. Tổng kỳ vọng 450000.
- **Expected Result:** Preview 10%. Đơn `awaiting_confirm` / `cod`, promo 50000, total 450000, tồn 9. Track đúng 200, track sai mã 404. Replay cùng `public_code`, tồn vẫn 9, header replay true.
- **Priority:** Critical
- **Test Type:** Integration

### XR-03

- **Test Scenario:** CTV thấy đơn khi còn mở.
- **Test Objective:** Che địa chỉ và chưa ghi nhận tiền.
- **Precondition:** XR-02.
- **Test Steps:** CTV đọc stats và danh sách. Admin đọc orders của CTV.
- **Test Data:** Tháng VN của đơn.
- **Expected Result:** CTV thấy đơn, `total_vnd=0`, `discount_vnd=0` nếu chưa completed. Không có phone và địa chỉ. Admin thấy `0901234567` và địa chỉ.
- **Priority:** Critical
- **Test Type:** Integration, Security

### XR-04

- **Test Scenario:** Admin hoàn tất giao hàng.
- **Test Objective:** CTV chỉ có tiền sau `completed`.
- **Precondition:** XR-03.
- **Test Steps:** Admin `packing` → `shipping` → `completed`. CTV đọc stats sau packing và sau completed.
- **Test Data:** Id đơn XR-02.
- **Expected Result:** Sau packing/shipping: tiền CTV vẫn 0. Sau completed: `total_vnd=450000`, `discount_vnd=50000`. Payment COD vẫn `cod`.
- **Priority:** Critical
- **Test Type:** Integration

### XR-05

- **Test Scenario:** Lead tư vấn đi hết trạng thái.
- **Test Objective:** Khách tạo, admin chốt.
- **Precondition:** Admin đang làm việc.
- **Test Steps:** Khách POST lead `lose_fat`. Admin `contacted` rồi `won` với note. Khách POST goal `nope`.
- **Test Data:** Tên và số hợp lệ.
- **Expected Result:** Lead 201 status `new`. Sau xử lý là `won`, note còn. Goal lạ 400.
- **Priority:** Medium
- **Test Type:** Integration

### XR-06

- **Test Scenario:** HLV phát hành lịch, khách xem, HLV kia bị chặn.
- **Test Objective:** Share công khai, bài riêng thì không.
- **Precondition:** HLV A và B của XR-01.
- **Test Steps:** A tạo lịch có notes và một bài private. Khách GET share và export PDF. Khách search bài. B GET lịch. Khách PUT content. Admin GET my-plans.
- **Test Data:** Notes `Ghi chu rieng`. Tên bài private.
- **Expected Result:** Share 200 có notes. PDF 200. Search không có bài private. B nhận 403. Khách PUT 401. Admin thấy lịch của A.
- **Priority:** Critical
- **Test Type:** Integration, Authorization

### XR-07

- **Test Scenario:** Khách đổi một mã tem chưa dùng.
- **Test Objective:** Đốt mã đúng một lần.
- **Precondition:** Admin đã có một mã unused (lô hoặc mã của một đơn khác chưa hủy).
- **Test Steps:** Lookup. Generate 100 ngày. Lookup lại. Generate lại.
- **Test Data:** Mã `TT-` unused. Không dùng mã `1` cho nhánh này.
- **Expected Result:** Lookup đầu `valid`. Sau generate `redeemed`, `view_path` là `/lich/{mã}`. Lần hai 403.
- **Priority:** Critical
- **Test Type:** Integration

### XR-08

- **Test Scenario:** Hủy một đơn khác không làm sai KPI đơn đã hoàn thành.
- **Test Objective:** Đơn completed giữ số. Đơn hủy hoàn tồn của chính nó.
- **Precondition:** XR-04 đã chốt 450000. Tạo thêm đơn promo thứ hai còn `awaiting_confirm`, ghi tồn sau đơn hai.
- **Test Steps:** Hủy đơn hai. Đọc stats admin và stats CTV. Thử PATCH đơn đã hủy sang `completed`.
- **Test Data:** Đơn hai cùng mã CTV.
- **Expected Result:** Tồn đơn hai được hoàn. Mã đơn hai void. `total_vnd` CTV của đơn completed vẫn 450000, không cộng và không trừ đơn hai. GMV admin không cộng đơn hủy. Đơn đã hủy sang completed: 400.
- **Priority:** Critical
- **Test Type:** Data, Regression

### XR-09

- **Test Scenario:** Đơn chuyển khoản tách khỏi đơn COD.
- **Test Objective:** Trạng thái tiền khác nhau.
- **Precondition:** Cùng sản phẩm, tồn còn.
- **Test Steps:** Checkout `bank_transfer` với promo, key mới. Đọc response. Không gọi SePay. Sau đó gọi SePay đúng tiền nếu môi trường có key test.
- **Test Data:** Total 450000. Memo `SEVQR` + mã không gạch.
- **Expected Result:** `payment_status=awaiting_transfer`, `amount_vnd=450000`. `order_status` vẫn `awaiting_confirm`. Khi chưa có webhook, không thành `paid`. Nếu thiếu key SePay trên môi trường thủ công thì phần webhook là Blocked, phần tạo đơn vẫn phải Pass.
- **Priority:** Critical
- **Test Type:** Integration

## Ngoài phạm vi của bộ case

- Không gọi `/api/v1/payments/*`. Router đó không được mount.
- Không kiểm hoa hồng chi trả. Không có ví CTV.
- Không kiểm đăng nhập Google hoặc Facebook.
- Rate limit chỉ ghi nhận ngưỡng cấu hình: checkout 10/phút/IP, track 20/phút/IP, generate 8/phút/IP. Không có bài tải lớn.
