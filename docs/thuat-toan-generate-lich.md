# Thuật toán generate lịch tập TAPTOT (V1.11)

Tài liệu tóm tắt **cách hệ thống đang tạo lịch** — API `POST /api/v1/ai/generate-workout-schedule`.

Phiên bản generator: `master_v1_11_openai_pick`.

**OpenAI chọn bài và đề xuất set/rep** trong shortlist (đã lọc theo input + Master). Rule engine gửi `dose_bounds`, kiểm tra kết quả và fallback prescription nếu dose sai; model không được đổi số slot. Thiếu API key / OpenAI lỗi / JSON sai phần chọn bài → **fail cứng** (không fallback deterministic). OpenAI lời khuyên HLV vẫn tuỳ chọn (fail soft).

Entry: `api/app/services/workout_generation/service.py` → `generate_workout`.

---

## 1. Tư duy

Không bắt đầu bằng “hôm nay Bench hay Dumbbell Press?”.

Thứ tự:

1. Người này **cần gì** (mục tiêu, chỗ tập, thời gian, test thể lực).
2. **Khung tuần** (split, số buổi) từ Master + overlay.
3. Mỗi buổi: **recipe** (số bài theo phút) + **shortlist** (lọc dụng cụ / chấn thương / độ khó).
4. **OpenAI** chọn `exercise_ids` và đề xuất set/rep trong biên an toàn (một lần cho cả tuần).
5. Validator kẹp **set / rep / giây giữ** theo test thể lực; dose sai dùng prescription mặc định.
6. Kẹp **hard sets** theo budget tuần.
7. Nhân ra nhiều tuần → TDEE/macro + lưu plan.

```
User profile + fitness tests
        ↓
TrainingCapacity (effective_level, strength_tier)
        ↓
WEEK_MATRIX → Split score overlay → khung tuần
        ↓
Mỗi buổi: recipe + shortlist
        ↓
OpenAI pick exercise_ids + đề xuất dose (hard fail nếu lỗi chọn bài)
        ↓
Rule clamp (fitness tests + prescription) + weekly hard-set budget
        ↓
Periodization → TDEE/macro + lưu plan
```

---

## 2. Input (wizard AI)

| Nhóm | Trường | Vai trò |
|------|--------|---------|
| Hồ sơ | `goal`, `gender`, `age`, `height_cm`, `weight_kg`, `activity`, `kg_per_week` (0,5–1 khi giảm cân) | TDEE / macro. Split **không** theo giới. `activity` không cắt số buổi (cảnh báo wizard nếu sedentary + ≥5 buổi). |
| Tập | `experience_level` 1–3, `sessions_per_week` 2–6, `session_minutes`, `duration_weeks` | Độ khó, số buổi, số bài/buổi, số tuần |
| Chỗ | `location` = gym \| home | Gym không lọc dụng cụ user; home lọc |
| Dụng cụ (home) | `equipment_list`, `no_equipment`, `ai_suggest_equipment` | Candidate bài tại nhà |
| Ưu tiên | `focus_areas`: nguc, lung, vai, chan, mong, tay, bung, eo | Score + quota + nới budget |
| Mục tiêu phụ | `extra_goals`: strength, endurance, mental_health, heartbreak_recovery | Rep/RPE/LISS — không đổi chọn bài |
| Test | `fitness_baseline`: chống đẩy, xà, plank, squat | Capacity — không tin mỗi “số tháng tập” |
| Khác | `food_ids`, `ai_suggest_foods`, `health_note` | Thực đơn (rule engine) / deny list khớp (từ khóa) |

Level 4+ (24 tháng) **chặn**, chưa generate. **Thử thách 100 ngày** (`challenge_100_days`) → `duration_weeks = 14` (3 pha: tuần 1–4 / 5–8 / 9–14; deload tuần 4/8/14).

---

## 3. Capacity (test thể lực)

File: `capacity.py`

Mỗi test điểm 0 / 1 / 2. **Thiếu test thì bỏ qua**, không tính 0.

