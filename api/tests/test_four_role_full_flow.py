"""One dataset walks Admin, CTV, guest, and HLV the way the shop and plans actually connect."""

from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import RateLimitMiddleware
from app.core.security import Role, hash_password
from app.main import create_app
from app.models.base import Base
from app.models.entities import Exercise, MuscleGroup, User, UserDailyPlan
from app.services.gen_queue import get_db_for_generate

PRICE = 500_000
PROMO = "CTVQA"
PHONE = "0901234567"
SHIP = {
    "recipient_name": "Nguyen Van A",
    "phone": PHONE,
    "province_code": "01",
    "province_name": "Ha Noi",
    "district_name": "Ba Dinh",
    "ward_code": "00001",
    "ward_name": "Phuc Xa",
    "address_line": "12 Pho Hue",
}


def _client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_for_generate] = override_db
    return TestClient(app), SessionLocal


def _login(client: TestClient, email: str, password: str) -> None:
    client.cookies.clear()
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    assert res.json()["email"] == email


def _step_up(client: TestClient, password: str = "Secret12") -> None:
    res = client.post("/api/v1/auth/confirm-password", json={"password": password})
    assert res.status_code == 200, res.text


def _checkout(client: TestClient, product_id: int, *, promo: str | None, method: str, key: str, phone: str = PHONE):
    body = {
        **SHIP,
        "phone": phone,
        "payment_method": method,
        "items": [{"product_id": product_id, "quantity": 1}],
    }
    if promo:
        body["promo_code"] = promo
    return client.post("/api/v1/shop/orders", json=body, headers={"Idempotency-Key": key})


