# Gen lịch tập tại nhà (có dụng cụ) + OpenAI

Tài liệu tổng hợp thuật toán hiện tại của TAPTOT: **engine quyết định khung, pool bài, an toàn và liều lượng**; **OpenAI chỉ chọn bài (và đề xuất sets/reps) trong danh sách đã lọc**. Dùng để nghiên cứu và phát triển tiếp — không đi sâu vào chi tiết triển khai (SQL, schema JSON, tên hàm).

Hai nhánh lớn:

1. **Lịch thường** — một tuần mẫu, lặp theo số tuần.
2. **Thử thách 100 ngày** (~14 tuần, 3 pha) — OpenAI chọn 3 lần, mỗi pha tránh bài/pha trước; có tuần A/B (đổi isolation).

Nhánh **làm quen (familiarization)** là curriculum riêng, không đi theo pipeline này.

---

## Ý tưởng cốt lõi

Không để AI tự bịa bài hay tự thiết kế buổi tập. Luồng luôn là:

```
Wizard (người dùng)
  → chuẩn hóa đầu vào + sức tập
  → khung tuần (split: Push/Pull/Legs hoặc Full body…)
  → công thức buổi (bao nhiêu bài compound / isolation / cardio)
  → shortlist từ catalog, đã lọc dụng cụ / chấn thương / trình độ
  → slot (ô bài: ngực nằm, kéo dọc, squat…) + pool ứng viên
  → ưu tiên dụng cụ đã chọn, bodyweight chỉ khi thiếu lựa chọn
  → gắn biên liều lượng (sets/reps cho phép)
  → OpenAI chọn id trong pool + đề xuất dose trong biên
  → ráp buổi → chỉnh volume, thời lượng, đa dạng dụng cụ
  → bữa ăn + lưu plan
```

OpenAI **fail cứng** nếu thiếu key, tắt flag, trả thiếu ngày, hoặc chọn id không nằm trong pool. Không có fallback “tự pick ngẫu nhiên im lặng”.

---

## Đầu vào wizard (liên quan gen có dụng cụ)

- Mục tiêu: giảm / giữ / tăng cân (tăng cơ gom về tăng cân khi đặt tên lịch).
- Giới tính, tuổi, chiều cao, cân, mức hoạt động hàng ngày.
- **Địa điểm luôn là nhà** trên đường gen hiện tại.
- **Bắt buộc chọn dụng cụ.** Bộ được phép:
  - Dây kháng lực (khi gen → tube ngũ sắc).
  - Tạ đơn.
  - Xà đơn **và** vòng treo (chọn một cái thì hệ thống ghép cặp cả hai).
- Số buổi/tuần, phút/buổi, số tuần (hoặc flag 100 ngày).
- Trình độ tự khai (1–3; trên 12 tháng đang chặn).
- Vùng ưu tiên (ngực, lưng, chân…).
- Ghi chú sức khỏe / chấn thương.
- Test thể lực (chống đẩy, squat, plank, kéo xà / chèo / pulldown, tạ đơn…).
- Dị ứng / sở thích ăn (cho engine bữa, không phải buổi tập).

Nếu danh sách dụng cụ trống hoặc slug lạ → lỗi, không gen.

---

## Từng bước xử lý

### 1. Chuẩn hóa dụng cụ

- Chỉ giữ 3 kit wizard.
- Dây công khai → kit tube khi lọc catalog.
- Xà và vòng treo luôn đi cặp (kỹ năng kéo / chống đẩy trên vòng cần cả hai).

Mục đích: catalog có nhiều slug; wizard chỉ mở vài bộ thật sự hỗ trợ tại nhà.

### 2. Ước lượng sức tập (capacity)

Không tin hoàn toàn “tôi tập được 6–12 tháng”.

- Mỗi bài test được chấm yếu / ổn / mạnh (ngưỡng nam–nữ khác nhau; dây có hệ số màu).
- Gộp thành **bậc sức** (`weak` / `ok` / `strong`) và **trình độ hiệu lực** (có thể hạ xuống so với tự khai).
- Nếu yếu: volume tuần thận trọng hơn, policy có thể giảm số buổi / phút / split nặng.

