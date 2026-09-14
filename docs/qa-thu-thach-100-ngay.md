# QA — Thử thách 100 ngày

Checklist thủ công cho flow generate / overview / guest. Pytest tự động cover request, periodization, nutrition blocks, expand, TTL, và generate (mocked meals) — xem `api/tests/test_challenge_*`, `test_nutrition_*`, `test_guest_plan_ttl.py`, `test_workout_generation_integration.py`.

## Tiền điều kiện

- API + frontend chạy local; tài khoản guest và user đăng nhập sẵn sàng.
- Library foods có dữ liệu (generate meal thật; integration test mock khi thiếu bảng `foods`).

## Wizard (Plan AI)

- [ ] Checkbox **Thử thách 100 ngày thay đổi bản thân** bật → duration khóa **14 tuần** (≈ 100 ngày); slider thời gian thường không vượt 8 khi tắt challenge.
- [ ] Generate với challenge: response/insights có `challenge_100_days`, `duration_weeks: 14`, `curriculum` / `week_templates`.
- [ ] Generate **không** tick challenge: không có `challenge_100_days`; không leak label curriculum 12 tuần cũ.
- [ ] Alias cũ `curriculum_12_weeks` (nếu client gửi) vẫn map sang challenge 14 tuần.

## Overview / lịch

- [ ] Card **Thử thách 100 ngày** hiện khi plan challenge.
- [ ] Tiêu đề tuần dạng `Pha M · Tuần W` (pha 1: 1–4, pha 2: 5–8, pha 3: 9–14).
- [ ] Deload rõ ở tuần **4, 8, 14** (title/notes chứa Deload).
- [ ] Đủ **98 ngày** (14×7) sau expand từ template.
- [ ] 3 nutrition blocks khớp range tuần 1–4 / 5–8 / 9–14; check-in interval **28 ngày**.
- [ ] Mục tiêu calo deload trên cut ở tuần 4/8/14 (cao hơn tuần cut trong cùng block nếu áp dụng).
- [ ] Insights có `challenge_variation` (chest_ab, swaps_per_phase).
- [ ] Tuần có ≥2 buổi push: buổi ngực 1 flat+incline, buổi ngực 2 flat+decline (hoặc fallback có trong fallbacks).
- [ ] Pha 2/3 (tuần 5+ / 9+): secondary/iso khác pha 1; flat neo giữ nguyên.

## Guest TTL

- [ ] Guest **không** challenge: TTL ~**100** ngày (hết hạn sau ~100).
- [ ] Guest **có** challenge: TTL ~**110** ngày (copy overview: “Lịch giữ 110 ngày”).
- [ ] User đăng nhập: plan không bị xóa theo guest TTL.

## Regression nhanh

- [ ] Level 4+ vẫn bị chặn generate (không liên quan challenge).
- [ ] Plan 4–8 tuần thường: deload chỉ tuần cuối theo profile (không ép 4/8/14).
- [ ] Mobile: checkbox + overview card đọc được, không che CTA.

## Pytest (CI / local)

```bash
cd api
python -m pytest tests/test_challenge_100_request.py tests/test_challenge_variation.py tests/test_nutrition_checkin_due.py tests/test_guest_plan_ttl.py tests/test_periodization.py tests/test_nutrition_blocks.py tests/test_challenge_plan_expand.py tests/test_phase_templates.py tests/test_workout_generation_integration.py::test_generate_workout_challenge_100_days tests/test_workout_generation_integration.py::test_generate_workout_non_challenge_no_curriculum_leak -q
```
