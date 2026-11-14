# Bộ test case chuyên môn và nhánh ít đụng

Căn cứ: [full-system-test-plan.md](full-system-test-plan.md). Không sao chép bước của [full-role-flow-testcases.md](full-role-flow-testcases.md). Chỗ đã có ID cũ được đánh dấu hồi quy và chỉ thêm expected chưa khóa.

Mỗi case mới có: Test Case ID, Test Scenario, Test Objective, Precondition, Test Steps, Test Data, Expected Result, Priority, Test Type.

Kết quả thực thi không ghi trong file này.

## Dữ liệu dùng chung

Persona gửi `POST /api/v1/ai/generate-workout-schedule` với `location=home`, `challenge_100_days=true`, `ai_suggest_foods=true`, trừ khi case nói khác. Môi trường bắt mã tem thì thêm `redeem_code=1` cho mọi GEN trừ GEN-14.

| ID | Giới | Tuổi | Cao | Nặng | Level | Mục tiêu | Kit | Buổi | Phút | Baseline |
|---|---|---:|---:|---:|---:|---|---|---:|---:|---|
| GEN-01 | male | 25 | 170 | 70 | 1 | lose_weight | dumbbell | 3 | 45 | Yếu: chống đẩy tối đa 3, squat tối đa 5, plank 15 giây. Kỳ vọng `strength_tier=weak` |
| GEN-02 | female | 30 | 160 | 55 | 1 | lose_weight | resistance-band | 3 | 45 | Cùng mức yếu |
| GEN-03 | male | 28 | 175 | 78 | 2 | gain_weight | pull-up-bar và gymnastic-rings | 4 | 60 | Kéo xà tối đa ≥ 12, hít đất tối đa ≥ 25, squat tối đa ≥ 30. Kỳ vọng `strength_tier=strong` |
| GEN-04 | female | 32 | 165 | 60 | 3 | maintain | dumbbell | 5 | 60 | Giữa: chống đẩy 8, squat 15, không `test_kit`. Kỳ vọng tier `ok`, đủ 2 bài test |

Activity mặc định `moderate`. Không gửi `kg_per_week` trừ khi case nói. `health_note` null trừ GEN-12.

`fitness_baseline` của GEN-01, GEN-02 và GEN-03 chỉ gửi các khóa ở bảng, không gửi `test_kit`, `db_press_reps`, `db_row_reps`, `goblet_reps`. Khi đó máy chấm dùng ngưỡng thân trọng: chống đẩy nam 5 và 15, chống đẩy nữ 3 và 10, squat 10 và 25, plank 20 và 60, kéo xà 1 và 8. Dưới mốc thấp được 0 điểm, từ mốc thấp đến dưới mốc cao được 1, từ mốc cao trở lên được 2. Trung bình ≤ 0.75 là `weak`, ≥ 1.5 là `strong`.

GEN-01 nam: chống đẩy 3, squat 5, plank 15 đều dưới mốc thấp, trung bình 0, `weak`, `effective_level` giữ 1. GEN-02 nữ: chống đẩy 3 được 1 điểm, squat 5 và plank 15 được 0, trung bình 0.33, vẫn `weak`. GEN-03: kéo xà 12, chống đẩy 25, squat 30 đều được 2 điểm, `strong`, level hiệu lực giữ 2.

Oracle split, volume, deload, calo nằm ở plan. Số dưới đây là expected đo trên plan đã lưu.

## GEN — Thử thách và nhập môn

### GEN-01

- **Test Scenario:** Nam mới, giảm cân, tạ đơn, ba buổi, test yếu.
- **Test Objective:** Split, trần set và ngân sách tuần sau hệ số `weak` đúng với người mới.
- **Precondition:** Catalog tạ đơn active. Mã `1` hoặc mã tem còn hạn nếu cổng gen đang bật.
- **Test Steps:** Gửi persona GEN-01. Đọc plan qua share token. Đếm buổi tuần 1, `split_role`, set từng bài `main`, hard set tuần 2 theo nhóm cơ, set một buổi.
- **Test Data:** Bảng persona. Kit `dumbbell` hoặc `ta-don`.
- **Expected Result:** HTTP 201 hoặc 200 kèm `share_token`. `duration_weeks=14`. Tuần 1 có 3 buổi, mã tuần PPL. `strength_tier=weak`, `effective_level` dùng ngân sách level 1. Trần hard set tuần không deload sau hệ số 0.8: ngực, lưng, đùi, hinge và vai tối đa 10; tay trước tối đa 6; tay sau tối đa 5; core tối đa 6. Bài sức thường ≤ 3 set. Bài test ở pha 2 được 4 set. Buổi 45 phút của level 1 ≤ 14 set `main`. Có bench, row và goblet. Không có muscle-up, kéo xà, hay bài vòng treo.
- **Priority:** Critical
- **Test Type:** Domain, Functional

### GEN-02

- **Test Scenario:** Nữ mới, giảm cân, dây kháng lực, ba buổi.
- **Test Objective:** Split nữ không bị gắn PPL của nam, và bài thuộc menu dây.
- **Precondition:** Catalog dây active.
- **Test Steps:** Gửi persona GEN-02. Đọc `split_role` tuần 1 và tên bài `main`.
- **Test Data:** Kit `resistance-band` hoặc `day-khang-luc`.
- **Expected Result:** 3 buổi, mã tuần LUL. Không phải PPL. Neo có press, pulldown và squat bằng dây. Không có ghế đẩy tạ đơn, không có kéo xà. Trần set/bài và ngân sách level 1 nhân 0.8 như GEN-01.
- **Priority:** Critical
- **Test Type:** Domain

### GEN-03

- **Test Scenario:** Nam level 2, tăng cân, xà đơn và vòng treo, bốn buổi, test mạnh.
- **Test Objective:** Split ULUL, trần set level 2, bài test theo pha, rep có đi lên vì mục tiêu tăng cân.
- **Precondition:** Catalog xà và vòng active. Baseline đủ để `strength_tier=strong`.
- **Test Steps:** Gửi persona GEN-03. So tuần 2, tuần 6 và tuần 9 trên cùng một bài test. Đọc rep tuần 1, một tuần giữa pha không deload, và tuần 4.
- **Test Data:** `equipment_list` gồm `pull-up-bar` và `gymnastic-rings`. `session_minutes=60`.
- **Expected Result:** 4 buổi, mã ULUL. `duration_weeks=14`. Trần set/bài 4, sàn 2. Bài test 3 set ở pha 1, 4 set ở pha 2, 3 set ở pha 3 trước khi deload cắt. Ngân sách level 2 nhân 1.1. Hard set ngực, lưng, đùi, hinge tuần không deload ≤ 15. Profile Novice: không có tuần làm việc nào nhiều hơn 4 set chỉ vì “cộng set theo tuần”. Rep một bài sức tăng dần trong pha ở tuần không deload, tuần 4 về đầu khoảng. Có hít đất, kéo xà và squat. Không có inverted row trên bàn. Không có bài tạ đơn làm neo.
- **Priority:** Critical
- **Test Type:** Domain