| Test | 0 | 1 | 2 |
|------|---|---|---|
| Chống đẩy | < 5 | 5–14 | ≥ 15 |
| Squat | < 10 | 10–24 | ≥ 25 |
| Plank (giây) | < 20 | 20–59 | ≥ 60 |
| Xà | < 1 | 1–7 | ≥ 8 |

Trung bình điểm → `strength_tier`:

- ≤ 0.75 → `weak`
- ≥ 1.5 → `strong`
- còn lại / không có test → `ok`

`effective_level`:

- `weak` → hạ 1 bậc (sàn 1). Ví dụ khai L3 + test yếu → L2.
- `strong` **không** tự nâng level nếu user chọn L1.
- Khai **L3** mà dùng **< 2 test** → `effective_level = 2` (lịch như 1–6 tháng). Không chặn generate.

`effective_level` dùng cho: band độ khó, prescription, khung Master, budget sets, periodization. `strength_tier=weak` còn làm dịu profile overload.

---

## 4. Split (khung tuần)

Hai lớp, **không xóa** ma trận Master.

### 4.1 Default — `WEEK_MATRIX`

File: `schedule_spec_master.py` (đồng bộ frontend `scheduleSpecMaster.ts`).

Khóa matrix vẫn có `gender`, nhưng lookup **luôn dùng template male** → nam/nữ cùng khung. Focus mông/chân xử lý bằng `focus_areas`, không bằng split nữ riêng.

Default 3 buổi (gym/home) ở mọi mức kinh nghiệm: **PPL**.

Map level → khóa kinh nghiệm: L1 `0-1`, L2 `1-6`, L3 `6-24`.

Số phút buổi (`GYM_SESSION_BY_MIN` / `HOME_SESSION_BY_MIN`) quyết định **bao nhiêu compound / isolation**, không đổi tên split.

### 4.2 Overlay — `split_score.py`

Lấy default + vài ứng viên cùng số buổi (PPL ↔ Full Body / UL; 6 buổi tránh PPL×2). Default **+10** (giữ matrix trừ khi ứng viên thắng rõ).

| Điều kiện | Điểm |
|-----------|------|
| Beginner hoặc `weak` + 3 buổi | PPL +30, UL +18, FB +12 (giữ PPL của matrix) |
| L1 / weak + 5 buổi | UL (Upper, Lower, Upper, Lower, Full Body); trần 5 buổi; PPLUL điểm thấp |
| L1 + 6 buổi | UL lặp (không PPL×2 / không ưu tiên PPLUL); beginner vẫn kẹp tối đa 5 buổi |
| Goal tăng cơ/tăng cân + ≥ 4 buổi (không beginner/weak) | PPL +8, UL +6 |
| Goal giảm mỡ + ≤ 3 buổi | FB +8, UL +4, PPL −4 |
| Focus chân/mông | UL/PPL +4 |
| Focus ngực/lưng + ≥ 4 buổi | PPL/UL +3 |

Kết quả: `week_code` + `split_reason_vi` nếu đổi so với matrix.

Mỗi ngày có `split_role`: `fb`, `upper`, `lower`, `push`, `pull`, `legs`, `core`.

---

## 5. Recipe buổi (thời lượng)

File: `session_blocks.py` + spec Master. Bucket phút: 30 / 45 / 60 / 75 / 90.

Ví dụ gym 45 phút: warmup + ~2 compound + ~2 isolation + cooldown. Home: `resistance` + `conditioning` (map sang prescription compound / isolation).

Bảng phút gym 45 **không** có cardio. Nếu `extra_goals` có `endurance` **hoặc** mục tiêu `lose_weight` và buổi ≥ 45 phút: **inject** LISS 8–10 phút cuối (không cắt compound). Cardio bảng phút vẫn từ ≥ 60 phút (`cardio_on_lift_days`).

**Không** generate 8 bài cho người 30 phút — số slot đến từ bảng phút.

---

## 6. Shortlist bài

File: `shortlist.py`. Tối đa ~16 ứng viên / block.

Lọc `exercises`:

- `is_active`
- **Difficulty band** theo `effective_level`: L1 `{1,2}`; L2 `{1,2,3}`; L3 `{1,2,3,4}` (vẫn giữ bài dễ)
- **Venue**: gym / home / both. Gym không bắt chọn dụng cụ. Home + `no_equipment` loại bài gắn `exercise_equipment`. Home + list dụng cụ giữ **bài dùng dụng cụ đã chọn ∪ bài không dụng cụ** (SQL lọc OR) — bodyweight chỉ bị cắt ở tầng pool gửi model (xem *Home có dụng cụ* bên dưới).
- `movement_role` khớp block

Chấm điểm (cộng dồn):

| Tín hiệu | Điểm |
|----------|------|
| `movement_pattern` thuộc split (push day → h_push, v_push, …) | +30 |
| Nhóm cơ gợi ý của split | +15 |
| `focus_areas` trùng slug | +20 |
| Gần độ khó mục tiêu (L1/L2 → 2, L3 → 3) | +8 / +4 / +1 theo khoảng cách |
| Đúng movement_role block | +10 |
| Pattern lệch split (block sức mạnh) | −40 |

Giữ đa dạng pattern (không 4 bài cùng một family).

**Deny list khớp / tuổi** (`injury_filters.py`): parse `health_note` (gối, vai, lưng, cổ tay, cổ chân) + tuổi ≥ 45 (plyo/kipping). Lọc sau `is_denied_for_split`. Shortlist trống → nới **pattern**, giữ family/token, ghi note; **không** fail generate.

### Home có dụng cụ: gear-first, bodyweight chỉ khi thiếu (`home_gear_priority.py`)

Áp dụng khi `location=home` và `equipment_list` không rỗng. `ShortlistItem` mang `equipment_slugs`; tier `0` = dùng dụng cụ user chọn, `1` = bodyweight, `2` = dụng cụ khác (đã bị filter).

1. **Pool slot gửi OpenAI** (`tier_slot_pool`, gọi trong `collect_day_shortlists_for_prompt`): `need = max(3, số buổi cùng split × biến_thể + 1)` (biến_thể = 3 nếu thử thách 100 ngày). Nếu slot có ≥ `need` bài gear → **cắt hết bodyweight** khỏi pool; nếu thiếu → bù đúng số thiếu bằng bodyweight (ưu tiên bài trúng `prefer` của slot), gear luôn đứng trước. Bài bodyweight còn lại trong pool được gắn `bw: 1`; bài gear không thêm field (tiết kiệm token). Block lẻ (không qua slot) chỉ sort gear-first trước `PROMPT_SHORTLIST_CAP`.
2. **Hậu kiểm lặp tuần** (`enforce_home_gear_variety`, chạy trong `_finish_generated_week` trước `apply_home_implement_coverage`): cùng `exercise_id` ≤ 2 lần/tuần, cùng `lift_stem` ≤ 3 trên phần main. Bài vượt cap được thay bằng bài **gear** cùng pattern (+ cùng cơ trước, nới cơ sau) chưa dùng trong tuần → hết gear mới lấy **bodyweight** → không có thì giữ nguyên và ghi `unchanged_no_alternative`. L1 không nhận hít xà/dip trần.
3. Bias phụ: `HOME_GEAR_HINT` nói rõ pool gear-first / `bw` là fallback; `_score_slot` ±35 theo `_gear`/`bw` cho đường fill deterministic; `repair_block_picks(user_gear=…)` fill gear trước.
4. Sửa kèm để gear thật sự lọt pool: `Ép ngực tạ đơn/tạ đòn` không còn bị `_COMPOUND_AVOID` "ép ngực" loại khỏi slot ngực (`is_free_weight_chest_press`); `Chèo tạ đơn / tạ ấm` không còn bị deny "row tại nhà" khi user có tạ đơn (`is_home_denied_exercise(exercise_slugs=…)`).

Insight: `insights.home_gear = {equipment, gear_share, thin_pools[], replaced[], unchanged_no_alternative[]}`.

Kho bài hiện tại (home/both): tạ đơn ~84 bài đủ gen gần 100 % gear; dây 18, xà đơn 9, vòng 14, xà kép 1 → dây không có `h_push`, xà không có squat/hinge nên bodyweight bù là đúng thiết kế, không phải lỗi.

---