Thử thách 100 ngày: nếu test thiếu hoặc quá yếu, hệ thống **điền load ước lượng** theo cân, giới tính, kit (và chế độ “dễ” nếu vẫn yếu) để pha sau không bị kẹt pool trống.

Song song: **cổng kỹ năng kéo** — đã test kéo xà trần hay chưa, có nên bắt đầu từ ring row / assisted / scapular.

### 3. Chấn thương và chính sách buổi

- Đọc ghi chú sức khỏe + tuổi → danh sách bài/pattern cấm + ghi chú tiếng Việt.
- Policy: trần buổi, phút, tuần; có cardio cuối buổi nâng tạ không; LISS (đi bộ Zone 2) hay không; có cho split dày (PPL×2…) không.

Số buổi yêu cầu bị **kẹp** theo sức phục hồi (thường 2–6, và không vượt policy).

Vùng focus → nhóm cơ slug để sau này ưu tiên trong pool và volume.

### 4. Chọn khung tuần (master frame)

Bảng master: trình độ × số buổi × giới tính × nhà × có đồ.

Ví dụ: 3 buổi có thể Full body xoay A/B/C; 4–6 buổi có thể Upper/Lower hoặc Push/Pull/Legs.

Có bước **chấm split**: nếu default không khớp mục tiêu / focus / sức, đổi `week_code` rồi lấy khung ngày (mỗi ngày một `split_role` + nhãn).

Full body: mỗi buổi được **xoay vai trò pick** (ngày 1 giống Push-ish, ngày 2 Pull-ish…) và đổi tiêu đề buổi, để không 3 ngày bài na ná.

### 5. Công thức buổi (recipe)

Theo địa điểm, phút, vai trò split, trình độ, policy cardio:

- Warmup / giãn.
- Khối sức: nhà thường gộp **resistance** (compound + isolation), gym tách compound / accessory.
- Core, cardio/conditioning cuối buổi (tùy policy).

Số bài `count_max` theo phút: buổi ngắn ít bài hơn; ~90 phút đủ compound + isolation + LISS, không nhồi thêm press.

### 6. Lọc catalog → shortlist

Mỗi khối buổi lấy bài từ DB, đã:

- Đúng venue nhà.
- Dụng cụ: mọi slug gắn bài phải nằm trong kit user (sau alias dây/xà).
- Độ khó khớp trình độ.
- Vai trò động tác (compound / isolation / cardio…).
- Pattern hợp split (Push không kéo xà nặng; Pull nhà không đồ ≠ hít xà phòng gym).
- Không trong deny list chấn thương / split.
- Bài “đồ specialty” (vòng, bóng tường, ghế captain…) chỉ khi user có đồ đó.
- Cấm xe trượt / sled tại nhà.
- Kỹ năng: L1 không dip / muscle-up trần; kéo xà trần chỉ khi đã test hoặc pha sau.
- Ưu tiên vùng focus (điểm cộng, không độc quyền).
- Thử thách: cardio cuối buổi **whitelist** (Shadow Boxing, Jumping Jack, Jump Rope, Running Intervals, Hiking, Trail Run) — không burpee / gối cao / mountain climber.

Shortlist bị cắt số lượng để prompt không phình; cardio/core có thể lấy pool rộng hơn.

### 7. Slot buổi (khuôn Boostcamp / PPL)

Với Push / Pull / Legs / Upper / Full body, buổi được tách **ô**:

- Ngực: ô 1 nằm, ô 2 (nếu có) dốc lên — **không dốc xuống**.
- Vai, tay sau / tay trước, lưng ngang / dọc, xô, chân trước / hinge / mông…
- Số ô compound vs isolation suy từ `count_max` của recipe.

Mỗi ô có **pool** bài khớp pattern/cơ. Nếu nhà có tạ/dây và test đủ, **bỏ chống đẩy sàn** khỏi pool ngực (tránh AI chọn push-up thay press).

### 8. Ưu tiên dụng cụ (trước khi gọi AI)

Hai tầng:

**Trước pick — pool theo tầng**

- Tầng 0: bài **dùng đúng đồ user chọn**.
- Tầng 1: bodyweight (không gắn equipment).
- Tầng 2: đồ khác (lẽ ra đã lọc hết).