### GEN-04

- **Test Scenario:** Nữ level 3, giữ cân, tạ đơn, năm buổi.
- **Test Objective:** Split năm buổi của nữ và nhánh cộng set Developing.
- **Precondition:** Ít nhất hai bài test để không bật `conservative_volume`, trừ bước riêng ở dưới.
- **Test Steps:** Gửi persona GEN-04. Đọc mã tuần. So set bài chính tuần 1 và tuần 6 trong cùng pha sau tuần 4. Gửi lại cùng người nhưng bỏ hết baseline, chỉ còn level 3.
- **Test Data:** 5 buổi, 60 phút, `goal=maintain`. Baseline lần đầu: `pushups_max=8`, `squats_max=15`, không `test_kit`. Lần sau: bỏ `fitness_baseline`.
- **Expected Result:** Mã tuần `LULU, Cardio-Core`, đúng 5 buổi. Có block cardio-core. Trần set vẫn 4. Baseline giữa dùng hai bài test điểm 1, ví dụ chống đẩy nữ 8 và squat 15, không gửi `test_kit`: tier `ok`, không `conservative_volume`, profile Developing. Có bài chính được cộng tối đa 1 set từ tuần 4 của pha so với tuần đầu pha, không vượt 4. Lần bỏ hết baseline: tier vẫn `ok`, `conservative_volume=true`, trần hard set level 3 nhân thêm 0.85, profile không tụt Novice nên nhánh cộng set vẫn còn. Rep giữ khoảng, không đi lên như GEN-03.
- **Priority:** High
- **Test Type:** Domain

### GEN-05

- **Test Scenario:** Nam level 1 xin 6 buổi.
- **Test Objective:** Người mới bị kẹp 5 buổi và 5 buổi nam vẫn là PPLUL.
- **Precondition:** Cùng kit tạ đơn với GEN-01.
- **Test Steps:** Gửi GEN-01 nhưng `sessions_per_week=6`. Đếm buổi trong một tuần không deload. Gửi thêm một request level 2, nam, `sessions_per_week=5`.
- **Test Data:** Level 1 xin 6. Level 2 nam xin 5.
- **Expected Result:** Level 1 lưu tối đa 5 buổi, không tạo ngày thứ 6. Năm buổi đó là PPLUL. Request level 2 nam 5 buổi cũng là PPLUL. PPLUL ở người mới không tính là defect.
- **Priority:** High
- **Test Type:** Boundary, Domain

### GEN-06

- **Test Scenario:** Cổng từ chối chương trình và dụng cụ không còn bán.
- **Test Objective:** Không tạo plan khi level, địa điểm hoặc mode nằm ngoài hai chương trình sống.
- **Precondition:** Không cần plan có sẵn.
- **Test Steps:** Gửi lần lượt level 4, level 5, `location=gym`, `no_equipment=true`, `equipment_list` rỗng, `generation_mode=free_home`, `fitness_advanced`, `fitness_soldier`. Mỗi lần một thay đổi trên persona GEN-01.
- **Test Data:** Các giá trị trên. Các field bắt buộc còn lại hợp lệ.
- **Expected Result:** Level 4 và 5: HTTP 400, message chứa `Mức kinh nghiệm trên 12 tháng đang được phát triển`. Gym: HTTP 422, `Chỉ tạo lịch tập tại nhà với dụng cụ đã chọn`. Không dụng cụ hoặc list rỗng: HTTP 422, `Cần chọn dụng cụ: dây kháng lực, tạ đơn, hoặc xà đơn và vòng treo`. `free_home`: HTTP 422, `Lịch nền thể lực không dụng cụ không còn tạo mới`. `fitness_advanced` và `fitness_soldier`: HTTP 422, `Thử thách thể lực nâng cao không còn tạo lịch mới`. Không có `share_token` mới ở mọi lần.
- **Priority:** Critical
- **Test Type:** Negative

### GEN-07

- **Test Scenario:** Biên tuổi, kích thước, phút và số tuần.
- **Test Objective:** Schema chặn ngoài biên. Trong biên thì thử thách bị ép 14 tuần và phút rơi vào 45 hoặc 60.
- **Precondition:** Persona GEN-01 hợp lệ để đối chứng.
- **Test Steps:** Gửi tuổi 15, 16, 45, 150, 151. Cao 49, 50, 250, 251. Nặng 19, 20, 400, 401. `session_minutes` 30 và 60 trên một thử thách hợp lệ. `duration_weeks` 4 kèm `challenge_100_days=true`. `duration_weeks` 3. `sessions_per_week` 1 và 7 với level 2. Một request `generation_mode=familiarization` hợp lệ.
- **Test Data:** Từng biên một, field khác lấy từ GEN-01.
- **Expected Result:** 15, 151, cao 49 hoặc 251, nặng 19 hoặc 401, `duration_weeks` 3, `sessions_per_week` 1: HTTP 422, không tạo plan. Tuổi 16, 45, 150, cao 50 và 250, nặng 20 và 400 được nhận. Tuổi 45 không tự Fail ở case này; bài nhảy xét ở GEN-12. Request 30 phút vẫn ra lịch, và phút dùng cho slot sức là 45. Request 60 phút dùng bucket 60. `duration_weeks=4` kèm cờ thử thách vẫn lưu 14 tuần. Level 2 xin 7 buổi bị kẹp còn tối đa 6. Nhập môn lưu 4 tuần, 3 buổi, 45 phút.
- **Priority:** High
- **Test Type:** Boundary

### GEN-08

