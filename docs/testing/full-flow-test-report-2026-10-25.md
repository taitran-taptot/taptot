# Báo cáo test full luồng TAPTOT

Ngày: 2026-10-25  
Môi trường: local `http://localhost:3000` + API `http://127.0.0.1:8000` (`GET /health` → `development`). Không đụng `taptot.vn`.  
Phạm vi: hành vi đang chạy (khách, HLV, admin). Không sửa sản phẩm trong vòng này.  
Đối chiếu: [main-flow-test-report-2026-10-24.md](main-flow-test-report-2026-10-24.md).

Kết luận: **chưa ký production cho toàn bộ sản phẩm.** Các luồng đã đi và pass được ghi ở cuối. Ba lỗi đã biết từ 24/10 vẫn đúng. Có thêm 2 lỗi UI mới (token rác, xóa bài riêng đang nằm trong lịch).

## Điều kiện

- PostgreSQL đang lắng nghe cổng 5432. API và frontend đã chạy sẵn.
- Shop có 3 kit đang bán: dây kháng lực, tạ đơn, xà đơn và vòng treo (500.000 ₫/kit).
- `NEXT_PUBLIC_REQUIRE_REDEEM_CODE=true`. Không có Turnstile site key, captcha bị bỏ qua trên local.
- Nút đăng nhập header tắt (`AUTH_UI_ENABLED = false`). Vào thẳng `/dang-nhap`.
- Tài khoản local tạo cho vòng này dùng đuôi `@taptot.vn`. Email `@taptot.test` bị `EmailStr` từ chối (`special-use or reserved name`) nên không đăng nhập được. Mật khẩu không ghi trong báo cáo này.
- Sau vòng test, mật khẩu HLV local đã được đổi rồi đổi lại. Đơn `TAPTOT-EUT7P` được nhảy trạng thái qua API rồi trả về `awaiting_confirm` để xác nhận `KNOWN-ADM-008`.

## Tầng tự động

| ID | Kết quả | Chứng cứ |
| --- | --- | --- |
| FE-AUTO | pass | `npm test` trong `frontend`: 26 file, **182 passed**, 0 failed. Hôm 24/10 là 180 passed. Không có fail mới. |
| API-AUTO | fail | `python -m pytest -q --ignore=tests/test_export_schedule_matrix.py` trong `api`: **1229 passed, 16 failed, 1 xfailed** (68.6s). Hôm 24/10: 1259 passed, 16 failed, 1 xfailed. Số fail không tăng; số pass giảm 30. `tests/test_export_schedule_matrix.py` vẫn không collect được vì import `export_schedule_matrix_xlsx`. |

Cụm tiền (`test_main_flow_regression.py`, `test_shop_checkout.py`, `test_redeem_codes.py`, `test_pushup_challenge.py`, `test_auth_guest_security.py`) không nằm trong 16 fail. xfail vẫn là `test_admin_cannot_skip_or_reverse_fulfillment_states` (`KNOWN-ADM-008`).

16 fail hiện tại, cùng họ với drift catalog/search/seed đã ghi hôm 24/10, không tính là regression mới của luồng tiền:

1. `tests/test_auth_cookies.py::test_hlv_cannot_write_admin_foods` — 201 thay vì 403. Route dùng `require_staff_write`. Đã biết.
2. `tests/test_challenge_100_request.py::test_familiarization_keeps_food_ids_and_blocks_ai_suggest` — `duration_weeks` 4 == 9.
3. `tests/test_challenge_100_request.py::test_first_push_pull_forces_fixed_60_day_schedule` — `duration_weeks` 4 == 9.
4. `tests/test_gym_shortlist_score.py::test_gym_upper_prefers_smith_and_db_over_pike` — `63 > 63`.
5–8. `tests/test_raw_foods_audit.py` — catalog 168 thay vì ≥ 400; thiếu tag subgroup; dish/packaged 0; đường dẫn ảnh có `?v=` nên `Path.is_file` fail.
9–15. `tests/test_search_specialization.py` (7 test) — sqlite `no such column: exercises.owner_user_id`.
16. `tests/test_unlink_bar_rings_library.py::test_library_filter_hides_unlinked_rows` — cùng cột sqlite thiếu.

## Khách

