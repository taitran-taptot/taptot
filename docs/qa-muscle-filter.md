# QA — Filter nhóm cơ kho bài tập

Checklist sau khi deploy taxonomy muscle hierarchy.

## Bộ lọc sidebar

- [ ] Dropdown **Ngực** mở ra: Ngực trên / giữa / dưới.
- [ ] Dropdown **Lưng**: Xô (lat) / Lưng giữa / Thắt lưng.
- [ ] Dropdown **Vai**: Vai trước / giữa / sau.
- [ ] Dropdown **Bụng**: Bụng trên / dưới / Nghiêng.
- [ ] **Chân** / **Tay**: vẫn có con như trước (quads, biceps, …).
- [ ] Tick cả nhóm cha → trả về bài của mọi con (API expand `muscle_group_ids`).
- [ ] Tick một con → chỉ bài thuộc vùng đó (vd. incline → `chest-upper`).
- [ ] Badge thẻ bài: `Ngực · Ngực trên` (parent · child).

## API

- [ ] `GET /search/muscle-groups/tree` trả cây cha/con.
- [ ] `GET /search/muscle-groups` có `parent_id`, `is_filter_only`.

## Pytest

```bash
cd api
python -m pytest tests/test_exercise_muscle_region.py tests/test_muscle_group_hierarchy.py -q
```

## Remap catalog (admin)

```bash
python scripts/classify_exercise_muscle_regions.py
python scripts/classify_exercise_muscle_regions.py --apply
```

Xem review: `tmp/exercise_muscle_region_review.csv`