- **Test Scenario:** Deload tuần 4, 8, 14 và hướng rep theo mục tiêu.
- **Test Objective:** Set và nghỉ tuần deload đúng hệ số. Chỉ tăng cân mới đi rep.
- **Precondition:** Plan GEN-01 và plan GEN-03 đã tạo. Nếu chưa, tạo trong case này.
- **Test Steps:** Với mỗi plan, lấy một bài `main` có rep dạng khoảng số. Đọc set và `rest_seconds` ở tuần 3 và tuần 4, tuần 7 và tuần 8, tuần 13 và tuần 14. Đọc rep tuần 1, tuần 3 và tuần 4.
- **Test Data:** GEN-01 giảm cân, level 1. GEN-03 tăng cân, level 2.
- **Expected Result:** Tuần 4, 8, 14 có dấu deload trên tiêu đề hoặc cờ tương đương. Set deload = `max(2, round(set_tuần_liền_trước * 0.6))` với bài đang có từ 2 set trở lên. Ví dụ 3 set thành 2, 4 set thành 2. Nghỉ deload của level 1 và level 2 = nghỉ tuần trước nhân 1.15, trần 180, rồi nằm trên thang 0, 30, 45, 60, 90, 120, 150, 180. GEN-01 giữ cùng khoảng rep ở tuần 1 và tuần 3; tuần 4 không cao hơn đầu khoảng. GEN-03 rep tuần 3 cao hơn hoặc bằng đầu khoảng và không vượt cuối khoảng; tuần 4 về đầu khoảng. Ghi chú deload nói tập nhẹ hơn và giữ mức tạ, không bảo tăng tạ.
- **Priority:** Critical
- **Test Type:** Domain

### GEN-09

- **Test Scenario:** Nghỉ giữa set và khối khởi động.
- **Test Objective:** Nghỉ khớp vai trò bài. Buổi có primer đúng bài chính đầu.
- **Precondition:** Plan GEN-01 (level 1) và plan GEN-04 (level 3).
- **Test Steps:** Đọc section `warmup` và bài `main` đầu của một ngày đẩy hoặc kéo ở tuần 1. Đọc `rest_seconds` của một compound và một isolation.
- **Test Data:** Hai plan trên.
- **Expected Result:** Có một bài khởi động chung 2 set, rep dạng 20–30 giây, nghỉ giữa hai set đó 30 hoặc 60 giây theo thang. Primer là cùng bài với bài chính đầu, 2 set, rep khoảng một nửa rep làm việc, nghỉ primer 90 giây. Compound level 1 nghỉ 120 giây. Compound level 3 nghỉ 180 giây trước khi deload hoặc trước khi profile cắt nghỉ. Isolation 90 giây. Không có nghỉ compound level 1 dưới 120 giây, trừ cardio 0 giây và nhịp cooldown 20 giây. Giá trị nghỉ nằm trên thang đã nêu trong plan.
- **Priority:** High
- **Test Type:** Domain

### GEN-10

- **Test Scenario:** Mỗi lịch một kit.
- **Test Objective:** Bài chính không rò sang dụng cụ khác.
- **Precondition:** Ba plan: GEN-01 tạ đơn, GEN-02 dây, GEN-03 xà và vòng. Có thể tái sử dụng plan đã tạo.
- **Test Steps:** Liệt kê tên bài `main` của tuần 1 và của một tuần pha 3. Đối chiếu neo và danh sách cấm.
- **Test Data:** Ba kit.
- **Expected Result:** Tạ đơn có bench, row, goblet; không muscle-up. Dây có press, pulldown, squat; không ghế đẩy tạ đơn và không kéo xà. Xà và vòng có hít đất, kéo xà, squat; không inverted row trên bàn và không bài neo của tạ đơn. Không buổi nào trộn hai kit làm bài chính.
- **Priority:** Critical
- **Test Type:** Domain, Data

### GEN-11

- **Test Scenario:** 45 phút và 60 phút cùng số slot sức. Focus bị giới hạn ba vùng.
- **Test Objective:** Thêm phút không thêm bài. Focus chỉ chuyển set.
- **Precondition:** Catalog tạ đơn.
- **Test Steps:** Gen nam level 2, giữ cân, tạ đơn, 4 buổi, 45 phút, không focus. Gen cùng người 60 phút, `focus_areas=["nguc"]`. Gen lần nữa với bốn vùng `nguc`, `lung`, `vai`, `tay`.
- **Test Data:** `sessions_per_week=4`. Focus một vùng và bốn vùng.
- **Expected Result:** Cả 45 và 60 phút đều 5 bài sức `main` trên một ngày đẩy, không tính khởi động, core finisher và cardio. Bản 60 phút với focus ngực có set ngực cao hơn bản 45 hoặc cao hơn bản 60 không focus, và vai hoặc bài bị lấy set không xuống dưới 2. Bốn vùng không trả 422: request vẫn tạo plan, `focus_areas` lưu tối đa 3 phần tử đầu, vùng thứ tư không xuất hiện trong lịch.
- **Priority:** High
- **Test Type:** Domain, Boundary

### GEN-12

- **Test Scenario:** Ghi chú chấn thương trên API.
- **Test Objective:** Bộ lọc chạy khi `health_note` và tuổi được gửi thẳng.
- **Precondition:** Persona GEN-03 vì lịch xà dễ lộ kéo, nhảy và squat. Đổi kit sang tạ đơn nếu cần một ngày chân có squat và hinge.
- **Test Steps:** Bốn request riêng. (1) `age=45`, `health_note` null. (2) `age=30`, note `đau gối meniscus`. (3) `age=30`, note `đau vai rotator`. (4) `age=30`, note `thoát vị đĩa đệm`.
- **Test Data:** Các chuỗi trên, viết thường có dấu hoặc không dấu đều được vì bộ lọc gấp chữ.
- **Expected Result:** (1) Không jumping jack, burpee, box jump, high knees, kipping, pistol. Squat và hinge vẫn được phép. (2) Không squat và không nhảy. (3) Không đẩy qua đầu. (4) Không hinge và không deadlift. Mỗi lịch vẫn tạo được nếu còn bài thay. Bài cấm xuất hiện ở `main` là Blocker.
- **Priority:** Critical
- **Test Type:** Domain, Negative

### GEN-12-UI

- **Test Scenario:** Wizard thử thách không gửi chấn thương.
- **Test Objective:** Phân biệt lỗ hổng sản phẩm với lỗi API.
- **Precondition:** App local mở `/batdau`. Chưa login.
- **Test Steps:** Đi wizard Thử thách 100 ngày tới lúc gọi generate. Bắt request `POST /ai/generate-workout-schedule`. Tìm ô ghi chấn thương trên form. Nếu có ô, nhập `đau gối` rồi gửi.
- **Test Data:** Người lớn hơn hoặc bằng 45 tuổi nếu form có tuổi. Một người dưới 45 cho nhánh gối.
- **Expected Result:** Body có `health_note: null` và `extra_goals: []` khi form không có ô chấn thương. Không Fail API. Ghi rủi ro: lọc gối, vai, lưng không chạy từ wizard. Nếu form có tuổi ≥ 45 và request mang `age`, lịch trả về vẫn không có bài nhảy; Fail nếu có jumping jack. Nếu người chạy gõ được `đau gối` mà request vẫn `health_note: null`, ghi defect Major vì UI nuốt ghi chú.
- **Priority:** High
- **Test Type:** UI, Risk

