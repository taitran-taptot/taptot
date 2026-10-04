"""HLV catalog: create, update all, hide only own, list mine."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.exceptions import ForbiddenError
from app.core.security import Role, create_access_token, hash_password
from app.main import create_app
from app.models.base import Base
from app.models.entities import Exercise, MuscleGroup, User
from app.services.admin_food_service import AdminFoodService


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


def _seed_muscle(Session) -> int:
    db = Session()
    mg = MuscleGroup(slug="chest", name_vi="Ngực", sort_order=1)
    db.add(mg)
    db.commit()
    mg_id = mg.id
    db.close()
    return mg_id


FOOD_BODY = {
    "name_vi": "Cơm HLV",
    "kcal_100g": 130,
    "protein_100g": 2.7,
    "carbs_100g": 28,
    "fat_100g": 0.3,
}

EX_BODY = {
    "name_vi": "Đẩy ngực HLV",
    "muscle_group_id": 1,
    "exercise_type": "main",
    "movement_role": "compound",
    "movement_pattern": "h_push",
    "venue": "gym",
    "difficulty": 2,
    "is_active": True,
}


def test_hlv_creates_food_and_exercise():
    client, Session = _app_client()
    hlv_id = _add_user(Session, email="hlv@example.com", role=Role.HLV.value)
    mg_id = _seed_muscle(Session)
    headers = _bearer(hlv_id, Role.HLV.value)

    food = client.post("/api/v1/admin/foods", json=FOOD_BODY, headers=headers)
    assert food.status_code == 201, food.text
    assert food.json()["created_by"] == hlv_id

    ex = client.post(
        "/api/v1/admin/exercises",
        json={**EX_BODY, "muscle_group_id": mg_id},
        headers=headers,
    )
    assert ex.status_code == 201, ex.text
    assert ex.json()["created_by"] == hlv_id
    assert ex.json()["name_vi"] == "Đẩy ngực HLV"


def test_hlv_updates_others_but_cannot_hide():
    client, Session = _app_client()
    owner = _add_user(Session, email="owner@example.com", role=Role.HLV.value)
    other = _add_user(Session, email="other@example.com", role=Role.HLV.value)
    mg_id = _seed_muscle(Session)

    created_food = client.post(
        "/api/v1/admin/foods",
        json=FOOD_BODY,
        headers=_bearer(owner, Role.HLV.value),
    )
    food_id = created_food.json()["id"]
    created_ex = client.post(
        "/api/v1/admin/exercises",
        json={**EX_BODY, "muscle_group_id": mg_id, "name_vi": "Seed bench"},
        headers=_bearer(owner, Role.HLV.value),
    )
    ex_id = created_ex.json()["id"]

    other_h = _bearer(other, Role.HLV.value)
    renamed = client.patch(
        f"/api/v1/admin/foods/{food_id}",
        json={"name_vi": "Cơm sửa"},
        headers=other_h,
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name_vi"] == "Cơm sửa"

    hide_food = client.patch(
        f"/api/v1/admin/foods/{food_id}",
        json={"status": "deprecated"},
        headers=other_h,
    )
    assert hide_food.status_code == 403, hide_food.text

    hide_ex = client.patch(
        f"/api/v1/admin/exercises/{ex_id}",
        json={"is_active": False},
        headers=other_h,
    )
    assert hide_ex.status_code == 403, hide_ex.text


def test_hlv_hides_own_other_hlv_cannot():
    client, Session = _app_client()
    owner = _add_user(Session, email="a@example.com", role=Role.HLV.value)
    other = _add_user(Session, email="b@example.com", role=Role.HLV.value)
    mg_id = _seed_muscle(Session)
    owner_h = _bearer(owner, Role.HLV.value)

    food = client.post("/api/v1/admin/foods", json=FOOD_BODY, headers=owner_h)
    food_id = food.json()["id"]
    ex = client.post(
        "/api/v1/admin/exercises",
        json={**EX_BODY, "muscle_group_id": mg_id},
        headers=owner_h,
    )
    ex_id = ex.json()["id"]

    hid_food = client.patch(
        f"/api/v1/admin/foods/{food_id}",
        json={"status": "deprecated"},
        headers=owner_h,
    )
    assert hid_food.status_code == 200, hid_food.text
    assert hid_food.json()["status"] == "deprecated"

    hid_ex = client.patch(
        f"/api/v1/admin/exercises/{ex_id}",
        json={"is_active": False},
        headers=owner_h,
    )
    assert hid_ex.status_code == 200, hid_ex.text
    assert hid_ex.json()["is_active"] is False

    restore = client.patch(
        f"/api/v1/admin/foods/{food_id}",
        json={"status": "active"},
        headers=_bearer(other, Role.HLV.value),
    )
    assert restore.status_code == 403


def test_hlv_cannot_hide_seed_exercise():
    client, Session = _app_client()
    hlv_id = _add_user(Session, email="hlv@example.com", role=Role.HLV.value)
    mg_id = _seed_muscle(Session)
    now = datetime.now(UTC)
    db = Session()
    row = Exercise(
        name_vi="Seed push",
        muscle_group_id=mg_id,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    ex_id = row.id
    db.close()

    res = client.patch(
        f"/api/v1/admin/exercises/{ex_id}",
        json={"is_active": False},
        headers=_bearer(hlv_id, Role.HLV.value),
    )
    assert res.status_code == 403, res.text

    ok = client.patch(
        f"/api/v1/admin/exercises/{ex_id}",
        json={"name_vi": "Seed push sửa"},
        headers=_bearer(hlv_id, Role.HLV.value),
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["name_vi"] == "Seed push sửa"
    assert ok.json()["is_active"] is True


def test_mine_list_only_own():
    client, Session = _app_client()
    a = _add_user(Session, email="a@example.com", role=Role.HLV.value)
    b = _add_user(Session, email="b@example.com", role=Role.HLV.value)
    mg_id = _seed_muscle(Session)

    client.post("/api/v1/admin/foods", json=FOOD_BODY, headers=_bearer(a, Role.HLV.value))
    client.post(
        "/api/v1/admin/foods",
        json={**FOOD_BODY, "name_vi": "Cơm B"},
        headers=_bearer(b, Role.HLV.value),
    )
    client.post(
        "/api/v1/admin/exercises",
        json={**EX_BODY, "muscle_group_id": mg_id, "name_vi": "Bài A"},
        headers=_bearer(a, Role.HLV.value),
    )
    client.post(
        "/api/v1/admin/exercises",
        json={**EX_BODY, "muscle_group_id": mg_id, "name_vi": "Bài B"},
        headers=_bearer(b, Role.HLV.value),
    )

    foods = client.get("/api/v1/admin/foods?mine=true", headers=_bearer(a, Role.HLV.value))
    assert foods.status_code == 200, foods.text
    names = [i["name_vi"] for i in foods.json()["items"]]
    assert names == ["Cơm HLV"]

    exs = client.get("/api/v1/admin/exercises?mine=true", headers=_bearer(a, Role.HLV.value))
    assert exs.status_code == 200, exs.text
    ex_names = [i["name_vi"] for i in exs.json()["items"]]
    assert ex_names == ["Bài A"]


def test_admin_hides_hlv_item_hlv_forbidden_on_stats():
    client, Session = _app_client()
    hlv_id = _add_user(Session, email="hlv@example.com", role=Role.HLV.value)
    admin_id = _add_user(Session, email="admin@example.com", role=Role.ADMIN.value)
    mg_id = _seed_muscle(Session)

    food = client.post(
        "/api/v1/admin/foods", json=FOOD_BODY, headers=_bearer(hlv_id, Role.HLV.value)
    )
    food_id = food.json()["id"]
    ex = client.post(
        "/api/v1/admin/exercises",
        json={**EX_BODY, "muscle_group_id": mg_id},
        headers=_bearer(hlv_id, Role.HLV.value),
    )
    ex_id = ex.json()["id"]

    hid_food = client.patch(
        f"/api/v1/admin/foods/{food_id}",
        json={"status": "deprecated"},
        headers=_bearer(admin_id, Role.ADMIN.value),
    )
    assert hid_food.status_code == 200, hid_food.text

    hid_ex = client.patch(
        f"/api/v1/admin/exercises/{ex_id}",
        json={"is_active": False},
        headers=_bearer(admin_id, Role.ADMIN.value),
    )
    assert hid_ex.status_code == 200, hid_ex.text

    stats = client.get("/api/v1/admin/stats", headers=_bearer(hlv_id, Role.HLV.value))
    assert stats.status_code == 403


def test_food_service_hlv_cannot_deprecate_others():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    owner_id = str(uuid4())
    other_id = str(uuid4())
    created = AdminFoodService(db).create(**FOOD_BODY, created_by=owner_id)
    actor = CurrentUser(id=other_id, role=Role.HLV, email="o@x.com")
    try:
        AdminFoodService(db).update(created["id"], {"status": "deprecated"}, actor=actor)
        raise AssertionError("expected ForbiddenError")
    except ForbiddenError:
        pass
    owner = CurrentUser(id=owner_id, role=Role.HLV, email="a@x.com")
    updated = AdminFoodService(db).update(created["id"], {"status": "deprecated"}, actor=owner)
    assert updated["status"] == "deprecated"