## 7. Chọn bài

File: `openai_picker.py` → `pick_with_openai` + `validate_openai_picks` (đường production).

1. Gom shortlist cả tuần → một request OpenAI (kèm profile: goal, level, location, focus, injury).
2. Model chỉ trả `exercise_ids` ∈ shortlist; đúng `count_max` mỗi block bắt buộc.
3. Validate cứng: id lạ / sai số lượng / thiếu ngày / trùng strength trong buổi → fail.
4. **Không** gọi `deterministic_picks`, **không** chạy coverage/quota repair để ghi đè lựa chọn AI.
5. `deterministic_picks` vẫn giữ trong file cho unit test / debug nội bộ.

Set/rep không do OpenAI — xem §8.

---

## 8. Set / rep / RPE

File: `exercise_prescription.py`

Bảng DB `exercise_prescription_defaults`: level × compound|isolation → `default_sets` + **tâm rep**. Engine xuất **khoảng**:

- Compound: tâm ± 2; tăng cơ nới +1 cận trên. Tâm 10 → `8-12` (tăng cơ `8-13` lúc gán RX, không phải periodization).
- Isolation: tâm ± 3; giảm mỡ nới +2 cận trên. Tâm 15 → `12-18` (giảm mỡ `12-20`).

RPE ghi `notes_vi` (không cột DB): L1 ≈ 7; L2 ≈ 8; L3 compound 8 / isolation 7. `mental_health` / `heartbreak_recovery`: RPE −1 (sàn 6).

`extra_goals.strength` (compound): tâm 6 → khoảng **5–8**, mọi level.

L3 + mục tiêu tăng cơ/tăng cân **không** tick sức mạnh: tâm compound **10** → **8–12**. Có `strength`: giữ 5–8.

Compound/resistance đầu buổi: note khởi động tăng dần tạ + cue tăng tạ khi đạt cận trên range.

Nghỉ: compound ~120s, isolation ~75s.

---

## 9. Budget volume tuần (hard sets)

File: `weekly_volume.py` → `apply_weekly_dose`

Đếm **set trực tiếp** theo nhóm cơ chính (không nhân 0.5 cho cơ phụ): ngực, lưng, quads, hinge, vai, **biceps**, **triceps**, core.

Budget **recommended_min / target / max** (tier `ok`; `weak` ×0.8, `strong` ×1.1). Focus nới max (+2) và sàn recommended. `recommended_min` chỉ **ghi note** khi nhóm focus thiếu — không fail generate, không tự thêm bài.

| Nhóm | L1 | L2 | L3 |
|------|----|----|-----|
| ngực / lưng / quads / hinge | 6–8–12 | 6–9–14 | 8–10–16 |
| vai | 6–8–12 | 4–6–10 | 4–8–12 |
| biceps / triceps | 0–2–4 | 0–3–6 | 2–4–8 |
| core | 0–4–8 | 0–6–10 | 0–6–12 |

Quy tắc kẹp:

- Vượt **max sets** → bỏ isolation (kể cả focus) từ cuối tuần; bỏ bài trùng pattern; bỏ vai khỏi Legs/Lower.
- L1 cap **set/buổi** tối đa 16.
- `VOLUME_FAIL` → không lưu plan.
- **Không** drop isolation nếu đó là bài cuối phủ family bắt buộc của `split_role` (coverage).
- L1 thêm cap **set/buổi** ≈ 14 @ 45 phút (scale theo phút, sàn 8); coverage thắng cap.
- **Không** xóa compound.
- Sau periodization: `create_plan` kẹp **từng tuần** (tránh tuần 4 +set vượt max).

---

## 10. Nhiều tuần (periodization)

File: `periodization.py`, gọi khi `duration_weeks` > 1. Nhân template 1 tuần × N (tối đa 13).

**Lịch thường (4–8 tuần):** một tuần mẫu; deload **tuần cuối** nếu đủ `deload_min_weeks` theo profile.

**Thử thách 100 ngày (`challenge_100_days`):** 14 tuần = 3 pha.