### GEN-13

- **Test Scenario:** Nhập môn 28 ngày và trần gen miễn phí.
- **Test Objective:** Chương trình nền không dùng menu 100 ngày. Trần thiết bị và IP chỉ chấm khi Turnstile được cấu hình.
- **Precondition:** `generation_mode=familiarization`. Secret Turnstile ghi trong biên bản. Không secret thì nhánh captcha và trần là Blocked, nhánh hình dạng lịch vẫn chấm.
- **Test Steps:** Gen một lần với thiết bị UUID A. Đọc số tuần, số buổi, tên bài. Lặp đến lần thứ 4 trong cùng ngày Việt Nam với cùng `x-device-id`. Đổi thiết bị, giữ IP, đến lần thứ 6. Gửi một lần không có header thiết bị khi secret đang bật. Hai request song song khi bộ đếm đang ở 2/3.
- **Test Data:** Header `x-device-id` là UUID. `captcha_token` hợp lệ nếu secret bật.
- **Expected Result:** Lịch 4 tuần, 3 buổi mỗi tuần, 45 phút. Không có neo bench, pulldown, kéo xà hay vòng treo của thử thách 100 ngày. Lần 1–3 của cùng thiết bị được tạo. Lần 4 cùng thiết bị bị từ chối. Lần thứ 6 cùng IP bị từ chối dù đổi thiết bị. Thiếu UUID khi secret bật thì từ chối, không tạo plan. Nếu hai request song song lúc bộ đếm còn một suất mà cả hai đều 201, ghi rủi ro Major: bộ đếm tăng sau khi tạo plan. Không secret: không kết luận Pass cho captcha.
- **Priority:** High
- **Test Type:** Boundary, Domain

### GEN-14

- **Test Scenario:** Đốt một mã tem cho thử thách 100 ngày.
- **Test Objective:** Hồi quy KH-REDEEM-01 đến KH-REDEEM-04 và XR-07 trên một mã `TT-` thật.
- **Precondition:** Một mã `unused` dạng `TT-XXXX-XXXX`. Không dùng mã `1`.
- **Test Steps:** Chạy đúng các bước của KH-REDEEM-02, KH-REDEEM-03 và KH-REDEEM-04. Không chép lại bảng tiền.
- **Test Data:** Mã unused. Persona GEN-01 không gửi `redeem_code=1`.
- **Expected Result:** Giữ expected của ba ID cũ: lookup đầu `valid`, sau generate thì `redeemed` và `view_path` là `/lich/{mã}`, lần generate thứ hai 403, hủy đơn thì void mã và xóa plan đã đổi từ mã đó, đơn khác không bị đụng. Thêm một điểm domain: plan tạo ra vẫn phải đạt GEN-01 nếu persona là GEN-01. Mã `1` không chứng minh case này.
- **Priority:** Critical
- **Test Type:** Regression, Integration

## NUT — Dinh dưỡng trên plan đã gen

Tính theo công thức ở plan. `int` cắt phần thập phân của `bmr * hệ số`. `round` là round half to even của Python. Đọc `target_calories`, `target_protein_g`, `target_carbs_g`, `target_fat_g` trên plan và trên từng khối dinh dưỡng.

### NUT-01

- **Test Scenario:** Giảm cân nam 70 kg của GEN-01.
- **Test Objective:** Mục tiêu không vượt TDEE, không dưới sàn nam, macro đúng hệ số.
- **Precondition:** Plan GEN-01, activity moderate, không gửi `kg_per_week`, 3 buổi, 45 phút.
- **Test Steps:** Tính BMR, TDEE và mục tiêu. So với plan và với cả ba khối 4 tuần.
- **Test Data:** BMR 1642.5. TDEE 2657. Mặc định 0.50 kg/tuần. Trừ 550. Mục tiêu 2107 kcal. Đạm 126 g. Béo 49 g. Carb 290.5 g.
- **Expected Result:** `target_calories=2107`. Sàn nam `max(1500, 1642)=1642`, mục tiêu nằm trong khoảng đó và ≤ 2657. Đạm, béo, carb khớp số trên trong dung sai làm tròn 0.1 g. `meals` hoặc số bữa trong ngày là 4. Ba khối tuần 1–4, 5–8, 9–14 cùng 2107 kcal. Ngày tập và ngày nghỉ cùng số. Nếu chữ trên plan hứa mỗi pha một mức calo khác 2107, ghi Minor, số lưu vẫn phải là 2107.
- **Priority:** Critical
- **Test Type:** Domain, Data

### NUT-02

- **Test Scenario:** Sàn calo nữ khi mức giảm yêu cầu quá sâu.
- **Test Objective:** Không giao dưới max(BMR, 1200).
- **Precondition:** Nữ 45 tuổi, 150 cm, 45 kg, `activity=sedentary`, `goal=lose_weight`, `kg_per_week=1.5`, 2 buổi, 45 phút, kit dây, level 1.
- **Test Steps:** Tính BMR và sàn. Gen. Đọc `target_calories`.
- **Test Data:** BMR = 10×45 + 6.25×150 − 5×45 − 161 = 1001.5. Sàn = max(1200, 1002) = 1200. `kg_per_week=1.5` bị kẹp theo % cân của 45 kg, không được hiểu là engine trừ đúng 1.5 kg. TDEE cơ bản `int(1001.5 × 1.2)` cộng kcal tập.
- **Expected Result:** `target_calories` ≥ 1200 và ≤ TDEE đã cộng kcal tập. Nếu công thức thô ra dưới 1200 mà plan lưu dưới 1200, Blocker. Đạm = 45 × 1.8 = 81 g trước khi kẹp 1.6–2.0, rồi vẫn trong khoảng 72–90 g.
- **Priority:** Critical
- **Test Type:** Boundary, Domain

### NUT-03

- **Test Scenario:** Tăng cân bị trần TDEE + 500.
- **Test Objective:** Thặng dư không vượt 500 kcal kể cả khi xin 1.5 kg/tuần.
- **Precondition:** Persona GEN-03 nhưng `kg_per_week=1.5`.
- **Test Steps:** Tính TDEE của đúng số buổi và số phút đã lưu. Đọc mục tiêu.
- **Test Data:** `goal=gain_weight`, `kg_per_week=1.5`.
- **Expected Result:** `target_calories` ≤ TDEE + 500 và ≥ TDEE. Đạm = 2.0 g/kg, không vượt 2.0 và không dưới 1.6. Béo không vượt 30% năng lượng mục tiêu. Carb > 0.
- **Priority:** High
- **Test Type:** Boundary, Domain