Nếu số bài tầng 0 ≥ ngưỡng cần (tối thiểu 3, hoặc nhiều hơn khi cùng split lặp nhiều buổi / 3 pha thử thách) → **pool chỉ còn đồ**.  
Nếu thiếu → thêm bodyweight **đủ cho đủ lựa chọn**, không nhồi cả đống BW.

Prompt đánh dấu bài BW để model biết đó là dự phòng.

**Sau ráp lịch — đa dạng trong tuần**

- Cùng một bài không quá 2 lần/tuần; cùng họ (lunge, step-up, chống đẩy, kéo xà) không quá 3.
- Trùng thì **đổi sang bài đồ chưa dùng** trong pool; BW chỉ khi hết đồ.

**Phủ kit trong tuần**

Nếu user chọn cả dây + tạ + xà/vòng, lịch không được “chỉ tạ đơn”. Engine cố **trộn implement** (đặc biệt lưng/chân ưu tiên tube; pull ưu tiên pulldown/chèo dây). Cardio nhảy dây chỉ khi user có dây nhảy (kit wizard hiện không mở nhảy dây như lựa chọn chính — hint cardio nhà thường Zone 2).

### 9. Biên liều lượng (dose bounds)

Mỗi ứng viên trong prompt mang khoảng sets/reps/rest **an toàn** theo:

- Trình độ, nhà vs gym, có load hay BW.
- Test (chống đẩy max → rep chống đẩy; kéo xà max → không bịa 10 rep nếu test = 0).
- Loại bài (giữ plank theo giây; cardio interval vs phút còn thừa).

OpenAI **được chọn trong khoảng**; ra ngoài thì hệ thống kẹp hoặc fallback prescription mặc định.

Thử thách: tôn trọng dose AI hơn lịch thường (sau đó vẫn kẹp rest/thời lượng).

### 10. Gọi OpenAI chọn bài

**Lịch thường:** gửi từng **lô 2 ngày**. Model là HLV người mới Việt Nam.

Nhiệm vụ:

- Chỉ chọn `exercise_id` trong pool của từng slot/block.
- Slot bắt buộc: đúng số bài `pick`, id khác nhau.
- Slot optional: được `[]` nếu pool trống.
- Kèm sets/reps trong `dose_bounds`.
- Không hai compound cùng pattern / cùng họ trong một buổi (hai lunge, hai step-up…).
- Ưu tiên đa dạng: tránh `avoid_ids` đã dùng các ngày trước trong tuần.
- Nhà: mix dụng cụ; ngực không decline; hint L1 xà; cardio nhà nhẹ.

Trả JSON. Thiếu ngày → retry 1 lần từng ngày; vẫn thiếu → lỗi cho user.

**Thử thách 100 ngày:** mỗi pha một lần gọi lớn hơn:

- Playbook kiến thức pha (volume, kỹ thuật, deload tuần 4/8/14).
- `avoid_ids` / `avoid_stems` từ pha trước (trừ bài “cổng kỹ năng” được mở dần, ví dụ kéo xà pha sau).
- Trả **tuần A** (compound giữ) và **tuần B** (được đổi isolation/cardio nếu pool còn lựa chọn).
- Sau mỗi pha: kẹp RPE/pha, kẹp phút buổi.

Nếu tuần B trùng A vì pool isolation chỉ còn đúng bài đã chọn → ghi insight “không có alternative”, không bịa bài.

**Bữa thử thách:** pool món → OpenAI chọn thực phẩm ưa theo pha (vẫn trong catalog), rồi engine ráp macro.

### 11. Kiểm tra lựa chọn AI (không tin mù)

Với mỗi ngày:

- Map JSON → id theo slot.
- Id phải nằm trong pool; đủ số lượng slot bắt buộc.
- Loại pattern trùng, họ trùng, bài cấm kỹ năng.
- Gắn `_dose_by_exercise` nếu hợp lệ.

Thiếu / sai → lỗi, user gen lại. Không tự điền bài “gần đúng” ngoài pool (trừ các bước **sửa sau** có kiểm soát: refill phút, đổi bài trùng, phủ kit — vẫn lấy từ shortlist ngày đó).

### 12. Ráp buổi

Với mỗi ngày:

- Lấy prescription (sets/reps/rest/ghi chú) từ catalog + dose AI đã kẹp.
- Gắn section: warmup / main / cardio.
- Sửa thiếu khối (repair) nếu AI thiếu block optional.
- Sắp bài main theo hạn ngạch cơ (không 4 bài ngực liên tiếp nếu split yêu cầu vai/tay).
- Bơm thêm bài nếu buổi quá mỏng so với phút mục tiêu (từ cùng pool).

### 13. Hoàn thiện tuần (deterministic, sau AI)

Thứ tự ý nghĩa:

1. Bỏ bài main nhà **cấm** (lọt lưới tên / specialty).
2. **Ngân sách set/tuần theo cơ** — cắt set isolation nếu ngực/lưng/chân vượt trần trình độ; có thể bỏ bài phụ nếu vẫn vượt. Ghi chú volume tiếng Việt.
3. Buổi quá mỏng → refill từ pool.
4. Top-up thêm set/bài cho gần phút mục tiêu.
5. L1: gom set cho dễ theo dõi.
6. **Kẹp thời lượng buổi** về phút đã chọn (cắt set/cardio thừa).
7. Đa dạng đồ + phủ kit (mục 8).
8. Ngày kéo: đảm bảo có pull ngang/dọc thật, không chỉ tay trước.
9. Sắp lại thứ tự main.
10. **Warmup cố định 2 ô:** 1 giãn + **primer** = bài main đầu, 1–2 set, rep khoảng nửa working (nhà) hoặc 4 rep loaded.
11. Lịch thường nhà: ghi đè dose theo test thể lực (nếu không phải thử thách đang honor AI).

### 14. Dinh dưỡng

- Ước TDEE / macro từ tuổi, cân, mục tiêu, hoạt động, số buổi.
- Lịch thường: khối macro theo số tuần; ráp thực đơn từ pool món Việt, dị ứng, bữa tập vs nghỉ.
- Thử thách: 3 khối dinh dưỡng theo 3 pha; deload ăn khác; AI gợi ý món trong pool.

### 15. HLV phụ (lịch thường, khi lưu)

OpenAI thứ hai (nếu bật) viết lời khuyên + **swap bài trong cùng allowed ids** + chỉnh duration nhẹ. Rồi kẹp phút lần nữa.

Thử thách **không** qua bước coach swap này (curriculum đã có playbook pha).

### 16. Lưu plan

- Tiêu đề: mục tiêu + timestamp.
- Mô tả = recap wizard.
- Insights: khung master, periodization, dinh dưỡng, dụng cụ, pool mỏng (phải nhét BW), bài không đổi được.
- Check-in: 14 ngày thường / 28 ngày thử thách.
- `source = ai`.

Preview (`persist=false`) gen bài nhưng bỏ bữa và một phần advice.

---

## Gợi ý OpenAI nhận (tóm tắt sản phẩm)

Profile gửi kèm: mục tiêu, giới tính, trình độ hiệu lực, bậc sức, test, buổi/phút, nhà, focus, chấn thương, `week_code`, hint ngực nhà, hint L1 xà, hint cardio, (thử thách) playbook pha.

Model **không** được:

- Bịa id.
- Đổi số bài slot.
- Chọn decline / dip L1 / muscle-up L1.
- Bỏ qua pool BW khi còn đồ chưa dùng — nhưng pool đã được cắt BW sẵn, nên đây là lớp nhắc.

---

## Điểm thiết kế quan trọng khi phát triển tiếp

| Nguyên tắc | Vì sao |
|---|---|
| AI chỉ pick trong shortlist | Catalog + an toàn pháp lý/HLV; dễ test |
| Fail cứng khi AI lỗi | Tránh lịch “rác” im lặng |
| Dụng cụ bắt buộc, 3 kit | Tránh mix catalog phòng gym vào nhà |
| Gear-first, BW top-up | User mua đồ thì phải thấy đồ trong lịch |
| Dose trong biên, volume tuần sau AI | Model hay phóng set; người mới dễ overreach |
| Slot pattern (nằm / dốc / kéo…) | Buổi có cấu trúc, không 3 bài isolation |
| Pha + avoid stem (100 ngày) | Tiến bộ + đỡ chán, vẫn cùng khung |
| Primer = bài chính | Ấm đúng pattern sẽ tập |
| Kẹp phút cuối | Wizard hứa 45' thì không ra 75' |