1. OpenAI pick **1 tuần** → `challenge_variation.py` gán **Chest A/B** trong tuần (chỉ challenge):
   - Buổi ngực 1 (`push` / `upper` có ngực): compound **flat + incline**.
   - Buổi ngực 2: **flat + decline** (thiếu decline → dip / incline khác, ghi `insights.challenge_variation.fallbacks`).
   - OHP / không-ngực không bị rule góc.
2. `phase_templates.py` tạo 3 template: đổi **secondary press + isolation** theo pha (pool từ shortlist/meta, không gọi lại OpenAI) rồi gắn RPE/sets:
   - Pha 1 nền tảng: iso “dễ” (cáp/máy/fly) nếu có; RPE 6–7.
   - Pha 2 tăng áp lực: swap secondary + 1–2 iso; nghỉ ngắn hơn; RPE 7–8.
   - Pha 3 tinh chỉnh: focus `chest` bias incline trên secondary; +1 set focus; RPE 7–8.
   - **Neo cố định:** 1 flat press / buổi ngực + compound chính không-ngực.
3. `expand_plan_days_for_weeks(..., curriculum=True, week_templates=[...])`:
   - Tuần 1–4 / 5–8 / 9–14 dùng template pha tương ứng.
   - Deload tuần **4, 8, 14**.
   - Ramp set/rest **reset mỗi pha**.
4. Title: `Pha M · Tuần W — Deload: …`
5. Insights: `curriculum`, `week_templates`, `challenge_100_days`, `challenge_variation`.

Góc bench nhận diện bằng **tên bài** (flat / incline / decline / dip) — chưa có cột DB.

**Rep range giữ nguyên** (`8-12` không thành `8-13` theo tuần). Không giả lập tăng tạ — chưa có journal.

| Profile | Level | Set auto | Range | Deload |
|---------|-------|----------|-------|--------|
| Novice | L1–2 | không | cố định | tuần cuối nếu ≥ **6** tuần: −1 set, nghỉ ×1.15 |
| Developing | L3 | thêm set từ tuần 4, tối đa +1 (rồi kẹp lại budget tuần) | cố định | ≥ 4 tuần: −1 set, nghỉ ×1.20 |
| Experienced | (map L4–5; generate hiện chặn L4+) | ramp set sớm hơn, tối đa +2 | cố định | như developing |

`weak` hạ một bậc profile (experienced → developing).

Cue (notes + advice): *Khi làm được cận trên range với RPE mục tiêu, tăng tạ nhỏ (khoảng 2.5 kg) phiên sau.*

---

## 11. Dinh dưỡng (đi kèm lịch)

Mifflin-St Jeor × hệ số `activity` → TDEE, rồi kẹp an toàn.

- Giảm cân: thâm hụt theo `kg_per_week`, tối đa ~25% TDEE / 750 kcal; sàn calo an toàn. **Macro:** đạm ~2.0 g/kg (sàn 1.6), béo sàn ~0.7 g/kg hoặc ≥20% kcal (hormone), carb = phần còn lại.
- Tăng cân / tăng cơ: surplus (tăng cơ +300 kcal). Đạm ~2.0 g/kg, béo ~0.9 g/kg (sàn hormone), carb phần còn lại.
- Giữ cân: TDEE. Đạm ~1.8 g/kg (trong band 1.6–2.0), béo ~0.8 g/kg, carb phần còn lại.

### Calo linh hoạt theo tuần

Sau khi có `avg_target` (mức trung bình/ngày), `build_weekly_calorie_schedule()` phân bổ calo 7 ngày:

- **Strength** (upper/lower/push/…): hệ số cao nhất (vd giảm cân ×1.05).
- **Full body** (fb/fb_a/…): gần trung bình.
- **Cardio / recovery**: thấp hơn strength.
- **Ngày nghỉ** (`7 − S` buổi): thấp nhất; `rest_target = (7×avg − Σ train) / R`.

Tổng 7 ngày = `7 × avg_target` (±10 kcal). Mỗi mức calo → macro riêng (`_macros_for`). Lưu `target_*` trên từng `user_daily_plan_days`; plan-level `target_calories` = trung bình (backward compatible).

Insights thêm `rest_day_nutrition` + `rest_day_meals` (template ngày nghỉ).