| ID | Kết quả | Chứng cứ |
| --- | --- | --- |
| HOME | pass | `/` có CTA Bắt đầu, Về TAPTOT, Dụng cụ, sự kiện, shop, HLV, ba link kho. Header không có nút đăng nhập. Có giỏ hàng. |
| ABOUT | pass | `/ve-taptot` có `hero-gym.jpg` và `tran-tai.jpg`. |
| EXERCISES | partial | `/bai-tap` ra 451 bài. Lọc Ngực + Tạ đơn ra 9 bài. Modal «Đẩy ngực tạ đơn» có hướng dẫn và video. Tìm `zzznomatchxyz` ra «Không tìm thấy». Overlay dev «Expected static flag was missing» tại `ExerciseLibrary` (`bai-tap/page.tsx`). Badge «Xóa bộ lọc (4)» trong khi chỉ thấy 2 ô đang chọn. Không phải regression 24/10 (suite đó không đi UI này). |
| FOODS | pass | Quầy có số lượng. Mở Bắp cải tím (37 kcal/100g). Tìm rỗng ra «Không tìm thấy thực phẩm». |
| KNOWLEDGE | pass | `/kien-thuc` Cơ bản 19 / Trung cấp 9 / Nâng cao 2. Bài `/kien-thuc/xac-dinh-muc-tieu-tap-luyen` mở được. Slug sai vẫn HTTP 200 với title kho; câu trống phía client chưa xác nhận. |
| COOKING | pass | `/cach-nau?mon=com-ga-hoi-an` hiện nguyên liệu. |
| CALC | pass | Bộ số hợp lệ: BMI 22.5, mục tiêu 1.918 kcal/ngày. Tuổi 5 ra alert «Vui lòng nhập đúng tuổi, chiều cao và cân nặng.» |
| LEGAL | pass | `/dieu-khoan`, `/chinh-sach-bao-mat`, `/chinh-sach-ban-hang`, `/chinh-sach-thanh-toan`, `/khieu-nai`, `/thong-tin-don-vi` đều có title. «Đang cập nhật» trên thông tin đơn vị không tính fail. |
| REDIRECTS | pass | `/kho-bai-tap` → `/bai-tap`. `/ve-chung-toi` 308 → `/ve-taptot`. `/qua-tang` → `/batdau?nhap-ma=1`. `/kiemtratheluc` → `/sukien`. `/hlv` đẩy khách tới `/dang-nhap?next=%2Ftai-khoan`. |
| SIGNUP | pass | `/dang-ky` tiêu đề «Đăng ký đã đóng». |
| FAM | partial | `/batdau?moi=1` tạo được `/lich/nhapmon`: «Nhập môn · 28 ngày», 3 buổi/tuần, tuần 1–4, không tab bữa ăn (đúng thiết kế). Nút «Xuất PDF» không hiện trên tổng quan (`compactMonthOverview`). `POST /api/v1/plans/share/nhapmon/export` trả PDF 200, 85.575 byte. |
| BAD-TOKEN | fail | `/lich/khong-ton-tai-fullflow` chỉ hiện chuỗi tiếng Anh `UserDailyPlan 'khong-ton-tai-fullflow' not found`. Không có câu tiếng Việt và không có link về `/batdau?moi=1`. Không nằm trong phạm vi báo cáo 24/10. |
| CHALLENGE | pass | Mã `TT-BAD0-CODE` bị «Mã không đúng». Mã QA `1` qua cổng, đủ 4 bài test, dụng cụ, lịch, 6 món (2/2/2), đồng ý điều khoản, ra `/lich/LAdZtjxu1wd4eEcymvvX_Q`: 14 tuần, tuần 14 deload, có bữa ăn. Nút PDF chuyển «Đang xuất…». Export API 200, PDF 149.499 byte. |
| P2 | pass | `/tao-lich-tap/tu-tao` lưu lịch khách `POST /plans`, mở `/lich/ifg02hOUGiO5TdkOFzC3zQ` «Lịch tự tạo — Giữ cân», 3 buổi/tuần, 4 tuần. «Tạo lịch tập» giữ disabled khi chưa có bài. |
| SHOP | pass | `/mua-dung-cu` có 3 kit, mở chi tiết dây kháng lực, thêm giỏ ghi `taptot.guest_cart.v1`. |
| CHK-EMPTY | pass | `/gio-hang` giữ «Tiếp tục» disabled khi thiếu tên, SĐT, tỉnh, quận, phường, đường hoặc checkbox điều khoản. |
| COD | pass | Đơn `TAPTOT-41X9Q`, SĐT `0900000001`, dây kháng lực, 500.000 ₫, trang thành công nói có 1 mã lộ trình tặng kèm và không in chuỗi mã. |
| TRACK | pass | Sai SĐT + đúng mã: UI «Không tìm thấy đơn hàng…», API 404. Đúng cặp: «Chờ xác nhận · 500.000 ₫», không có mã quà. JSON track không có field `redeem`. |
| BANK | pass | `/don-hang/thanh-toan` của `TAPTOT-EUT7P` có ảnh QR VietQR, MB Bank, số tài khoản `0000000000`, tên TAPTOT, nội dung là mã đơn. «Tôi đã chuyển khoản» sang trang thành công, không lộ chuỗi mã. Số tài khoản placeholder không tính fail vì QR và số đều hiện. |
| EVENTS | partial | `/sukien` liệt kê chống đẩy và plank. Chống đẩy tới màn đồng ý, camera đếm rồi kết thúc «0 cái» vì không có người trong khung, không ra voucher. Plank tới màn đồng ý rồi dừng, không bật camera. Mốc 5/10/15% không đi trên UI; ranh giới vé nằm ở `api/tests/test_pushup_challenge.py`. Không có `?uu-dai=1` trên giỏ. |
| CONTACT | pass | `/lien-he` gửi lead Fullflow Lead, `0900000011`, mục tiêu giảm mỡ. Modal thành công. Overlay hydration dev tại `FeaturedTrainerIntro.tsx` không chặn gửi. |
| FEEDBACK | pass | Hạng mục dụng cụ gửi được. Hạng mục lịch không có URL thì focus ô URL và không gửi. Có URL lịch thì gửi được. |