def _fake_generate(db, user_id, payload, commit=True):
    now = datetime.now(UTC)
    row = UserDailyPlan(
        title_vi="Lich 100 ngay",
        source="ai",
        challenge_100_days=True,
        share_token=f"tmp-{uuid4().hex[:12]}",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    if commit:
        db.commit()
    db.refresh(row)
    return {
        "plan_id": row.id,
        "share_token": row.share_token,
        "plan": {"id": row.id, "title_vi": row.title_vi, "source": "ai"},
    }


def _vn_month() -> str:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m")


def _ctv_completed(client: TestClient) -> dict:
    month = _vn_month()
    stats = client.get(f"/api/v1/collaborator/promo/stats?period=month&on={month}")
    assert stats.status_code == 200, stats.text
    return stats.json()


def test_four_roles_share_one_order_one_plan_and_one_redeem_code(monkeypatch):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    monkeypatch.setattr("app.api.v1.ai.generate_workout", _fake_generate)

    async def _allow(self, request, call_next):
        return await call_next(request)

    monkeypatch.setattr(RateLimitMiddleware, "dispatch", _allow)
    client, SessionLocal = _client()
    now = datetime.now(UTC)
    db = SessionLocal()
    admin = User(
        id=str(uuid4()),
        email="admin.qa@example.com",
        password_hash=hash_password("Secret12"),
        display_name="Admin QA",
        role=Role.ADMIN.value,
        created_at=now,
        email_verified_at=now,
    )
    customer = User(
        id=str(uuid4()),
        email="khach.cu@example.com",
        password_hash=hash_password("Secret12"),
        display_name="Khach cu",
        role=Role.USER.value,
        created_at=now,
    )
    muscle = MuscleGroup(slug="nguc-qa", name_vi="Nguc", sort_order=1)
    db.add_all([admin, customer, muscle])
    db.commit()
    db.refresh(muscle)
    muscle_id = muscle.id
    db.add(
        Exercise(
            name_vi="Chong day cong khai",
            muscle_group_id=muscle_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    db.close()

    closed = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "Secret12", "display_name": "Moi"},
    )
    assert closed.status_code == 403
    rejected = client.post(
        "/api/v1/auth/login",
        json={"email": "khach.cu@example.com", "password": "Secret12"},
    )
    assert rejected.status_code == 403
    assert "HLV" in rejected.json()["detail"]

    _login(client, "admin.qa@example.com", "Secret12")
    blocked = client.post(
        "/api/v1/admin/staff",
        json={
            "email": "hlv.qa@example.com",
            "password": "Coach123",
            "display_name": "HLV QA",
            "role": "hlv",
        },
    )
    assert blocked.status_code == 403
    assert blocked.json().get("code") == "admin_step_up"
    wrong = client.post("/api/v1/auth/confirm-password", json={"password": "SaiMatKhau1"})
    assert wrong.status_code == 401
    _step_up(client)

    not_hlv = client.post(
        "/api/v1/admin/staff",
        json={
            "email": "admin2.qa@example.com",
            "password": "Coach123",
            "display_name": "Khong phai HLV",
            "role": "admin",
        },
    )
    assert not_hlv.status_code == 422
    weak = client.post(
        "/api/v1/admin/staff",
        json={
            "email": "hlv.yeu@example.com",
            "password": "12345678",
            "display_name": "Yeu",
            "role": "hlv",
        },
    )
    assert weak.status_code == 422

    hlv = client.post(
        "/api/v1/admin/staff",
        json={
            "email": "hlv.qa@example.com",
            "password": "Coach123",
            "display_name": "HLV QA",
            "role": "hlv",
        },
    )
    assert hlv.status_code == 201, hlv.text
    assert hlv.json()["role"] == "hlv"
    assert hlv.json()["email_verified"] is True
    other = client.post(
        "/api/v1/admin/staff",
        json={
            "email": "hlv.khac@example.com",
            "password": "Coach123",
            "display_name": "HLV khac",
            "role": "hlv",
        },
    )
    assert other.status_code == 201, other.text

    ctv = client.post(
        "/api/v1/admin/collaborators",
        json={
            "email": "ctv.qa@example.com",
            "password": "Secret12",
            "display_name": "CTV QA",
            "discount_percent": 10,
        },
    )
    assert ctv.status_code == 201, ctv.text
    ctv_id = ctv.json()["id"]
    code = client.post(f"/api/v1/admin/collaborators/{ctv_id}/code", json={"code": PROMO})
    assert code.status_code == 201, code.text
    assert code.json()["code"] == PROMO
    again = client.post(f"/api/v1/admin/collaborators/{ctv_id}/code", json={"code": "CTVQB"})
    assert again.status_code == 409

    product = client.post(
        "/api/v1/admin/shop/products",
        json={
            "name_vi": "Day khang luc QA",
            "price_vnd": PRICE,
            "stock_qty": 10,
            "slug": "day-khang-luc-qa",
            "is_active": True,
        },
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    public_product = client.get("/api/v1/shop/products/slug/day-khang-luc-qa")
    assert public_product.status_code == 200
    assert public_product.json()["price_vnd"] == PRICE

    batch = client.post(
        "/api/v1/shop/redeem-codes/batches",
        json={"qty": 2, "product_id": product_id, "note": "QA"},
    )
    assert batch.status_code == 201, batch.text
    void_code = batch.json()["codes"][0]
    live_code = batch.json()["codes"][1]["code"]
    voided = client.post(f"/api/v1/shop/redeem-codes/{void_code['id']}/void")
    assert voided.status_code == 200, voided.text
    assert voided.json()["status"] == "void"

    year, month = _vn_month().split("-")
    before = client.get(f"/api/v1/admin/stats?year={year}&month={month}")
    assert before.status_code == 200, before.text
    assert before.json()["kpis"]["orders_count"] == 0
    assert before.json()["kpis"]["orders_gmv_vnd"] == 0

    _login(client, "ctv.qa@example.com", "Secret12")
    promo = client.get("/api/v1/collaborator/promo")
    assert promo.status_code == 200, promo.text
    assert promo.json()["code"] == PROMO
    assert promo.json()["discount_percent"] == 10
    assert promo.json()["discount_vnd"] == 0
    assert promo.json()["orders"]["total"] == 0
    assert client.get("/api/v1/admin/shop/orders").status_code == 403
    assert client.get("/api/v1/my-plans").status_code == 403
    assert client.get("/api/v1/admin/stats").status_code == 403

    client.cookies.clear()
    client.cookies.set("taptot_guest", "browser-a-token-0123456789abcdefABCD")
    bad_promo = client.get("/api/v1/shop/promo-codes/SAI")
    assert bad_promo.status_code == 400
    preview = client.get(f"/api/v1/shop/promo-codes/{PROMO}")
    assert preview.status_code == 200
    assert preview.json()["discount_percent"] == 10
    short_phone = _checkout(client, product_id, promo=PROMO, method="cod", key="qa-phone-short-01", phone="09123")
    assert short_phone.status_code == 400
    assert "10 chữ số" in short_phone.json()["detail"]
    missing_name = client.post(
        "/api/v1/shop/orders",
        json={**SHIP, "recipient_name": "A", "payment_method": "cod", "promo_code": PROMO, "items": [{"product_id": product_id, "quantity": 1}]},
        headers={"Idempotency-Key": "qa-name-too-short1"},
    )
    assert missing_name.status_code == 400

    order = _checkout(client, product_id, promo=PROMO, method="cod", key="qa-cod-ctv-000001")
    assert order.status_code == 201, order.text
    placed = order.json()
    assert placed["order_status"] == "awaiting_confirm"
    assert placed["payment_status"] == "cod"
    assert placed["promo_code"] == PROMO
    assert placed["promo_percent"] == 10
    assert placed["promo_discount_vnd"] == 50_000
    assert placed["total_vnd"] == 450_000
    public_code = placed["public_code"]
    replay = _checkout(client, product_id, promo=PROMO, method="cod", key="qa-cod-ctv-000001")
    assert replay.status_code == 201, replay.text
    assert replay.json()["public_code"] == public_code
    assert replay.headers["idempotency-replayed"] == "true"
    assert client.get("/api/v1/shop/products/slug/day-khang-luc-qa").json()["stock_qty"] == 9

    found = client.post("/api/v1/shop/orders/track", json={"phone": PHONE, "public_code": public_code})
    assert found.status_code == 200, found.text
    assert found.json()["order_status"] == "awaiting_confirm"
    missing = client.post("/api/v1/shop/orders/track", json={"phone": "0900000000", "public_code": public_code})
    assert missing.status_code == 404

    lead = client.post(
        "/api/v1/contact/trainer",
        json={"full_name": "Nguyen Van A", "phone_zalo": PHONE, "goal": "lose_fat", "message": "Can giam mo"},
    )
    assert lead.status_code == 201, lead.text
    bad_goal = client.post(
        "/api/v1/contact/trainer",
        json={"full_name": "Nguyen Van A", "phone_zalo": PHONE, "goal": "bulk_fast"},
    )
    assert bad_goal.status_code == 400
    feedback = client.post(
        "/api/v1/feedback",
        json={"category": "workout_plan", "content": "Lich nay chua hop", "plan_url": None},
    )
    assert feedback.status_code == 400

    guest_plan = client.post(
        "/api/v1/plans",
        json={"title_vi": "Lich tu tao", "source": "manual", "duration_weeks": 4, "day_count": 7, "days": []},
    )
    assert guest_plan.status_code == 201, guest_plan.text
    assert guest_plan.json()["share_token"]
    challenge = client.post(
        "/api/v1/plans",
        json={"title_vi": "Thu thach", "source": "manual", "challenge_100_days": True, "day_count": 7, "days": []},
    )
    assert challenge.status_code == 401

    _login(client, "ctv.qa@example.com", "Secret12")
    waiting = _ctv_completed(client)
    assert waiting["total_vnd"] == 0
    assert waiting["discount_vnd"] == 0
    dash = client.get("/api/v1/collaborator/promo")
    assert dash.json()["discount_vnd"] == 0
    assert PHONE not in dash.text
    assert "Phuc Xa" not in dash.text
    assert "12 Pho Hue" not in dash.text

    _login(client, "admin.qa@example.com", "Secret12")
    _step_up(client)
    listed = client.get("/api/v1/admin/shop/orders")
    assert listed.status_code == 200, listed.text
    admin_order = next(row for row in listed.json()["items"] if row["public_code"] == public_code)
    assert admin_order["phone"] == PHONE
    assert admin_order["address_line"] == "12 Pho Hue"
    assert admin_order["promo_code"] == PROMO
    assert admin_order["promo_discount_vnd"] == 50_000
    order_id = admin_order["id"]

    for status in ("packing", "shipping"):
        moved = client.patch(f"/api/v1/admin/shop/orders/{order_id}", json={"order_status": status})
        assert moved.status_code == 200, moved.text
        assert moved.json()["order_status"] == status
        client.cookies.clear()
        tracked = client.post("/api/v1/shop/orders/track", json={"phone": PHONE, "public_code": public_code})
        assert tracked.json()["order_status"] == status
        _login(client, "ctv.qa@example.com", "Secret12")
        still_open = _ctv_completed(client)
        assert still_open["total_vnd"] == 0
        assert still_open["discount_vnd"] == 0
        _login(client, "admin.qa@example.com", "Secret12")
        _step_up(client)

    done = client.patch(f"/api/v1/admin/shop/orders/{order_id}", json={"order_status": "completed"})
    assert done.status_code == 200, done.text
    assert done.json()["order_status"] == "completed"
    client.cookies.clear()
    finished = client.post("/api/v1/shop/orders/track", json={"phone": PHONE, "public_code": public_code})
    assert finished.json()["order_status"] == "completed"

    _login(client, "admin.qa@example.com", "Secret12")
    _step_up(client)
    stats = client.get(f"/api/v1/admin/stats?year={year}&month={month}")
    assert stats.json()["kpis"]["orders_count"] == 1
    assert stats.json()["kpis"]["orders_gmv_vnd"] == 450_000
    leads = client.get("/api/v1/admin/trainer-contacts")
    assert leads.status_code == 200, leads.text
    row = leads.json()["items"][0]
    assert row["status"] == "new"
    assert row["full_name"] == "Nguyen Van A"
    noted = client.patch(
        f"/api/v1/admin/trainer-contacts/{row['id']}",
        json={"status": "contacted", "admin_note": "Da goi"},
    )
    assert noted.status_code == 200, noted.text
    won = client.patch(f"/api/v1/admin/trainer-contacts/{row['id']}", json={"status": "won"})
    assert won.status_code == 200, won.text
    assert won.json()["status"] == "won"
    assert won.json()["admin_note"] == "Da goi"

    _login(client, "hlv.qa@example.com", "Coach123")
    assert client.get("/api/v1/admin/trainer-contacts").status_code == 403
    assert client.get("/api/v1/admin/stats").status_code == 403
    assert client.patch(f"/api/v1/admin/shop/orders/{order_id}", json={"order_status": "cancelled"}).status_code == 403
    assert client.post(f"/api/v1/admin/collaborators/{ctv_id}/code", json={"code": "CTVQC"}).status_code == 403

    _login(client, "ctv.qa@example.com", "Secret12")
    completed_stats = _ctv_completed(client)
    assert completed_stats["order_count"] == 1
    assert completed_stats["total_vnd"] == 450_000
    assert completed_stats["discount_vnd"] == 50_000
    filtered = client.get(
        f"/api/v1/collaborator/promo/stats?period=month&on={_vn_month()}&q={public_code}&status=completed"
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["orders"]["total"] == 1
    assert filtered.json()["orders"]["items"][0]["public_code"] == public_code
    own = client.get("/api/v1/collaborator/promo")
    assert own.json()["discount_vnd"] == 50_000
    assert "phone" not in own.json()["orders"]["items"][0]

    _login(client, "admin.qa@example.com", "Secret12")
    admin_view = client.get(f"/api/v1/admin/collaborators/{ctv_id}/orders")
    assert admin_view.status_code == 200, admin_view.text
    full = next(item for item in admin_view.json()["items"] if item["public_code"] == public_code)
    assert full["phone"] == PHONE
    assert full["address_line"] == "12 Pho Hue"

    client.cookies.clear()
    cancelled = _checkout(client, product_id, promo=PROMO, method="cod", key="qa-cod-cancel-0001", phone="0901234568")
    assert cancelled.status_code == 201, cancelled.text
    cancel_id = cancelled.json()["id"]
    cancel_code = cancelled.json()["public_code"]
    _login(client, "admin.qa@example.com", "Secret12")
    _step_up(client)
    dropped = client.patch(f"/api/v1/admin/shop/orders/{cancel_id}", json={"order_status": "cancelled"})
    assert dropped.status_code == 200, dropped.text
    assert dropped.json()["order_status"] == "cancelled"
    kept = client.patch(f"/api/v1/admin/shop/orders/{cancel_id}", json={"order_status": "completed"})
    assert kept.status_code == 400
    after_cancel = client.get(f"/api/v1/admin/stats?year={year}&month={month}")
    assert after_cancel.json()["kpis"]["orders_count"] == 1
    assert after_cancel.json()["kpis"]["orders_gmv_vnd"] == 450_000

    _login(client, "ctv.qa@example.com", "Secret12")
    after = _ctv_completed(client)
    assert after["order_count"] == 1
    assert after["discount_vnd"] == 50_000
    assert after["total_vnd"] == 450_000
    hidden = client.get(f"/api/v1/collaborator/promo/stats?period=month&on={_vn_month()}&q={cancel_code}&status=cancelled")
    assert hidden.json()["orders"]["total"] == 1
    assert hidden.json()["discount_vnd"] == 50_000

    client.cookies.clear()
    bank = _checkout(client, product_id, promo=None, method="bank_transfer", key="qa-bank-transfer-01", phone="0901234569")
    assert bank.status_code == 201, bank.text
    assert bank.json()["payment_method"] == "bank_transfer"
    assert bank.json()["payment_status"] == "awaiting_transfer"
    assert bank.json()["bank_transfer"]["amount_vnd"] == PRICE
    assert bank.json()["bank_transfer"]["transfer_content"]

    _login(client, "hlv.qa@example.com", "Coach123")
    created = client.post(
        "/api/v1/my-plans",
        json={
            "title_vi": "Lich cho Nguyen Van A",
            "source": "manual",
            "duration_weeks": 4,
            "day_count": 7,
            "days": [],
            "client": {"height_cm": 170, "weight_kg": 65, "gender": "male", "notes": "Giam mo"},
        },
    )
    assert created.status_code == 201, created.text
    plan_id = created.json()["id"]
    token = created.json()["share_token"]
    assert created.json()["insights"]["client"]["height_cm"] == 170
    client.cookies.clear()
    shared = client.get(f"/api/v1/plans/share/{token}")
    assert shared.status_code == 200, shared.text
    assert shared.json()["title_vi"] == "Lich cho Nguyen Van A"
    assert shared.json()["insights"]["client"]["notes"] == "Giam mo"
    exported = client.post(f"/api/v1/plans/share/{token}/export", json={"format": "pdf"})
    assert exported.status_code == 200, exported.text
    assert "pdf" in exported.headers["content-type"]
    assert client.put(f"/api/v1/my-plans/{plan_id}/content", json={"title_vi": "Sua trom", "days": []}).status_code == 401

    _login(client, "hlv.khac@example.com", "Coach123")
    assert client.get(f"/api/v1/my-plans/{plan_id}").status_code == 403
    other_list = client.get("/api/v1/my-plans")
    assert all(item["id"] != plan_id for item in other_list.json())

    _login(client, "admin.qa@example.com", "Secret12")
    admin_plans = client.get("/api/v1/my-plans")
    assert any(item["id"] == plan_id for item in admin_plans.json())
    assert client.get(f"/api/v1/my-plans/{plan_id}").status_code == 200

    _login(client, "hlv.qa@example.com", "Coach123")
    private = client.post(
        "/api/v1/my-exercises",
        json={"name_vi": "Bai rieng QA", "muscle_group_id": muscle_id, "exercise_type": "main"},
    )
    assert private.status_code == 201, private.text
    client.cookies.clear()
    library = client.get("/api/v1/search/exercises")
    names = [item["name_vi"] for item in library.json()["items"]]
    assert "Bai rieng QA" not in names
    assert "Chong day cong khai" in names

    client.cookies.clear()
    assert client.get(f"/api/v1/shop/redeem-codes/lookup?code={void_code['code']}").json()["valid"] is False
    assert client.get("/api/v1/shop/redeem-codes/lookup?code=TT00000000").json()["valid"] is False
    ready = client.get(f"/api/v1/shop/redeem-codes/lookup?code={live_code}")
    assert ready.json()["valid"] is True
    assert ready.json()["status"] == "unused"
    generated = client.post(
        "/api/v1/ai/generate-workout-schedule",
        json={
            "age": 25,
            "height_cm": 170,
            "weight_kg": 65,
            "gender": "male",
            "goal": "lose_fat",
            "equipment_list": ["resistance-band"],
            "duration_weeks": 14,
            "challenge_100_days": True,
            "location": "home",
            "redeem_code": live_code,
        },
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["code_applied"] is True
    assert generated.json()["view_path"] == f"/lich/{live_code}"
    burned = client.get(f"/api/v1/shop/redeem-codes/lookup?code={live_code}")
    assert burned.json()["valid"] is False
    assert burned.json()["status"] == "redeemed"
    reused = client.post(
        "/api/v1/ai/generate-workout-schedule",
        json={
            "age": 25,
            "height_cm": 170,
            "weight_kg": 65,
            "equipment_list": ["resistance-band"],
            "duration_weeks": 14,
            "challenge_100_days": True,
            "redeem_code": live_code,
        },
    )
    assert reused.status_code == 403

    _login(client, "hlv.qa@example.com", "Coach123")
    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Coach123", "new_password": "Newpass12"},
    )
    assert changed.status_code == 200, changed.text
    stale = client.get("/api/v1/my-plans")
    assert stale.status_code == 401
    client.cookies.clear()
    old = client.post("/api/v1/auth/login", json={"email": "hlv.qa@example.com", "password": "Coach123"})
    assert old.status_code == 401
    _login(client, "hlv.qa@example.com", "Newpass12")
    assert client.get("/api/v1/my-plans").status_code == 200