### NUT-04

- **Test Scenario:** Giữ cân và số bữa theo ngưỡng 1800 kcal.
- **Test Objective:** Giữ cân bám TDEE. Dưới 1800 kcal thì 3 bữa.
- **Precondition:** Một plan `goal=maintain` từ GEN-04. Một plan nữ rất nhẹ, sedentary, 2 buổi, sao cho mục tiêu dưới 1800 nếu tính ra vậy; nếu không đạt dưới 1800 thì ghi Blocked cho nửa 3 bữa và vẫn chấm nửa giữ cân.
- **Test Steps:** So `target_calories` với TDEE. Đếm loại bữa trong một ngày.
- **Test Data:** GEN-04 cho nhánh ≥ 1800. Persona nhẹ cho nhánh dưới 1800.
- **Expected Result:** Giữ cân: mục tiêu bằng TDEE đã cộng kcal tập, dung sai 0 kcal vì cả hai đều là số nguyên của cùng công thức. Đạm 1.8 g/kg trong kẹp 1.6–2.0. Ngày ≥ 1800 có 4 bữa. Ngày dưới 1800 có 3 bữa. Tổng kcal các bữa lệch mục tiêu không quá 10%.
- **Priority:** High
- **Test Type:** Domain

### NUT-05

- **Test Scenario:** Pool món tự chọn.
- **Test Objective:** Thiếu nhóm thì từ chối. Đủ nhóm thì không kéo món ngoài danh sách.
- **Precondition:** Biết ít nhất hai `food_id` đạm, hai tinh bột, hai rau đang `ai_eligible`. Một id không tồn tại.
- **Test Steps:** Gen GEN-01 với `ai_suggest_foods=false` và chỉ một id đạm. Gen lại với đủ sáu id. Gen với 31 id.
- **Test Data:** `food_ids` thật từ catalog.
- **Expected Result:** Một món hoặc thiếu nhóm: HTTP 400, message `Chọn ít nhất 2 món đạm, 2 món tinh bột và 2 món rau (tối đa 30 món).` Không có plan. Đủ sáu món: mọi `food_id` trong bữa thuộc sáu id đó. 31 id: HTTP 422 từ schema `food_ids` tối đa 30, không tạo plan. Nước lọc và muối không bị cộng kcal. Nước nấu trong một công thức không làm tăng tổng kcal mẻ so với tổng nguyên liệu sống.
- **Priority:** High
- **Test Type:** Negative, Data

## MAN — Lịch tự tạo

### MAN-01

- **Test Scenario:** Khách lưu lịch tự tạo.
- **Test Objective:** Server không đổi bài, set, rep người dùng đã chọn.
- **Precondition:** Chưa login. Biết một `exercise_id` public.
- **Test Steps:** `POST /api/v1/plans` với một ngày, một bài, set 4, rep `6-8`, nghỉ 150, tiêu đề `Lịch tự tạo`. Đọc share.
- **Test Data:** `source` để trống hoặc `manual`. `duration_weeks=1`. Không gửi cờ thử thách.
- **Expected Result:** 201. Share trả đúng bài, 4 set, rep `6-8`, nghỉ 150. Không có tuần 2 tự sinh bài mới khi `duration_weeks=1`. Không có neo kit nào được thêm hộ.
- **Priority:** High
- **Test Type:** Functional

### MAN-02

- **Test Scenario:** Khách gắn cờ thử thách trên lịch tay.
- **Test Objective:** Cờ `challenge_100_days` khi chưa login bị từ chối.
- **Precondition:** Chưa login. Body đủ field tạo plan như MAN-01.
- **Test Steps:** `POST /plans` với `challenge_100_days=true` và đủ `title_vi`.
- **Test Data:** Cùng bài với MAN-01.
- **Expected Result:** HTTP 401. Không có share token. Hồi quy phần 401 của KH-PLAN-04; case này chỉ tính khi body đủ field. 422 vì thiếu tiêu đề không được dùng làm bằng chứng.
- **Priority:** High
- **Test Type:** Authorization, Negative

### MAN-03

- **Test Scenario:** HLV tạo và sửa lịch tay.
- **Test Objective:** Sửa content không tính lại calo. Restore trả snapshot gốc.
- **Precondition:** HLV đã login. Một plan tạo bằng `POST /my-plans` với `target_calories=2107` và một bài 3 set.
- **Test Steps:** `PUT /my-plans/{id}/content` đổi bài thành 8 set, rep `20`, nghỉ 30. Đọc `target_calories`. `POST /my-plans/{id}/restore-ai` nếu plan có snapshot AI; nếu là plan tay không có snapshot thì ghi Blocked cho riêng bước restore và vẫn chấm bước sửa.
- **Test Data:** Set 8, rep `20`, nghỉ 30.
- **Expected Result:** Sau PUT, bài là 8 set, rep `20`, nghỉ 30. `target_calories` vẫn 2107. Restore đưa lại 3 set và rep cũ nếu snapshot tồn tại.
- **Priority:** High
- **Test Type:** Functional, Data

### MAN-04

- **Test Scenario:** Biên set và nghỉ trên lịch tay.
- **Test Objective:** 1 và 20 set, 0 và 600 giây được nhận. Ngoài biên thì từ chối.
- **Precondition:** HLV login.
- **Test Steps:** Tạo hoặc sửa với set 1 nghỉ 0, rồi set 20 nghỉ 600, rồi set 0, set 21, nghỉ 601, nghỉ −1.
- **Test Data:** Các biên trên.
- **Expected Result:** Set 1 nghỉ 0 và set 20 nghỉ 600 được lưu đúng số. Set 0, set 21, nghỉ 601 và nghỉ âm trả 422. Bản ghi cũ không đổi ở những lần 422.
- **Priority:** Medium
- **Test Type:** Boundary

### MAN-05

- **Test Scenario:** PDF và share không gen lại bài.
- **Test Objective:** File xuất ra đúng bản đã lưu, không cần đăng nhập.
- **Precondition:** Plan MAN-01 đã có token. Biết rep `6-8`.
- **Test Steps:** Không cookie. `GET /plans/share/{token}`. `POST /plans/share/{token}/export` với `format=pdf`.
- **Test Data:** Token của MAN-01.
- **Expected Result:** GET 200, còn rep `6-8` và 4 set. PDF 200, `application/pdf`, nội dung có cùng rep. Không xuất hiện bài của kit mà người dùng không chọn. Hồi quy KH-PLAN-05 về mã HTTP; case này thêm đối chiếu nội dung.
- **Priority:** Medium
- **Test Type:** Functional