## HLV

Đăng nhập `fullflow.hlv@taptot.vn` vào `/tai-khoan?tab=ke-hoach`.

| ID | Kết quả | Chứng cứ |
| --- | --- | --- |
| HLV-CLAIM | pass | Sau đăng nhập, localStorage token khách bị xóa và danh sách có «Lịch tự tạo — Giữ cân» cùng «Lịch tập giảm cân 25/10/2026 23:58». |
| HLV-CART | pass | Giỏ khách `{product_id:28, quantity:1}` biến mất khỏi localStorage. `/gio-hang` hiện Dây kháng lực ngũ sắc 500.000 ₫ trên giỏ server. |
| HLV-PLAN | pass | Tạo lịch trống «Fullflow trống», 7 ngày, slug `fullflow-trong` → `/tai-khoan/lich/52` (route thật là `/tai-khoan/lich/{id}`, không phải `?id=`). Thêm bài riêng và món Bánh canh Trảng Bàng (bữa sáng), «Lưu thay đổi» còn sau reload. «Lưu thành template» ra «Mẫu — Fullflow trống» (7 ngày · 1 bài · 1 món). «Dùng mẫu» tạo `/tai-khoan/lich/54` «Fullflow từ mẫu» và vẫn có bài. Xóa lịch nguồn; template và bản copy còn. |
| HLV-EX | partial | Tạo «Fullflow chống đẩy» (Ngực trên, phần Chính) hiện trong tab Bài tập của tôi. Bài chưa gắn lịch («Fullflow xoa», id 2748) xóa được: `DELETE` 204 và biến khỏi danh sách. Bài đang nằm trong lịch (id 2747): hộp thoại hứa «ẩn khỏi danh sách», `DELETE /my-exercises/2747` trả 204 và set `is_active=false`, nhưng `list_mine` không lọc `is_active` nên bài vẫn hiện. Không phải regression 24/10. |
| HLV-PW | pass | Đổi mật khẩu ra «Đã đổi mật khẩu. Vui lòng đăng nhập lại.», session bị đá về `/dang-nhap`, đăng nhập bằng mật khẩu mới vào lại được. Đã đổi về mật khẩu cũ trong cùng vòng. |
| HLV-ADMIN | pass | `/tai-khoan/quan-tri` đẩy về `/tai-khoan?tab=ke-hoach`. Menu chỉ còn Lịch của tôi, Bài tập của tôi, Đổi mật khẩu. |
| HLV-FORGOT | pass | `/quen-mat-khau` gửi được. Dev mode hiện link `/dat-lai-mat-khau` (không mở link, không đặt lại mật khẩu). |

Picker bài trong lịch HLV chỉ hiện bài do HLV tạo («Không lấy kho công khai»). Đó là lý do phải tạo bài riêng trước khi sửa lịch trống.

## Admin

Đăng nhập `fullflow.admin@taptot.vn` vào `/tai-khoan/quan-tri`.