### Block dinh dưỡng (V1 dự báo + V2 check-in)

Khi gen lịch nhiều tuần với mục tiêu giảm/tăng cân và có `weight_kg`:

1. `build_nutrition_blocks()` — mặc định block **2 tuần**; thử thách 100 ngày dùng **3 block** khớp pha (`1–4`, `5–8`, `9–14`).
2. Cân dự báo mỗi block theo số tuần đã qua trước block đó.
3. Gọi lại `estimate_targets()` + `build_weekly_calorie_schedule()` cho từng block.
4. **Kẹp bước nhảy:** ±150 kcal (block 2 tuần) hoặc ±250 kcal (block theo pha).
5. `generate_meals_with_blocks()` — ráp món bằng thuật toán (`meal_engine`, **không** gọi OpenAI), scale khẩu phần theo target từng block. Challenge xoay món theo `block_index` (3 pha không copy cùng menu). Trên cut + challenge: thêm `deload_sessions` gần maintenance cho tuần deload **4/8/14**.
6. Sau `expand_plan_days_for_weeks()` → `apply_nutrition_blocks_to_expanded_days()` gán meals + `target_*` theo tuần (parse `Tuần N` trong `title_vi`).

Insights lưu `nutrition_blocks[]`, `sessions_per_week`, `nutrition_block_size`, `nutrition_payload` (metadata regen). Plan-level `target_calories` = block 0 (backward compatible).

**V2 check-in** (`POST /my-plans/{id}/nutrition-checkin`): owner nhập cân mới → tính lại calo (kẹp ±150, rule adaptive nhanh/chậm hơn mục tiêu) → regen meals từ block/tuần hiện tại trở đi; append `nutrition_checkins[]`, cập nhật `next_nutrition_checkin_due` (+14 ngày thường / **+28 ngày** thử thách 100 ngày).

### Thực đơn (rule engine)

File: `meal_engine.py`. **Không** dùng OpenAI chọn món.

1. Pool: `ai_suggest_foods` → nguyên liệu tươi (`ingredient`), gồm cả `raw`; ưu tiên `default_for_ai`. User tự chọn → `food_ids` (cần ≥2 đạm + ≥2 tinh bột).
2. Mỗi bữa: đĩa đạm + tinh bột + rau (không còn món hoàn chỉnh).
3. **`fit_meals_to_target()`** — scale khẩu phần lặp (±10% so với `target_calories` ngày):
   - Scale đều theo loại món (không kẹp factor ×1.6 cũ); cap servings: đạm 0.5–3.0 (mở rộng tối đa 6.0 khi cần), tinh bột/rau 0.5–4.0 (tối đa 5.0), món hoàn chỉnh 0.75–1.5.
   - Bump đạm nếu thiếu; trim/bù tinh bột để giữ calo ±10%.
   - **`_fit_macros_to_target()`** sau fit calo: đạm & béo ≥88% mục tiêu, tinh bột ±12% (béo ưu tiên sàn hormone trước khi cắt carb).
   - Khi gán template theo ngày (`apply_meals_with_schedule`), re-fit theo `day_targets` nếu lệch.
   - Nếu vẫn lệch >10% (pool quá ít món): cảnh báo trong `meal_notes`, không fail gen.
4. Template riêng theo loại buổi (strength / fullbody / cardio) + mẫu **ngày nghỉ**; gán meals theo `split_role` từng ngày tập.
5. Nhiều block (challenge 3 pha): `rotation_index = block_index` để xoay món, không copy menu tháng này sang tháng kia.

App **không** quản lý giờ tập trong ngày hay timing bữa (trước/sau tập) — người dùng tự sắp xếp lịch ăn/tập ngoài hệ thống.

Món: `food_ids` / AI pool — **tách** khỏi thuật toán chọn bài.

---

## 12. Output lưu DB

`UserDailyPlan` + ngày + bài + (tuỳ) món.

- `source = ai`
- `experience_level` = **effective_level**
- `strength_tier` trên payload create
- Insights: `week_code`, `split_reason_vi`, `generator = master_v1_9`, `effective_level`, `volume_meta`, `focus_slugs`
- Mô tả / advice: lý do đổi split, test yếu, ưu tiên nhóm cơ, note volume nếu thiếu