### MAN-06

- **Test Scenario:** Ghi chú hồ sơ trên link share.
- **Test Objective:** Xác nhận ghi chú đang công khai, để không Pass nhầm thành dữ liệu kín.
- **Precondition:** HLV tạo plan với `notes` hoặc ghi chú ngày chứa `Ghi chu rieng QA`.
- **Test Steps:** Đăng xuất. `GET /plans/share/{token}`.
- **Test Data:** Chuỗi `Ghi chu rieng QA`.
- **Expected Result:** 200 và body chứa đúng chuỗi. Ghi rủi ro riêng tư. Không đánh Pass theo nghĩa “ghi chú được bảo vệ”. Hồi quy quan sát ở XR-06 và báo cáo 2026-11-07.
- **Priority:** High
- **Test Type:** Security, Risk

## SHOP — Nhiều mặt hàng và nhánh ít đụng

Người nhận, mã CTV và công thức tiền lấy từ plan. Key idempotency mỗi đơn một chuỗi hợp lệ, trừ case cố tình dùng lại key.

### SHOP-M1

- **Test Scenario:** Một đơn ba kit, số lượng khác nhau.
- **Test Objective:** Tồn và số tem bằng tổng đơn vị. Khách không thấy mã tem.
- **Precondition:** Dây tồn 5, tạ đơn tồn 5, xà và vòng tồn 5. Giá đang bán ghi lại trước lúc đặt. Chưa login.
- **Test Steps:** `POST /shop/orders`, `payment_method=cod`, ba dòng quantity 1, 2 và 1. Key mới. Admin đọc đơn kèm gift codes.
- **Test Data:** Ba `product_id` active. Tổng đơn vị = 4.
- **Expected Result:** 201. `order_status=awaiting_confirm`, `payment_status=cod`, `shipping_fee_vnd=0`. `total_vnd` bằng tổng giá nhân số lượng, chưa giảm. Tồn còn 4, 3 và 4. Đúng 4 mã `TT-`, alphabet không có I, L, O, 0, 1. JSON checkout và `POST /shop/orders/track` không có `gift_codes`. `gifts` trên URL thành công, nếu có, là 4 chứ không phải danh sách mã.
- **Priority:** Critical
- **Test Type:** Integration, Data

### SHOP-M2

- **Test Scenario:** Một dòng đủ hàng, một dòng thiếu.
- **Test Objective:** Cả đơn bị từ chối, không trừ tồn dòng kia.
- **Precondition:** Sản phẩm A tồn 5, sản phẩm B tồn 1.
- **Test Steps:** Checkout A quantity 2 và B quantity 3 trong một body.
- **Test Data:** Hai dòng. Key mới.
- **Expected Result:** HTTP 409. Message có tên B và số còn 1. Tồn A vẫn 5, tồn B vẫn 1. Không `public_code`. Không mã tem.
- **Priority:** Critical
- **Test Type:** Negative, Data

### SHOP-M3

- **Test Scenario:** Cùng một sản phẩm chỉ có một dòng giỏ.
- **Test Objective:** Thêm hai lần thì cộng số lượng và trừ chung một `stock_qty`. Không còn dòng theo kích thước.
- **Precondition:** Sản phẩm xà đơn và vòng treo tồn 3. Không có `option_key` trên giỏ và không có `options_json` trên sản phẩm.
- **Test Steps:** Thêm sản phẩm quantity 1, rồi thêm tiếp quantity 1. Checkout quantity 4. Sau đó, trên tồn còn lại, checkout quantity 2.
- **Test Data:** Một `product_id`. Không gửi lựa chọn.
- **Expected Result:** Giỏ có đúng một dòng, `quantity` = 2. Lần tổng 4 khi tồn 3: HTTP 409, tồn vẫn 3. Lần tổng 2 khi tồn 3: 201, một dòng đơn, `name_vi` là tên sản phẩm, tồn còn 1. Không có radio trên thẻ catalog hay trang chi tiết.
- **Priority:** High
- **Test Type:** Data

### SHOP-UI

- **Test Scenario:** Thẻ catalog trên mobile.
- **Test Objective:** Thẻ bán được ngay, không hỏi loại, chữ trong thẻ căn giữa.
- **Precondition:** App local mở `/mua-dung-cu` ở khung 390px. Ba kit đang bán. Giỏ khách đang trống.
- **Test Steps:** Đọc một thẻ. Bấm Thêm vào giỏ trên thẻ. Mở giỏ.
- **Test Data:** Sản phẩm `day-khang-luc` hoặc kit đang hiện tên trên thẻ.
- **Expected Result:** Thẻ có mức độ, tên, số còn, giá, nút Thêm vào giỏ và liên kết Xem chi tiết. Không có radio. Tên, số còn và giá căn giữa. Toast là `Đã thêm {tên sản phẩm} vào giỏ`. Giỏ có đúng một dòng của sản phẩm đó, quantity 1.
- **Priority:** High
- **Test Type:** UI

### SHOP-M4

- **Test Scenario:** Giỏ lẫn hàng ngừng bán.
- **Test Objective:** Cả đơn 409. Tồn hàng inactive không giảm.
- **Precondition:** Một sản phẩm `is_active=false`, tồn 4. Một kit active tồn 4. Một id 999999.
- **Test Steps:** Checkout kit active quantity 1 cùng sản phẩm inactive. Checkout riêng id 999999. Với user đã login, thêm hàng rồi tắt `is_active` và đọc giỏ server trước khi đặt.
- **Test Data:** Hai trường hợp body.
- **Expected Result:** Cả hai checkout HTTP 409, message chứa `Một sản phẩm không còn bán`. Tồn inactive vẫn 4, tồn kit active vẫn 4. Giỏ server của user đăng nhập vẫn có thể trả dòng inactive và cộng dòng đó vào `total_vnd` trước lúc đặt. Ghi nhận lệch UI nếu màn giỏ thu tiền của hàng đã tắt. Đặt từ giỏ đó vẫn 409.
- **Priority:** High
- **Test Type:** Negative

### SHOP-M5