---

# Prompt phát triển chức năng (dùng cho agent / HLV kỹ thuật)

Copy khối dưới khi muốn **xây lại hoặc mở rộng** gen lịch nhà + dụng cụ + OpenAI, bám hành vi hiện tại.

```
Bạn sẽ thiết kế / triển khai hệ thống GEN LỊCH TẬP TẠI NHÀ CÓ DỤNG CỤ theo mô hình hybrid:

A) Engine deterministic quyết định mọi ràng buộc.
B) OpenAI CHỈ chọn bài và đề xuất sets/reps trong danh sách đã lọc.
C) Engine ráp buổi, kẹp volume/thời lượng, trộn dụng cụ, warmup, rồi bữa ăn.

## Sản phẩm
App fitness Việt Nam (TAPTOT). Đối tượng chính: người mới–trung bình (0–12 tháng).
Địa điểm gen: nhà. Không gen “không dụng cụ” trên luồng này.

## Dụng cụ wizard (bắt buộc chọn ≥1)
- Dây kháng lực → khi lọc catalog dùng kit tube ngũ sắc.
- Tạ đơn.
- Xà đơn và vòng treo luôn đi cặp (chọn 1 thì thêm cái kia).
Slug lạ hoặc list rỗng → lỗi tiếng Việt, không gen.

## Đầu vào
goal, gender, age, height, weight, activity,
equipment_list, sessions_per_week, session_minutes, duration_weeks,
experience_level (1–3; >3 chặn “đang phát triển”),
focus_areas, health_note, fitness_baseline (pushup/squat/plank/pull/row/db…),
challenge_100_days (14 tuần, 3 pha 4+4+6, deload tuần 4/8/14).

## Pipeline bắt buộc (đúng thứ tự)

1. Chuẩn hóa kit.
2. Capacity: chấm test → strength_tier weak/ok/strong + effective_level (có thể hạ so với tự khai).
   Thử thách: nếu yếu/thiếu test thì ước load theo cân/giới/kit.
   Skill gate kéo xà: L1 không dip/muscle-up trần; kéo trần chỉ khi đã test hoặc pha sau; sớm dùng assisted/scapular/ring row.
3. Parse chấn thương. Policy kẹp số buổi, phút, tuần, cardio cuối buổi, cấm split quá dày.
4. Chọn khung tuần master (trình độ × buổi × giới × nhà × có đồ). Full body: xoay vai trò pick theo ngày.
5. Recipe buổi theo phút + split (nhà: khối resistance; warmup; core; cardio tùy policy).
6. Shortlist catalog: venue nhà, đủ đồ user, độ khó, pattern split, chấn thương, cấm specialty không có đồ, cấm sled.
   Cardio thử thách chỉ 6 bài whitelist; lịch thường nhà: Zone 2, không burpee/gối cao/jack (trừ thử thách).
7. Session slots kiểu PPL: ngực nằm rồi dốc lên, không decline. Map bài vào ô. Nhà có tạ/dây + test đủ → bỏ push-up sàn khỏi pool ngực.
8. Gear-first pool: giữ bài dùng đồ user; BW chỉ top-up khi số bài đồ < need
   (need = max(3, số buổi cùng split × số biến thể pha + 1)).
9. Gắn dose_bounds mỗi ứng viên (sets/reps/rest theo trình độ, test, timed vs loaded).
10. OpenAI:
    - Lịch thường: batch 2 ngày; JSON slots; đúng `pick` id; dose trong bounds; tránh avoid_ids; không 2 compound cùng họ/pattern.
    - 100 ngày: 1 call/pha + playbook; avoid id/stem pha trước; tuần A giữ compound, tuần B được đổi isolation nếu pool còn lựa chọn.
    - Thiếu key / JSON thiếu ngày / id ngoài pool → FAIL CỨNG, không fallback im lặng.
11. Validate pick rồi assemble: prescription, section, repair thiếu optional, hạn ngạch cơ, refill buổi mỏng.
12. Finish tuần: drop bài nhà cấm → ngân sách set/tuần theo cơ → refill → top-up phút → kẹp phút →
    đổi bài trùng (max 2 lần/bài, 3 lần/họ; ưu tiên bài đồ) → trộn kit (đừng chỉ dumbbell nếu pool còn dây/xà) →
    đảm bảo pull thật → reorder → warmup = 1 giãn + primer bài main đầu (1–2 set, ~nửa rep working) →
    lịch thường: dose theo test thể lực.
13. Nutrition từ TDEE/macro; thử thách 3 khối + AI chọn món trong pool.
14. Lịch thường khi persist: coach advice + swap chỉ trong allowed ids ngày đó; kẹp phút lại.
15. Lưu plan source=ai, recap wizard, insights (khung, volume, pool mỏng phải dùng BW).

## Ràng buộc chất lượng lịch
- User thấy dụng cụ đã chọn trong tuần, không lịch BW giả.
- Không bịa bài ngoài catalog.
- Buổi khớp phút đã hứa.
- Người mới không vượt volume tuần.
- Ngực nhà: Band/DB press nếu kit band/db; bar/rings mới được push-up/ring push.
- Mix implement; lưng/chân ưu tiên tube khi có dây.
- Tiếng Việt cho lỗi, ghi chú HLV, recap.

## Việc KHÔNG làm
- Không để model thiết kế split, số bài, hay id mới.
- Không silent fallback random.
- Không hỗ trợ gym hay lịch nhà không dụng cụ trên luồng này.
- Không gen familiarization trong cùng pipeline (curriculum khác).

## Kiểm thử gợi ý
- Kit chỉ dây / chỉ tạ / xà+vòng / cả 3: lịch phải chứa đúng họ bài.
- Pool đủ đồ → không còn BW trong slot sức.
- Pool thiếu đồ → BW top-up, insight thin_pools.
- OpenAI trả id lạ hoặc thiếu ngày → lỗi.
- 3 pha thử thách: compound đổi stem giữa pha khi pool cho phép; tuần B ≠ A nếu isolation còn alternative.
- Kẹp phút 45 vs 90.
- Test kéo = 0 + L1 → không pull-up/dip trần.
```

