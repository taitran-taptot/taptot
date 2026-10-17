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
    ShopOrderItem,
    ShopProduct,
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
    assert "shop" in body
    assert body["shop"]["grain"] == "month"


def _kit(db, *, slug: str, name: str, stock: int = 10) -> ShopProduct:
    row = ShopProduct(
        slug=slug,
        name_vi=name,
        price_vnd=500000,
        stock_qty=stock,
        is_active=True,
        created_at=JAN,
        updated_at=JAN,
    )
    db.add(row)
    db.flush()
    return row


def test_shop_stats_products_discount_and_day_grain():
    db = _session()
    _user(db, uid=USER_ID, email="u@test.com", role="user", created_at=JAN)
    band = _kit(db, slug="resistance-band", name="Dây kháng lực", stock=8)
    dumb = _kit(db, slug="dumbbell", name="Tạ đơn", stock=4)
    _kit(db, slug="bar-and-rings", name="Xà đơn", stock=12)

    o1 = ShopOrder(
        user_id=USER_ID,
        phone="0901111111",
        order_status="completed",
        total_vnd=450000,
        discount_percent=10,
        discount_vnd=50000,
        shipping_fee_vnd=0,
        created_at=JAN,
        payment_method="cod",
        payment_status="cod",
    )
    db.add(o1)
    db.flush()
    db.add(
        ShopOrderItem(
            order_id=o1.id,
            product_id=band.id,
            name_vi=band.name_vi,
            unit_price_vnd=500000,
            quantity=1,
        )
    )

    jan20 = datetime(2026, 1, 20, 10, 0, 0)
    o2 = ShopOrder(
        user_id=USER_ID,
        phone="0901111111",
        order_status="cancelled",
        total_vnd=1000000,
        discount_percent=0,
        discount_vnd=0,
        created_at=jan20,
        payment_method="cod",
        payment_status="cod",
    )
    db.add(o2)
    db.flush()
    db.add(
        ShopOrderItem(
            order_id=o2.id,
            product_id=dumb.id,
            name_vi=dumb.name_vi,
            unit_price_vnd=500000,
            quantity=2,
        )
    )

    o3 = ShopOrder(
        user_id=USER_ID,
        phone="0901111111",
        order_status="packing",
        total_vnd=1000000,
        discount_percent=0,
        discount_vnd=0,
        created_at=FEB,
        payment_method="bank_transfer",
        payment_status="paid",
    )
    db.add(o3)
    db.flush()
    db.add(
        ShopOrderItem(
            order_id=o3.id,
            product_id=band.id,
            name_vi=band.name_vi,
            unit_price_vnd=500000,
            quantity=1,
        )
    )
    db.add(
        ShopOrderItem(
            order_id=o3.id,
            product_id=dumb.id,
            name_vi=dumb.name_vi,
            unit_price_vnd=500000,
            quantity=1,
        )
    )
    db.add(
        PushupChallengeSession(
            id=str(uuid4()),
            started_at=JAN,
            finished_at=JAN,
            reps=25,
        )
    )
    db.commit()

    year = AdminStatsService(db).year_stats(2026)
    shop = year["shop"]
    assert shop["grain"] == "month"
    kpis = shop["kpis"]
    assert kpis["orders"] == 2
    assert kpis["cancelled"] == 1
    assert kpis["units"] == 3
    assert kpis["gross_vnd"] == 1500000
    assert kpis["discount_vnd"] == 50000
    assert kpis["net_vnd"] == 1450000
    assert kpis["collected_vnd"] == 1450000
    assert kpis["discount_orders"] == 1
    assert kpis["repeat_customers"] == 1
    by_slug = {p["slug"]: p for p in shop["products"]}
    assert by_slug["resistance-band"]["units"] == 2
    assert by_slug["resistance-band"]["line_vnd"] == 1000000
    assert by_slug["resistance-band"]["order_count"] == 2
    assert by_slug["dumbbell"]["units"] == 1
    assert by_slug["bar-and-rings"]["units"] == 0
    assert by_slug["bar-and-rings"]["stock_qty"] == 12
    assert shop["pushup"]["sessions_completed"] == 1
    assert shop["pushup"]["by_percent"]["10"] == 1
    jan = next(row for row in shop["series"] if row["period"] == "2026-01")
    assert jan["orders"] == 1
    assert jan["cancelled"] == 1
    assert jan["discount_vnd"] == 50000
    assert jan["units_by_slug"]["resistance-band"] == 1

    january = AdminStatsService(db).shop_stats(2026, 1)
    assert january["grain"] == "day"
    assert len(january["series"]) == 31
    day15 = next(row for row in january["series"] if row["period"] == "2026-01-15")
    day20 = next(row for row in january["series"] if row["period"] == "2026-01-20")
    assert day15["orders"] == 1
    assert day15["gross_vnd"] == 500000
    assert day15["discount_vnd"] == 50000
    assert day20["orders"] == 0
    assert day20["cancelled"] == 1
    assert january["kpis"]["orders"] == 1
    assert january["kpis"]["net_vnd"] == 450000


