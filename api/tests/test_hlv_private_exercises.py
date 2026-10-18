"""HLV private exercises stay out of the public library."""

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
from app.models.entities import Exercise, MuscleGroup, User


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


def _add_user(Session, *, email: str, role: str) -> str:
    uid = str(uuid4())
    db = Session()
    db.add(
        User(
            id=uid,
            email=email,
            password_hash=hash_password("Secret12"),
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


def test_private_exercise_hidden_from_library_and_admin_catalog():
    client, Session = _app_client()
    a = _add_user(Session, email="a@example.com", role=Role.HLV.value)
    b = _add_user(Session, email="b@example.com", role=Role.HLV.value)
    admin_id = _add_user(Session, email="admin@example.com", role=Role.ADMIN.value)
    mg_id = _seed_muscle(Session)
    now = datetime.now(UTC)
    db = Session()
    db.add(
        Exercise(
            name_vi="Public push",
            muscle_group_id=mg_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    db.close()

    created = client.post(
        "/api/v1/my-exercises",
        json={"name_vi": "Bài riêng A", "muscle_group_id": mg_id, "exercise_type": "main"},
        headers=_bearer(a, Role.HLV.value),
    )
    assert created.status_code == 201, created.text
    priv_id = created.json()["id"]
    assert created.json()["owner_user_id"] == a
    assert created.json()["is_private"] is True

    public = client.get("/api/v1/search/exercises")
    names = [i["name_vi"] for i in public.json()["items"]]
    assert "Bài riêng A" not in names
    assert "Public push" in names

    with_mine = client.get(
        "/api/v1/search/exercises?include_mine=true",
        headers=_bearer(a, Role.HLV.value),
    )
    mine_names = [i["name_vi"] for i in with_mine.json()["items"]]
    assert "Bài riêng A" in mine_names
    assert "Public push" in mine_names

    only_mine = client.get(
        "/api/v1/search/exercises?mine_only=true",
        headers=_bearer(a, Role.HLV.value),
    )
    only_names = [i["name_vi"] for i in only_mine.json()["items"]]
    assert "Bài riêng A" in only_names
    assert "Public push" not in only_names

    listed = client.get("/api/v1/my-exercises?page=1&page_size=12", headers=_bearer(a, Role.HLV.value))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["name_vi"] == "Bài riêng A"

    other_mine = client.get(
        "/api/v1/search/exercises?include_mine=true",
        headers=_bearer(b, Role.HLV.value),
    )
    assert "Bài riêng A" not in [i["name_vi"] for i in other_mine.json()["items"]]

    admin_cat = client.get("/api/v1/admin/exercises", headers=_bearer(admin_id, Role.ADMIN.value))
    assert "Bài riêng A" not in [i["name_vi"] for i in admin_cat.json()["items"]]

    detail = client.get(f"/api/v1/search/exercises/{priv_id}")
    assert detail.status_code == 404

    own_detail = client.get(
        f"/api/v1/search/exercises/{priv_id}",
        headers=_bearer(a, Role.HLV.value),
    )
    assert own_detail.status_code == 200


def test_only_owner_can_attach_private_exercise():
    client, Session = _app_client()
    a = _add_user(Session, email="a@example.com", role=Role.HLV.value)
    b = _add_user(Session, email="b@example.com", role=Role.HLV.value)
    mg_id = _seed_muscle(Session)

    priv = client.post(
        "/api/v1/my-exercises",
        json={"name_vi": "Row riêng", "muscle_group_id": mg_id},
        headers=_bearer(a, Role.HLV.value),
    )
    ex_id = priv.json()["id"]

    plan_a = client.post(
        "/api/v1/my-plans",
        json={"title_vi": "Lịch A", "source": "manual", "duration_weeks": 1, "day_count": 1, "days": []},
        headers=_bearer(a, Role.HLV.value),
    )
    assert plan_a.status_code == 201, plan_a.text
    id_a = plan_a.json()["id"]

    ok = client.put(
        f"/api/v1/my-plans/{id_a}/content",
        json={
            "sync_days": True,
            "days": [
                {
                    "day_number": 1,
                    "title_vi": "Ngày 1",
                    "exercises": [{"exercise_id": ex_id, "section": "main", "sets": 3, "reps": "8"}],
                    "meals": [],
                }
            ],
        },
        headers=_bearer(a, Role.HLV.value),
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["days"][0]["exercises"][0]["name_vi"] == "Row riêng"
    token = ok.json()["share_token"]
    shared = client.get(f"/api/v1/plans/share/{token}")
    assert shared.status_code == 200
    assert shared.json()["days"][0]["exercises"][0]["name_vi"] == "Row riêng"

    plan_b = client.post(
        "/api/v1/my-plans",
        json={"title_vi": "Lịch B", "source": "manual", "duration_weeks": 1, "day_count": 1, "days": []},
        headers=_bearer(b, Role.HLV.value),
    )
    id_b = plan_b.json()["id"]
    denied = client.put(
        f"/api/v1/my-plans/{id_b}/content",
        json={
            "sync_days": True,
            "days": [
                {
                    "day_number": 1,
                    "title_vi": "Ngày 1",
                    "exercises": [{"exercise_id": ex_id, "section": "main", "sets": 3, "reps": "8"}],
                    "meals": [],
                }
            ],
        },
        headers=_bearer(b, Role.HLV.value),
    )
    assert denied.status_code == 400

    listed = client.get("/api/v1/my-exercises", headers=_bearer(b, Role.HLV.value))
    assert listed.json()["items"] == []