- **Test Scenario:** Giá lúc commit, không nhận giá từ client.
- **Test Objective:** Body giả giá và việc đổi giá catalog không làm sai `total_vnd`.
- **Precondition:** `QA-KIT` giá 500000, tồn ≥ 2.
- **Test Steps:** Checkout một đơn với field giá 1 trong item nếu schema cho phép; nếu schema không có field giá thì gửi thêm field lạ. Trước đơn thứ hai, admin đổi giá thành 400000 rồi checkout không promo.
- **Test Data:** Key riêng cho mỗi đơn.
- **Expected Result:** Đơn đầu `total_vnd=500000`. Giá 1 trong body không được dùng. Đơn sau khi đổi catalog `total_vnd=400000`. Không có `expected_total` để giữ giá cũ. Ghi rủi ro vận hành mức Minor nếu trang giỏ không báo giá đã đổi, không Fail nếu số thu đúng giá mới.
- **Priority:** High
- **Test Type:** Data

### SHOP-M6

- **Test Scenario:** Idempotency và scope khách dùng chung.
- **Test Objective:** Replay không trừ tồn lần hai. Key khác body thì xung đột. Hai khách cùng key và cùng body nhìn thấy đơn của nhau.
- **Precondition:** Tồn ≥ 5. Chưa login.
- **Test Steps:** Đơn COD key `qa-shopm6-key-0001`. Gửi lại đúng body và đúng key. Gửi cùng key với số lượng khác. Gửi key 15 ký tự. Gửi key có dấu cách. Từ trình duyệt khác, chưa login, gửi đúng key và đúng body của đơn đầu.
- **Test Data:** Key hợp lệ dài từ 16. Key dài 15 là `short-key-12345`. Key có dấu cách `bad key-000000000`.
- **Expected Result:** Lần đầu 201, tồn giảm đúng số lượng, `Idempotency-Replayed` không phải true. Lần hai cùng body: cùng `public_code`, replay true, tồn không giảm thêm. Cùng key khác body: 409 `idempotency_conflict`, không đơn mới. Key 15 ký tự hoặc có dấu cách: không 201, tồn không đổi. Request từ khách thứ hai cùng key cùng body trả lại đơn của khách đầu, kèm địa chỉ `12 Le Loi`. Ghi defect Critical cho scope `guest` dùng chung. Không đánh Pass.
- **Priority:** Critical
- **Test Type:** Security, Negative

### SHOP-M7

- **Test Scenario:** Đơn 0 đồng.
- **Test Objective:** Sàn tiền không âm. SePay chỉ khớp đúng `total_vnd`, kể cả 0.
- **Precondition:** `QA-KIT` 500000. CTV percent 100, hoặc vé sự kiện cộng promo sao cho công thức ra 0. Bảng ở plan: event 100% và promo 10% trên 500000 ra thu 0.
- **Test Steps:** Checkout COD. Checkout `bank_transfer` với key khác. Nếu có API key SePay, gửi webhook `transferType=in`, số tiền 0, đúng mã. Gửi thêm webhook số tiền 1.
- **Test Data:** Subtotal 500000. Promo cắt trước khi event bị cắt, thu 0. `shipping_fee_vnd=0`.
- **Expected Result:** Cả COD và chuyển khoản đều 201, `total_vnd=0`, `promo_discount` và event không làm tổng âm. COD sang trang thành công, không mở trang chuyển khoản. Chuyển khoản giữ `awaiting_transfer` cho đến webhook. Webhook đúng 0: `payment_status=paid` nếu key hợp lệ. Webhook 1 đồng: `matched=false`, không `paid`. Không có key SePay: nhánh webhook Blocked, nhánh tạo đơn vẫn chấm.
- **Priority:** High
- **Test Type:** Boundary, Integration

### SHOP-M8

- **Test Scenario:** Vé sự kiện không cần camera.
- **Test Objective:** Trần rep và mốc plank đúng. Gian lận không bị coi là Pass chuyên môn.
- **Precondition:** Sản phẩm 500000. Không mở camera. Hồi quy phần trăm tiền ở KH-PROMO-05, không chép lại bảng.
- **Test Steps:** Finish chống đẩy với `reps=100` trong cửa sổ thời gian hợp lệ, checkout một lần, checkout lần hai cùng vé. Finish plank 54 giây và 55 giây. Finish chống đẩy `reps=100` với elapsed quá ngắn so với trần 100 rep trên 75 giây.
- **Test Data:** 54 giây, 55 giây, 100 rep, vé đã `entry_used_at`.
- **Expected Result:** 100 rep hợp lệ ra event 20%. Lần checkout thứ hai không được trừ tiếp 20%. Plank 54 giây không ra 10%. Plank 55 giây ra 10% và rep lưu 0. Rep vượt trần thời gian bị từ chối hoặc bị cắt. Request không đính kèm ảnh vẫn tạo vé nếu số nằm trong trần: ghi rủi ro gian lận, không Pass kiểm tra tư thế.
- **Priority:** High
- **Test Type:** Boundary, Risk

### SHOP-M9

- **Test Scenario:** Hủy đơn chuyển khoản đã `paid`.
- **Test Objective:** Thấy hệ thống hoàn tồn nhưng không có bút toán hoàn tiền.
- **Precondition:** Đơn `bank_transfer` đã `payment_status=paid`, `order_status` còn hủy được (`awaiting_confirm` hoặc `packing`). Một mã tem `unused`. Pytest có thể giả webhook. App local thiếu key thì dựng `paid` bằng đường test nội bộ hoặc ghi Blocked.
- **Test Steps:** Hủy đơn. Đọc tồn, trạng thái mã, `payment_status`, và mọi bảng hoàn tiền nếu có.
- **Test Data:** Quantity 1. Tồn ghi trước và sau.
- **Expected Result:** Tồn tăng lại đúng số lượng. Mã thành `void`. `order_status=cancelled`. `payment_status` vẫn `paid`. Không có bản ghi hoàn tiền. Kết luận vòng chạy là defect Major, không Pass. Expected này giữ cho đến khi có quy tắc hoàn tiền; khi đó viết lại expected chứ không đổi thành Pass chỉ vì code đang làm vậy.
- **Priority:** High
- **Test Type:** Data, Negative

### SHOP-M10

- **Test Scenario:** Hai checkout cùng lúc, tồn bằng 1.
- **Test Objective:** Postgres chỉ cho một đơn. SQLite không được dùng để kết luận.
- **Precondition:** Postgres. Sản phẩm tồn 1. Hai key khác nhau, hai body hợp lệ cùng quantity 1.
- **Test Steps:** Gửi hai `POST /shop/orders` song song. Đọc tồn và số đơn của sản phẩm đó.
- **Test Data:** Tồn đầu = 1.
- **Expected Result:** Một response 201, một response 409. Tồn cuối = 0. Đúng một đơn mới. Hai response 201 hoặc tồn âm là Critical. Trên SQLite: ghi Inconclusive, không Pass và không Fail sản phẩm.
- **Priority:** Critical
- **Test Type:** Integration

