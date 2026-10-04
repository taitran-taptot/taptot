"""Admin monthly ops stats: plans, orders, users; admin-only GET."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import Role, create_access_token
from app.main import create_app
from app.models.base import Base
from app.models.entities import (
    PaymentTransaction,
    ProductRedeemBatch,
    ProductRedeemCode,
    PushupChallengeSession,
    ShopOrder,
    User,
    UserDailyPlan,
)
from app.services.admin_stats_service import AdminStatsService
from app.services.payment_service import PURPOSE_CHALLENGE_GENERATE


JAN = datetime(2026, 1, 15, 10, 0, 0)
FEB = datetime(2026, 2, 10, 10, 0, 0)
ADMIN_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
HLV_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
USER_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


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


def _bearer(user_id: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def _user(
    db,
    *,
    uid: str,
    email: str,
    role: str,
    created_at: datetime,
) -> User:
    row = User(
        id=uid,
        email=email,
        password_hash="x",
        display_name=email.split("@")[0],
        role=role,
        created_at=created_at,
    )
    db.add(row)
    return row


def _plan(
    db,
    *,
    title: str,
    source: str,
    created_at: datetime,
    user_id: str | None = None,
    is_template: bool = False,
    challenge_100_days: bool = False,
) -> UserDailyPlan:
    row = UserDailyPlan(
        user_id=user_id,
        title_vi=title,
        source=source,
        is_template=is_template,
        challenge_100_days=challenge_100_days,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(row)
    return row


def _seed_ops(db) -> None:
    _user(db, uid=ADMIN_ID, email="admin@test.com", role="admin", created_at=JAN)
    _user(db, uid=HLV_ID, email="hlv@test.com", role="hlv", created_at=JAN)
    _user(db, uid=USER_ID, email="u@test.com", role="user", created_at=FEB)
    _plan(db, title="Guest AI", source="ai", created_at=JAN, user_id=None, challenge_100_days=True)
    _plan(db, title="Admin manual", source="manual", created_at=JAN, user_id=ADMIN_ID)
    _plan(db, title="HLV manual", source="manual", created_at=JAN, user_id=HLV_ID)
    _plan(db, title="HLV AI", source="ai", created_at=FEB, user_id=HLV_ID)
    _plan(db, title="User AI", source="ai", created_at=FEB, user_id=USER_ID)
    _plan(db, title="Template", source="manual", created_at=FEB, user_id=ADMIN_ID, is_template=True)
    db.add(
        ShopOrder(
            user_id=USER_ID,
            order_status="completed",
            total_vnd=200000,
            created_at=JAN,
            payment_method="cod",
            payment_status="cod",
        )
    )
    db.add(
        ShopOrder(
            user_id=USER_ID,
            order_status="cancelled",
            total_vnd=50000,
            created_at=JAN,
            payment_method="cod",
            payment_status="cod",
        )
    )
    db.add(
        ShopOrder(
            user_id=None,
            order_status="awaiting_confirm",
            total_vnd=99000,
            created_at=FEB,
            payment_method="bank_transfer",
            payment_status="awaiting_transfer",
        )
    )
    db.add(
        PaymentTransaction(
            user_id=None,
            amount_vnd=79000,
            currency="VND",
            status="completed",
            payment_provider="stub",
            transaction_metadata={"purpose": PURPOSE_CHALLENGE_GENERATE},
            created_at=JAN,
        )
    )
    db.add(
        PaymentTransaction(
            user_id=USER_ID,
            amount_vnd=10000,
            currency="VND",
            status="pending",
            payment_provider="stub",
            transaction_metadata={"purpose": PURPOSE_CHALLENGE_GENERATE},
            created_at=JAN,
        )
    )
    batch = ProductRedeemBatch(
        product_id=None,
        qty=2,
        note="test",
        created_by=ADMIN_ID,
        created_at=JAN,
    )
    db.add(batch)
    db.flush()
    db.add(
        ProductRedeemCode(
            batch_id=batch.id,
            code="TT-AAAA-AAAA",
            status="redeemed",
            redeemed_at=FEB,
            redeemed_user_id=USER_ID,
        )
    )
    db.add(
        ProductRedeemCode(
            batch_id=batch.id,
            code="TT-BBBB-BBBB",
            status="unused",
        )
    )
    db.add(
        PushupChallengeSession(
            id=str(uuid4()),
            started_at=JAN,
            finished_at=JAN,
            reps=20,
        )
    )
    db.commit()


def test_year_stats_buckets_plans_orders_users():
    db = _session()
    _seed_ops(db)
    out = AdminStatsService(db).year_stats(2026)
    assert out["year"] == 2026
    jan = out["months"][0]
    feb = out["months"][1]
    assert jan["month"] == "2026-01"
    assert jan["plans"]["generated"] == 1
    assert jan["plans"]["admin_created"] == 1
    assert jan["plans"]["hlv_created"] == 1
    assert jan["plans"]["guest"] == 1
    assert jan["plans"]["challenge_100"] == 1
    assert jan["orders"]["count"] == 1
    assert jan["orders"]["gmv_vnd"] == 200000
    assert jan["orders"]["collected_vnd"] == 200000
    assert jan["orders"]["by_status"]["cancelled"] == 1
    assert jan["orders"]["by_status"]["completed"] == 1
    assert jan["challenge"]["paid_count"] == 1
    assert jan["challenge"]["paid_vnd"] == 79000
    assert jan["users"]["staff"] == 2
    assert jan["users"]["new"] == 0
    assert feb["plans"]["generated"] == 2
    assert feb["plans"]["templates"] == 1
    assert feb["plans"]["admin_created"] == 1
    assert feb["plans"]["hlv_created"] == 1
    assert feb["orders"]["count"] == 1
    assert feb["orders"]["gmv_vnd"] == 99000
    assert feb["orders"]["collected_vnd"] == 0
    assert feb["users"]["new"] == 1
    assert feb["redeem"]["used"] == 1
    kpis = out["kpis"]
    assert kpis["plans_generated"] == 3
    assert kpis["plans_admin_created"] == 2
    assert kpis["plans_hlv_created"] == 2
    assert kpis["orders_count"] == 2
    assert kpis["orders_gmv_vnd"] == 299000
    assert kpis["orders_collected_vnd"] == 200000
    assert kpis["users_new"] == 1
    assert kpis["challenge_paid_vnd"] == 79000
    assert kpis["redeem_used"] == 1
    assert kpis["redeem_unused"] == 1
    assert kpis["pushup_completed"] == 1
    hlv_rows = out["hlv_accounts"]
    assert len(hlv_rows) == 1
    assert hlv_rows[0]["email"] == "hlv@test.com"
    assert hlv_rows[0]["total"] == 2
    assert hlv_rows[0]["generated"] == 1
    assert hlv_rows[0]["manual"] == 1
    assert out["open_orders"]["awaiting_confirm"] == 1
    assert out["open_orders"]["awaiting_transfer"] == 1
    assert all(m["month"].startswith("2026-") for m in out["months"])
    assert len(out["months"]) == 12


def test_year_stats_empty_year_is_zeros():
    db = _session()
    _seed_ops(db)
    out = AdminStatsService(db).year_stats(2025)
    assert out["kpis"]["plans_generated"] == 0
    assert out["kpis"]["orders_gmv_vnd"] == 0
    assert out["months"][0]["month"] == "2025-01"


def test_admin_stats_forbidden_for_user_and_hlv():
    client, Session = _app_client()
    db = Session()
    _user(db, uid=ADMIN_ID, email="admin@test.com", role="admin", created_at=datetime.now(UTC))
    _user(db, uid=HLV_ID, email="hlv@test.com", role="hlv", created_at=datetime.now(UTC))
    _user(db, uid=USER_ID, email="u@test.com", role="user", created_at=datetime.now(UTC))
    db.commit()
    db.close()

    user_res = client.get("/api/v1/admin/stats", headers=_bearer(USER_ID, Role.USER.value))
    assert user_res.status_code == 403, user_res.text
    hlv_res = client.get("/api/v1/admin/stats", headers=_bearer(HLV_ID, Role.HLV.value))
    assert hlv_res.status_code == 403, hlv_res.text


def test_admin_stats_ok_for_admin():
    client, Session = _app_client()
    db = Session()
    _seed_ops(db)
    db.close()
    res = client.get("/api/v1/admin/stats?year=2026", headers=_bearer(ADMIN_ID, Role.ADMIN.value))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["year"] == 2026
    assert body["kpis"]["plans_generated"] == 3
    assert body["kpis"]["plans_hlv_created"] == 2
    assert body["months"][0]["plans"]["admin_created"] == 1
    assert body["hlv_accounts"][0]["total"] == 2