def test_shop_stats_lists_active_catalog_not_hardcoded_kits():
    db = _session()
    _user(db, uid=USER_ID, email="u@test.com", role="user", created_at=JAN)
    _kit(db, slug="day-khang-luc-ngu-sac", name="Dây kháng lực ngũ sắc", stock=20)
    dead = _kit(db, slug="dumbbell", name="Tạ đơn", stock=4)
    dead.is_active = False
    db.commit()

    shop = AdminStatsService(db).shop_stats(2026)
    slugs = [p["slug"] for p in shop["products"]]
    assert slugs == ["day-khang-luc-ngu-sac"]
    assert "resistance-band" not in slugs
    assert "bar-and-rings" not in slugs
    jan = next(row for row in shop["series"] if row["period"] == "2026-01")
    assert set(jan["units_by_slug"]) == {"day-khang-luc-ngu-sac"}


def test_shop_stats_omits_orphaned_order_lines():
    db = _session()
    _user(db, uid=USER_ID, email="u@test.com", role="user", created_at=JAN)
    band = _kit(db, slug="resistance-band", name="Dây kháng lực ngũ sắc", stock=8)
    _kit(db, slug="dumbbell", name="Tạ đơn", stock=4)
    _kit(db, slug="bar-and-rings", name="Xà đơn treo tường và Vòng treo", stock=12)
    order = ShopOrder(
        user_id=USER_ID,
        phone="0901111111",
        order_status="completed",
        total_vnd=400000,
        created_at=JAN,
        payment_method="cod",
        payment_status="cod",
    )
    db.add(order)
    db.flush()
    db.add(
        ShopOrderItem(
            order_id=order.id,
            product_id=None,
            name_vi="Dây kháng lực 2",
            unit_price_vnd=400000,
            quantity=1,
        )
    )
    db.add(
        ShopOrderItem(
            order_id=order.id,
            product_id=band.id,
            name_vi=band.name_vi,
            unit_price_vnd=500000,
            quantity=1,
        )
    )
    db.commit()

    shop = AdminStatsService(db).shop_stats(2026)
    slugs = [p["slug"] for p in shop["products"]]
    assert slugs == ["resistance-band", "dumbbell", "bar-and-rings"]
    by_slug = {p["slug"]: p for p in shop["products"]}
    assert by_slug["resistance-band"]["units"] == 1
    assert shop["kpis"]["units"] == 2


def test_admin_stats_month_query_returns_daily_shop_series():
    client, Session = _app_client()
    db = Session()
    _user(db, uid=ADMIN_ID, email="admin@test.com", role="admin", created_at=JAN)
    db.commit()
    db.close()
    res = client.get(
        "/api/v1/admin/stats?year=2026&month=1",
        headers=_bearer(ADMIN_ID, Role.ADMIN.value),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["month"] == 1
    assert body["shop"]["grain"] == "day"
    assert len(body["shop"]["series"]) == 31