Frontend hiện `reps` dạng `8-12` và note RPE sẵn.

---

## 13. Catalog nhóm cơ (kho bài tập)

`muscle_groups` có `parent_id` + `is_filter_only`. Nhóm **cha** (`chest`, `back`, …) chỉ dùng filter; bài tập gán **nhóm lá** (`chest-upper`, `back-lats`, …).

- Seed: [`seeds/muscle_groups_hierarchy.json`](seeds/muscle_groups_hierarchy.json); startup `ensure_muscle_groups_hierarchy`.
- Remap rule-based: [`exercise_muscle_region.py`](api/app/services/exercise_muscle_region.py); script `scripts/classify_exercise_muscle_regions.py`.
- API filter: `muscle_group_ids` mở rộng sang con; `GET /search/muscle-groups/tree` cho FE.
- Generate: `CHEST_SLUGS` / `BACK_SLUGS` / … gồm slug con + legacy alias.

---

## 14. File code chính

| File | Việc |
|------|------|
| `workout_generation/session_policy.py` | Cap buổi/phút/tuần theo level |
| `capacity.py` | Test → tier / level; L3 thiếu test → L2 |
| `injury_filters.py` | Deny list `health_note` + tuổi ≥ 45 |
| `split_score.py` | Overlay split (L1 5–6 buổi ưu tiên UL) |
| `schedule_spec_master.py` | WEEK_MATRIX + phút/buổi |
| `shortlist.py` | Filter + score |
| `home_gear_priority.py` | Home có dụng cụ: pool gear-first, bodyweight bù theo ngưỡng, cap lặp tuần |
| `openai_picker.py` | OpenAI chọn id trong shortlist (fail cứng); `deterministic_picks` chỉ test |
| `muscle_quotas.py` / `coverage.py` / `repair.py` | Quota/coverage (test/debug); repair trim trên đường OpenAI |
| `focus.py` | Ưu tiên cơ (score shortlist) |
| `weekly_volume.py` | Budget hard sets / tuần |
| `assemble.py` | Ráp ngày + prescription |
| `workout_rest.py` | Rest mặc định: compound **3p** (180s), isolation/conditioning **1p30s** (90s) |
| `session_duration.py` | Ước lượng phút buổi + fill theo `session_minutes` |
| `exercise_prescription.py` | Set / range / RPE |
| `nutrition_targets.py` | TDEE / macro + kẹp an toàn |
| `meal_engine.py` | Pool món, ráp bữa, scale khẩu phần |
| `periodization.py` | Nhân tuần / mesocycle curriculum |
| `phase_templates.py` | 3 biến thể tuần cho thử thách 100 ngày (RPE/sets + gọi variation) |
| `challenge_variation.py` | Chest A/B flat/incline/decline + swap bài theo pha |
| `exercise_muscle_region.py` | Phân vùng cơ chi tiết (ngực trên/giữa/dưới, xô, vai trước/giữa/sau, …) |
| `muscle_group_hierarchy_seed.py` | Seed cây muscle_groups + remap bài khỏi nhóm cha |
| `coach_advice.py` | Copy HLV (OpenAI tuỳ chọn) |

---

## 15. Cố ý chưa làm

- Học từ journal / RPE thực tế / tăng tạ tự động theo log
- Fractional sets (0.5 indirect) — chờ mapping `secondary_muscles` sạch
- `movement_capacity` theo pattern, cột `technical_complexity`
- Goal sức mạnh sâu 3–6 reps / periodization sức mạnh riêng (wizard `strength` hiện kẹp compound ~5–8)
- ML recommendation
- Engine chấn thương y khoa (hiện chỉ từ khóa `health_note`)
- Bỏ `WEEK_MATRIX` hoặc bắt gym chọn dụng cụ
- Cột `rpe` riêng trên DB
- Generate cho level 4+ (24 tháng)

Bước tiếp theo hợp lý khi có user thật: **gắn log buổi tập vào score / overload**, không thay pipeline trên.