---

## Gợi ý hướng phát triển tiếp (nghiên cứu)

1. **Kit mới** (kettlebell, dây nhảy wizard): mở slug + alias + phủ implement + hint AI; đừng chỉ thêm vào UI.
2. **Gym**: luồng song song; nhiều rule nhà sẽ sai nếu copy.
3. **Trình độ >12 tháng**: đang chặn — cần frame, volume, skill gate mới.
4. **Quan sát thin_pools / unchanged_no_alternative**: nếu hay xuất hiện, catalog thiếu bài đồ cho slot đó — ưu tiên seed bài hơn nới AI.
5. **Giảm call AI**: lịch thường đã batch 2 ngày; thử thách 3 pha đắt — cân nhắc cache pool theo kit.
6. **Dose**: tranh chấp “honor AI” vs “test thể lực” — thử thách tin AI hơn; lịch ngắn tin test hơn. Giữ một nguồn sự thật cho từng mode.
7. **Familiarization**: đừng trộn vào shortlist nhà có đồ; đó là giáo trình ôn pattern.

---

## Bản đồ module (để đọc code, không bắt buộc hiểu hết)

| Việc | Chỗ gần đúng |
|---|---|
| Điều phối | `api/app/services/workout_generation/service.py` |
| Wizard recap | `wizard_inputs.py` |
| Sức tập | `capacity.py`, `load_estimate.py`, `skill_gate.py` |
| Khung tuần | `frame_picker.py`, `split_score.py`, `schedule_spec_master` |
| Policy phút/buổi | `session_policy.py` |
| Shortlist | `shortlist.py` |
| Slot | `session_templates.py` |
| Gear-first | `home_gear_priority.py`, `home_implements.py` |
| Prompt + GPT | `openai_picker.py` |
| Biên dose | `dose_bounds.py` |
| Ráp buổi | `assemble.py` |
| Sau AI | `week_pipeline.py`, `weekly_volume.py`, `session_duration.py` |
| 100 ngày | `phase_templates.py`, `phase_knowledge.py`, `challenge_prompt.py` |
| Bữa | `meal_engine.py`, `nutrition_targets.py` |

Điểm vào: `generate_workout`.