### SHOP-M11

- **Test Scenario:** Bước trạng thái giao hàng, gồm nhảy cóc.
- **Test Objective:** Hồi quy BUG-001 và giữ các bước hợp lệ.
- **Precondition:** Bốn đơn COD mới: A `awaiting_confirm`, B đã `completed`, C `shipping`, D `cancelled`.
- **Test Steps:** A gán thẳng `completed`. A khác đi `packing` rồi `shipping` rồi `completed`. B xin hủy. C xin `returned`. D gán `completed`. A đang `shipping` gán ngược `packing`.
- **Test Data:** Admin cookie đã step-up, hoặc Bearer trong pytest.
- **Expected Result:** Đường `packing` → `shipping` → `completed` được 200, COD vẫn `payment_status=cod`. Hủy B: 400 `Chỉ hủy được đơn chưa hoàn thành`, tồn không hoàn lần nữa. C sang `returned`: 200, tồn hoàn, mã void. D sang `completed`: 400 `Đơn đã đóng, không đổi trạng thái`. A nhảy thẳng `completed`, và chiều lùi `shipping` → `packing`: expected của bộ test là 400 và trạng thái giữ nguyên. Actual đã biết là gán được. Ghi Fail BUG-001 / KNOWN-ADM-008. Không sửa expected cho khớp actual.
- **Priority:** Critical
- **Test Type:** Regression, Negative

### SHOP-M12

- **Test Scenario:** Stats admin lệch ngày UTC so với stats CTV.
- **Test Objective:** Cùng một đơn 00:30 giờ Việt Nam đứng đúng ngày ở CTV và có thể đứng ngày UTC hôm trước ở bucket admin.
- **Precondition:** Hồi quy CTV-STATS-03 cho phía CTV. Thêm một đơn `completed` tạo tại 17:30 UTC hôm trước, tức 00:30 ngày D theo `Asia/Ho_Chi_Minh`, có promo CTV.
- **Test Steps:** Đọc stats CTV `period=day&on=D` và `on` ngày UTC. Đọc bucket tháng hoặc ngày của `GET /admin/stats` cho ngày D và ngày UTC.
- **Test Data:** Mốc 17:30 UTC. Đơn đã `completed` để CTV cộng tiền.
- **Expected Result:** CTV tính đơn vào ngày D, không vào ngày UTC hôm trước. `total_vnd` CTV bằng tiền đơn đó. Bucket admin theo UTC chứa đơn ở ngày UTC, không ở ngày D, nếu đơn chỉ lệch trong 7 giờ đầu ngày Việt Nam. Lệch này ghi nhận là đúng code hiện tại. Không Fail CTV. Không sửa số CTV cho khớp bảng admin.
- **Priority:** Medium
- **Test Type:** Boundary, Data

## ROLE — Phân quyền chưa khóa hết ở bộ cũ

KH-AUTH-01 đến KH-AUTH-05, AD-AUTH, HLV-DENY-01, CTV-DENY-01 đến CTV-DENY-03 và XR-06 chạy ở lớp 1. Ba case dưới chỉ thêm hành động bộ cũ chưa ghi từng request.

### ROLE-01

- **Test Scenario:** HLV sửa lịch của HLV khác.
- **Test Objective:** Sửa content bị chặn. Admin vẫn thấy cả hai lịch.
- **Precondition:** Hai HLV. HLV A có plan MAN-03 hoặc một plan tay. XR-06 đã khóa GET và search bài riêng; case này không làm lại các bước đó.
- **Test Steps:** Cookie HLV B `PUT /my-plans/{id của A}/content`. Cookie HLV B `POST /my-plans/{id của A}/restore-ai`. Cookie admin `GET /my-plans`.
- **Test Data:** Đổi tiêu đề thành `HLV B sua`.
- **Expected Result:** Cả hai request của B là 403. Tiêu đề và bài của A không đổi. Admin thấy plan của A trong danh sách. Khách không cookie PUT thì 401, hồi quy một dòng của XR-06, không cần chạy lại cả XR-06.
- **Priority:** Critical
- **Test Type:** Authorization

### ROLE-02

- **Test Scenario:** HLV với catalog, đơn và nội dung site.
- **Test Objective:** Ẩn được bài mình tạo. Không ẩn bài người khác. Không vào vùng admin.
- **Precondition:** HLV đã tạo một bài private hoặc một bài catalog ghi `created_by` là mình. Có một bài public do admin tạo.
- **Test Steps:** Ẩn bài của mình. Ẩn bài admin tạo. `POST` bài public theo route admin. `GET /admin/shop/orders`, `GET /admin/stats`, `GET /admin/collaborators`, `POST /admin/cooking-posts`, `PUT` site page media.
- **Test Data:** Cookie HLV, không dùng Bearer admin.
- **Expected Result:** Ẩn bài của mình thành công. Ẩn bài người khác: 403. Tạo bài public, đơn, stats, CTV, bài nấu, nội dung site: 403. Bài riêng không xuất hiện ở search khách, hồi quy HLV-ISO nếu đã Pass thì chỉ cần xác nhận một id mới.
- **Priority:** High
- **Test Type:** Authorization

### ROLE-03

- **Test Scenario:** Cookie admin ghi khi chưa step-up.
- **Test Objective:** UI và cookie thật đòi nhập lại mật khẩu. Bearer của pytest không được dùng làm Pass.
- **Precondition:** Admin login bằng form, chưa gọi `POST /auth/confirm-password` trong 10 phút. Hết hạn cookie `taptot_admin` nếu còn.
- **Test Steps:** Từ UI, tạo HLV, sửa giá sản phẩm, hoặc gán mã CTV. Đọc response. Gọi confirm-password đúng mật khẩu rồi lặp một ghi. Đợi quá 10 phút hoặc xóa cookie step-up rồi ghi lần nữa.
- **Test Data:** Cookie `taptot_access`. Không gắn `Authorization: Bearer`.
- **Expected Result:** Trước step-up: 403, `code=admin_step_up`, message `Nhập lại mật khẩu để thao tác quản trị.` Không tạo user và không đổi giá. Sau confirm-password: ghi thành công. Hết 10 phút: 403 trở lại. Một test Bearer bỏ qua step-up không tính Pass cho case này.
- **Priority:** Critical
- **Test Type:** Security, UI
