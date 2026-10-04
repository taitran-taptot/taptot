"""Staff-only login (HLV/Admin) and staff plan CRUD."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import Role, create_access_token, hash_password
from app.main import create_app
from app.models.base import Base
from app.models.entities import User


def _app_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    return TestClient(app), Session


def _add_user(Session, *, email: str, role: str, password: str = "Secret12") -> str:
    uid = str(uuid4())
    db = Session()
    db.add(
        User(
            id=uid,
            email=email,
            password_hash=hash_password(password),
            display_name=email.split("@")[0],
            role=role,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()
    return uid


def _bearer(user_id: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def test_user_login_is_forbidden():
    client, Session = _app_client()
    _add_user(Session, email="guest@example.com", role=Role.USER.value)
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "guest@example.com", "password": "Secret12"},
    )
    assert res.status_code == 403, res.text


def test_hlv_login_succeeds():
    client, Session = _app_client()
    _add_user(Session, email="hlv@example.com", role=Role.HLV.value)
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "hlv@example.com", "password": "Secret12"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["role"] == "hlv"


def test_admin_creates_hlv_and_hlv_logs_in():
    client, Session = _app_client()
    admin_id = _add_user(Session, email="admin@example.com", role=Role.ADMIN.value)
    res = client.post(
        "/api/v1/admin/staff",
        json={
            "email": "coach@example.com",
            "password": "Coach123",
            "display_name": "Coach",
            "role": "hlv",
        },
        headers=_bearer(admin_id, Role.ADMIN.value),
    )
    assert res.status_code == 201, res.text
    assert res.json()["role"] == "hlv"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "coach@example.com", "password": "Coach123"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["role"] == "hlv"


def test_hlv_blank_plan_crud_and_public_share():
    client, Session = _app_client()
    hlv_id = _add_user(Session, email="a@example.com", role=Role.HLV.value)
    other_id = _add_user(Session, email="b@example.com", role=Role.HLV.value)
    headers = _bearer(hlv_id, Role.HLV.value)

    created = client.post(
        "/api/v1/my-plans",
        json={
            "title_vi": "Lịch HLV",
            "source": "manual",
            "duration_weeks": 1,
            "day_count": 7,
            "days": [],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["share_token"]
    assert body["day_count"] == 7
    assert len(body["days"]) == 7
    plan_id = body["id"]
    token = body["share_token"]

    public = client.get(f"/api/v1/plans/share/{token}")
    assert public.status_code == 200, public.text
    assert public.json()["title_vi"] == "Lịch HLV"

    updated = client.put(
        f"/api/v1/my-plans/{plan_id}/content",
        json={
            "title_vi": "Lịch custom",
            "sync_days": True,
            "days": [
                {"day_number": 1, "title_vi": "Ngày mở đầu", "exercises": [], "meals": []},
                {"day_number": 2, "title_vi": "Ngày 2", "exercises": [], "meals": []},
            ],
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title_vi"] == "Lịch custom"
    assert updated.json()["day_count"] == 2

    shared = client.get(f"/api/v1/plans/share/{token}")
    assert shared.json()["title_vi"] == "Lịch custom"
    assert shared.json()["day_count"] == 2

    other = client.get(
        f"/api/v1/my-plans/{plan_id}",
        headers=_bearer(other_id, Role.HLV.value),
    )
    assert other.status_code == 403, other.text

    listed = client.get("/api/v1/my-plans", headers=_bearer(other_id, Role.HLV.value))
    assert listed.status_code == 200
    assert listed.json() == []



def test_hlv_client_plan_title_must_be_unique():
    client, Session = _app_client()
    hlv_id = _add_user(Session, email="title-owner@example.com", role=Role.HLV.value)
    other_id = _add_user(Session, email="title-other@example.com", role=Role.HLV.value)
    headers = _bearer(hlv_id, Role.HLV.value)

    first = client.post(
        "/api/v1/my-plans",
        json={"title_vi": "Lịch khách A", "source": "manual", "day_count": 3, "days": []},
        headers=headers,
    )
    assert first.status_code == 201, first.text
    plan_id = first.json()["id"]

    dup = client.post(
        "/api/v1/my-plans",
        json={"title_vi": "lịch khách a", "source": "manual", "day_count": 3, "days": []},
        headers=headers,
    )
    assert dup.status_code == 409, dup.text
    assert "Tên lịch khách" in dup.json()["detail"]

    # Other HLV can reuse the same title.
    other = client.post(
        "/api/v1/my-plans",
        json={"title_vi": "Lịch khách A", "source": "manual", "day_count": 3, "days": []},
        headers=_bearer(other_id, Role.HLV.value),
    )
    assert other.status_code == 201, other.text

    # Templates may share a title with a client plan.
    saved = client.post(
        f"/api/v1/my-plans/{plan_id}/save-as-template",
        json={"title_vi": "Lịch khách A"},
        headers=headers,
    )
    assert saved.status_code == 201, saved.text

    rename_conflict = client.put(
        f"/api/v1/my-plans/{plan_id}/content",
        json={
            "title_vi": "Lịch khách A",
            "sync_days": True,
            "days": [{"day_number": 1, "title_vi": "Ngày 1", "exercises": [], "meals": []}],
        },
        headers=headers,
    )
    assert rename_conflict.status_code == 200, rename_conflict.text

    second = client.post(
        "/api/v1/my-plans",
        json={"title_vi": "Lịch khách B", "source": "manual", "day_count": 3, "days": []},
        headers=headers,
    )
    assert second.status_code == 201, second.text
    second_id = second.json()["id"]

    bad_rename = client.put(
        f"/api/v1/my-plans/{second_id}/content",
        json={
            "title_vi": "Lịch khách A",
            "sync_days": True,
            "days": [{"day_number": 1, "title_vi": "Ngày 1", "exercises": [], "meals": []}],
        },
        headers=headers,
    )
    assert bad_rename.status_code == 409, bad_rename.text


def test_admin_sees_other_staff_plans():
    client, Session = _app_client()
    hlv_id = _add_user(Session, email="hlv2@example.com", role=Role.HLV.value)
    admin_id = _add_user(Session, email="boss@example.com", role=Role.ADMIN.value)

    created = client.post(
        "/api/v1/my-plans",
        json={"title_vi": "Của HLV", "source": "manual", "day_count": 3, "days": []},
        headers=_bearer(hlv_id, Role.HLV.value),
    )
    assert created.status_code == 201, created.text
    plan_id = created.json()["id"]

    admin_list = client.get("/api/v1/my-plans", headers=_bearer(admin_id, Role.ADMIN.value))
    assert admin_list.status_code == 200
    ids = [p["id"] for p in admin_list.json()]
    assert plan_id in ids

    admin_get = client.get(
        f"/api/v1/my-plans/{plan_id}",
        headers=_bearer(admin_id, Role.ADMIN.value),
    )
    assert admin_get.status_code == 200


def test_hlv_plan_template_lifecycle_and_copy_independence():
    client, Session = _app_client()
    hlv_id = _add_user(Session, email="template-owner@example.com", role=Role.HLV.value)
    other_id = _add_user(Session, email="template-other@example.com", role=Role.HLV.value)
    headers = _bearer(hlv_id, Role.HLV.value)
    other_headers = _bearer(other_id, Role.HLV.value)
    now = datetime.now(UTC)

    from app.models.entities import Exercise, Food, MuscleGroup

    db = Session()
    group = MuscleGroup(slug="template-test", name_vi="Template test", sort_order=1)
    db.add(group)
    db.flush()
    exercise = Exercise(
        name_vi="Template squat",
        muscle_group_id=group.id,
        exercise_type="main",
        difficulty=1,
        secondary_muscles=[],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    food = Food(
        slug="template-chicken",
        name_vi="Template chicken",
        serving_size="100g",
        serving_grams=100,
        calories=200,
        protein_g=20,
        carbs_g=0,
        fat_g=10,
        tags=[],
        vitamins_json={},
        food_kind="dish",
        created_at=now,
    )
    db.add_all([exercise, food])
    db.commit()
    exercise_id = exercise.id
    food_id = food.id
    db.close()

    source = client.post(
        "/api/v1/my-plans",
        json={
            "title_vi": "Lịch khách nguồn",
            "source": "manual",
            "client": {"height_cm": 170, "notes": "Dữ liệu khách cũ"},
            "days": [
                {
                    "day_number": 1,
                    "title_vi": "Chân",
                    "meal_notes": {"lunch": "Ăn sau tập"},
                    "section_notes": {"main": "Giữ lưng thẳng"},
                    "meals_flexible": True,
                    "target_calories": 2000,
                    "exercises": [
                        {
                            "exercise_id": exercise_id,
                            "sets": 4,
                            "reps": "8",
                            "rest_seconds": 90,
                            "rir": 2,
                            "rpe": 8,
                            "tempo": "3-1-1-0",
                            "technique": "drop_set",
                        }
                    ],
                    "meals": [
                        {
                            "food_id": food_id,
                            "meal_type": "lunch",
                            "servings": 1.5,
                        }
                    ],
                }
            ],
        },
        headers=headers,
    )
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]

    saved = client.post(
        f"/api/v1/my-plans/{source_id}/save-as-template",
        json={"title_vi": "Mẫu sức mạnh"},
        headers=headers,
    )
    assert saved.status_code == 201, saved.text
    template = saved.json()
    template_id = template["id"]
    assert template["is_template"] is True
    assert template["source"] == "template"
    assert not (template.get("insights") or {}).get("client")
    assert template["days"][0]["meals_flexible"] is True
    assert template["days"][0]["exercises"][0]["tempo"] == "3-1-1-0"
    assert template["days"][0]["meals"][0]["servings"] == 1.5

    listed = client.get("/api/v1/my-plans", headers=headers)
    assert [row["id"] for row in listed.json()] == [source_id]
    assert client.get("/api/v1/my-plans/quota", headers=headers).json()["used"] == 1
    template_list = client.get("/api/v1/my-plans/templates", headers=headers)
    assert [row["id"] for row in template_list.json()] == [template_id]
    assert client.get("/api/v1/my-plans/templates", headers=other_headers).json() == []

    forbidden = client.post(
        f"/api/v1/my-plans/templates/{template_id}/copy",
        json={"title_vi": "Không được phép"},
        headers=other_headers,
    )
    assert forbidden.status_code == 403

    copied = client.post(
        f"/api/v1/my-plans/templates/{template_id}/copy",
        json={
            "title_vi": "Lịch khách mới",
            "share_slug": "khach-moi-template",
            "client": {"height_cm": 180, "weight_kg": 75, "gender": "male"},
        },
        headers=headers,
    )
    assert copied.status_code == 201, copied.text
    clone = copied.json()
    assert clone["source"] == "manual"
    assert clone["is_template"] is False
    assert clone["share_token"] == "khach-moi-template"
    assert clone["insights"]["client"]["height_cm"] == 180
    assert clone["days"][0]["exercises"][0]["rir"] == 2
    assert clone["days"][0]["meals"][0]["servings"] == 1.5
    assert client.get("/api/v1/my-plans/quota", headers=headers).json()["used"] == 2

    changed = client.put(
        f"/api/v1/my-plans/{clone['id']}/content",
        json={
            "sync_days": True,
            "days": [{"day_number": 1, "title_vi": "Đã đổi", "exercises": [], "meals": []}],
        },
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    original_template = client.get(f"/api/v1/my-plans/{template_id}", headers=headers)
    assert len(original_template.json()["days"][0]["exercises"]) == 1
    assert len(original_template.json()["days"][0]["meals"]) == 1

    duplicate_slug = client.post(
        f"/api/v1/my-plans/templates/{template_id}/copy",
        json={"title_vi": "Trùng slug", "share_slug": "khach-moi-template"},
        headers=headers,
    )
    assert duplicate_slug.status_code == 409

    not_template = client.post(
        f"/api/v1/my-plans/templates/{source_id}/copy",
        json={"title_vi": "Sai nguồn"},
        headers=headers,
    )
    assert not_template.status_code == 400


def test_hlv_share_slug_duration_and_content_update():
    client, Session = _app_client()
    hlv_id = _add_user(Session, email="coach-slug@example.com", role=Role.HLV.value)
    headers = _bearer(hlv_id, Role.HLV.value)
    now = datetime.now(UTC)

    db = Session()
    from app.models.entities import (
        Exercise,
        MuscleGroup,
        ProductRedeemBatch,
        ProductRedeemCode,
    )

    mg = MuscleGroup(slug="chest", name_vi="Nguc", sort_order=1)
    db.add(mg)
    db.flush()
    ex = Exercise(
        name_vi="Pushup",
        muscle_group_id=mg.id,
        created_at=now,
        updated_at=now,
    )
    db.add(ex)
    batch = ProductRedeemBatch(qty=1, created_by=hlv_id, created_at=now)
    db.add(batch)
    db.flush()
    db.add(ProductRedeemCode(batch_id=batch.id, code="TT-7K3M-P2QX", status="unused"))
    db.commit()
    exercise_id = ex.id
    db.close()

    created = client.post(
        "/api/v1/my-plans",
        json={
            "title_vi": "Lich 2 tuan",
            "source": "manual",
            "duration_unit": "week",
            "duration_count": 2,
            "share_slug": "hlv-minh",
            "client": {
                "height_cm": 170,
                "weight_kg": 65,
                "gender": "male",
                "notes": "Tap toi",
            },
            "days": [],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["share_token"] == "hlv-minh"
    assert body["day_count"] == 14
    assert len(body["days"]) == 14
    assert body["insights"]["client"]["height_cm"] == 170
    plan_id = body["id"]

    public = client.get("/api/v1/plans/share/hlv-minh")
    assert public.status_code == 200, public.text
    assert public.json()["insights"]["client"]["gender"] == "male"

    dup = client.post(
        "/api/v1/my-plans",
        json={
            "title_vi": "Trung slug",
            "source": "manual",
            "day_count": 3,
            "share_slug": "hlv-minh",
            "days": [],
        },
        headers=headers,
    )
    assert dup.status_code == 409, dup.text
    assert "/lich/hlv-minh" in dup.json()["detail"]

    tem = client.post(
        "/api/v1/my-plans",
        json={
            "title_vi": "Trung tem",
            "source": "manual",
            "day_count": 3,
            "share_slug": "tt-7k3m-p2qx",
            "days": [],
        },
        headers=headers,
    )
    assert tem.status_code == 409, tem.text

    bad = client.post(
        "/api/v1/my-plans",
        json={
            "title_vi": "Slug ngan",
            "source": "manual",
            "day_count": 3,
            "share_slug": "ab",
            "days": [],
        },
        headers=headers,
    )
    assert bad.status_code == 400, bad.text

    over = client.post(
        "/api/v1/my-plans",
        json={
            "title_vi": "Qua dai",
            "source": "manual",
            "duration_unit": "month",
            "duration_count": 4,
            "days": [],
        },
        headers=headers,
    )
    assert over.status_code == 400, over.text

    days_payload = [
        {
            "day_number": i,
            "title_vi": f"Ngay {i}",
            "exercises": (
                [
                    {
                        "exercise_id": exercise_id,
                        "sets": 3,
                        "reps": "10",
                        "section": "main",
                        "rest_seconds": 45,
                    }
                ]
                if i == 1
                else []
            ),
            "meals": [],
        }
        for i in range(1, 15)
    ]
    updated = client.put(
        f"/api/v1/my-plans/{plan_id}/content",
        json={
            "title_vi": "Lich custom",
            "description_vi": "Mo ta ngan",
            "share_slug": "hlv-minh-v2",
            "overview_summary_vi": "Tap 4 buoi / tuan",
            "staff_knowledge": [{"slug": "cach-doc-lich-tap-quy-uoc-buoi-tap", "title_vi": "Cach doc lich"}],
            "client": {
                "height_cm": 171,
                "weight_kg": 66,
                "gender": "female",
                "notes": "Doi ghi chu",
            },
            "sync_days": True,
            "days": days_payload,
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    out = updated.json()
    assert out["share_token"] == "hlv-minh-v2"
    assert out["description_vi"] == "Mo ta ngan"
    assert out["insights"]["overview"]["summary_vi"] == "Tap 4 buoi / tuan"
    assert out["insights"]["staff_knowledge"][0]["slug"] == "cach-doc-lich-tap-quy-uoc-buoi-tap"
    assert out["insights"]["client"]["gender"] == "female"
    assert out["days"][0]["exercises"][0]["rest_seconds"] == 45

    shared = client.get("/api/v1/plans/share/hlv-minh-v2")
    assert shared.status_code == 200, shared.text
    shared_body = shared.json()
    assert shared_body["insights"]["overview"]["summary_vi"] == "Tap 4 buoi / tuan"
    assert shared_body["days"][0]["exercises"][0]["rest_seconds"] == 45

    old = client.get("/api/v1/plans/share/hlv-minh")
    assert old.status_code == 404