| ID | Kết quả | Chứng cứ |
| --- | --- | --- |
| ADM-STEPUP | pass | Sửa mô tả tạ đơn mở hộp «Xác nhận quản trị» / «Nhập lại mật khẩu để sửa catalog / shop.» Sau khi xác nhận, mô tả lưu được và đã hoàn tác. API ghi thiếu step-up: xem SEC-STEPUP. |
| ADM-STATS | pass | Thống kê cả năm: 6 đơn hiệu lực. Tháng 1: 0. Tháng 10: 6. Ba kit còn trên bảng tồn. |
| ADM-PRODUCT | pass | Sửa mô tả tạ đơn thêm hậu tố rồi trả lại câu gốc. Ba kit vẫn active, giá 500.000 ₫. Tồn sau các đơn của vòng này: dây kháng lực 24, tạ đơn 27, xà đơn 23 (sau khi hủy đơn B). Không xóa kit. |
| ADM-ORDER | pass | `TAPTOT-41X9Q` trên UI: Chờ xác nhận → Đang đóng gói → Đang giao → Hoàn thành. Mã kích hoạt trên đơn admin hiện «Chưa dùng» (có hiệu lực ngay, xem known). |
| ADM-CANCEL | pass | `TAPTOT-9T4K3` «Hủy + hoàn kho» thành «Đã hủy». Tồn `xa-don-va-vong-treo` từ 22 về 23. |
| ADM-LEAD | pass | Lead Fullflow Lead / `0900000011` đổi sang «Đã liên hệ». Ghi chú nội bộ «Fullflow da lien he» còn sau khi đóng/mở lại. |
| ADM-CONTENT | pass | Tab Nội dung web mở form video trang chủ, video shop và ảnh block. Không đổi ảnh. |
| ADM-STAFF | pass | Tạo HLV `fullflow.hlv2@taptot.vn`. Thông báo «Đã tạo HLV…». Đăng nhập được, header «Fullflow HLV 2», vào `/tai-khoan`. |
| ADM-CATALOG | pass | Mở được bài tập, dụng cụ (105 dòng đang hiện, có Thanh đòn thẳng), thức ăn, bài nấu. Sửa thông số dụng cụ id 405 (`straight-bar`) thành `fullflow` qua form rồi trả về chuỗi rỗng bằng `PATCH /equipment/405` (`specs_vi: ""`). `null` không xóa field. Không đụng 3 kit. |

`KNOWN-ADM-008` vẫn đúng, xác nhận lại bằng API sau step-up trên đơn `TAPTOT-EUT7P` (id 6): `awaiting_confirm` → `shipping` trả 200, rồi `shipping` → `awaiting_confirm` trả 200. Đơn được trả về chờ xác nhận. UI ẩn select khi đơn đã hoàn thành, nên khóa chỉ có ở giao diện.

## Cổng an toàn

| ID | Kết quả | Chứng cứ |
| --- | --- | --- |
| SEC-REGISTER | pass | `POST /auth/register` → 403 «Đăng ký công khai đã đóng…». |
| SEC-GUEST-ORDERS | pass | `GET /admin/shop/orders` không cookie → 401. |
| SEC-HLV-ORDERS | pass | Cùng URL với cookie HLV → 403 «Admin access required». |
| SEC-TRACK | pass | Body tra cứu đơn COD A không có mã `redeem`. |
| SEC-STEPUP | pass | Admin `PATCH /admin/shop/orders/5` thiếu cookie step-up → 403 `code: admin_step_up`. Đơn không đổi trạng thái. |

## Đã biết, không tính lỗi mới

- `KNOWN-ADM-008`: chuyển và lùi trạng thái đơn không bị khóa ở API. Vẫn đúng (xfail pytest và PATCH local ở trên).
- HLV vẫn ghi được thực phẩm admin: pytest `test_hlv_cannot_write_admin_foods` vẫn 201 thay vì 403.
- Mã quà có hiệu lực ngay sau checkout: trang thành công COD báo có mã tặng kèm; trên đơn admin mã ở trạng thái «Chưa dùng» trước khi đơn được giao xong.

## Không ký

- Token chia sẻ không tồn tại (BAD-TOKEN).
- Xóa bài riêng đang được lịch dùng không ẩn khỏi «Bài tập của tôi».
- Nhập môn không có nút Xuất PDF trên tổng quan, dù API export chạy.
- Sự kiện camera không ra mức giảm 5/10/15% trên UI trong vòng này.
- Full pytest còn 16 fail và số pass thấp hơn hôm 24/10.
- Overlay dev (bài tập, liên hệ, đăng nhập) chỉ thấy trên `next dev`, không dùng làm bằng chứng production.

## Được coi là đi được trên local

Trang chủ, về TAPTOT, kho bài tập/thức ăn/kiến thức/cách nấu, máy tính calo, trang pháp lý, redirect, đăng ký đóng, thử thách 100 ngày với mã QA, tự tạo lịch khách, shop 3 kit, chặn form checkout thiếu dữ liệu, COD, chuyển khoản (QR placeholder), tra cứu đúng/sai cặp SĐT+mã, form liên hệ và góp ý, claim lịch và merge giỏ khi HLV đăng nhập, lịch trống / template / copy / xóa lịch, đổi mật khẩu HLV, chặn HLV khỏi `/tai-khoan/quan-tri`, quên mật khẩu dev, step-up admin, thống kê theo tháng, sửa sản phẩm không phá 3 kit, chuỗi trạng thái một đơn COD, hủy đơn COD trả kho, lead, mở form nội dung web, tạo HLV mới và đăng nhập, cùng năm cổng API ở mục cổng an toàn.
