"""Admin shop finance and inventory stats."""

from datetime import UTC, datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import Role, create_access_token
from app.main import create_app
from app.models.base import Base
from app.models.entities import (
    ShopOrder,
    ShopOrderItem,
    ShopProduct,
    User,
)
from app.services.admin_stats_service import AdminStatsService


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



def test_admin_stats_forbidden_for_user_and_hlv():
    client, Session = _app_client()
    db = Session()
    _user(db, uid=ADMIN_ID, email="admin@test.com", role="admin", created_at=datetime.now(UTC))
    _user(db, uid=HLV_ID, email="hlv@test.com", role="hlv", created_at=datetime.now(UTC))
    _user(db, uid=USER_ID, email="u@test.com", role="user", created_at=datetime.now(UTC))
    db.commit()
    db.close()

    user_res = client.get("/api/v1/admin/stats", headers=_bearer(USER_ID, Role.USER.value))
    assert user_res.status_code == 401, user_res.text
    hlv_res = client.get("/api/v1/admin/stats", headers=_bearer(HLV_ID, Role.HLV.value))
    assert hlv_res.status_code == 403, hlv_res.text



def test_admin_stats_ok_for_admin():
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
    assert body["year"] == 2026
    assert body["month"] == 1
    assert "finance" in body
    assert "inventory" in body


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


def test_finance_board_month_costs_and_lifetime_profit():
    db = _session()
    _user(db, uid=USER_ID, email="u@test.com", role="user", created_at=JAN)
    band = _kit(db, slug="day-khang-luc", name="Dây kháng lực ngũ sắc", stock=5)
    db.commit()

    kept = ShopOrder(
        user_id=USER_ID,
        phone="0901111111",
        order_status="completed",
        total_vnd=1000000,
        created_at=JAN,
        payment_method="cod",
        payment_status="cod",
    )
    returned = ShopOrder(
        user_id=USER_ID,
        phone="0902222222",
        order_status="returned",
        total_vnd=500000,
        created_at=JAN,
        payment_method="cod",
        payment_status="cod",
    )
    february = ShopOrder(
        user_id=USER_ID,
        phone="0903333333",
        order_status="completed",
        total_vnd=400000,
        created_at=FEB,
        payment_method="cod",
        payment_status="cod",
    )
    db.add_all([kept, returned, february])
    db.flush()
    db.add(
        ShopOrderItem(
            order_id=kept.id,
            product_id=band.id,
            name_vi=band.name_vi,
            unit_price_vnd=500000,
            quantity=2,
        )
    )
    db.add(
        ShopOrderItem(
            order_id=returned.id,
            product_id=band.id,
            name_vi=band.name_vi,
            unit_price_vnd=500000,
            quantity=1,
        )
    )
    db.add(
        ShopOrderItem(
            order_id=february.id,
            product_id=band.id,
            name_vi=band.name_vi,
            unit_price_vnd=400000,
            quantity=1,
        )
    )
    db.commit()

    service = AdminStatsService(db)
    service.set_month_costs(
        2026,
        1,
        50000,
        30000,
        [{"product_id": band.id, "cost_vnd": 100000}],
    )
    service.set_month_costs(
        2026,
        2,
        10000,
        0,
        [{"product_id": band.id, "cost_vnd": 0}],
    )
    service.set_month_costs(2025, 12, 20000, 0, [])

    board = service.finance_board(2026)
    life = board["lifetime"]
    assert life["orders"] == 2
    assert life["revenue_vnd"] == 1400000
    assert life["operating_vnd"] == 80000
    assert life["marketing_vnd"] == 30000
    assert life["profit_vnd"] == 1090000

    january = board["months"][0]
    assert january["revenue_vnd"] == 1000000
    assert january["units_by_product"][0]["units"] == 2
    assert january["cogs_vnd"] == 200000
    assert january["profit_vnd"] == 720000
    february_row = board["months"][1]
    assert february_row["revenue_vnd"] == 400000
    assert february_row["profit_vnd"] == 390000
    product = board["products"][0]
    assert product["months"][0]["units"] == 2
    assert product["months"][0]["revenue_vnd"] == 1000000
    assert product["months"][1]["units"] == 1
    assert product["months"][1]["revenue_vnd"] == 400000
    assert board["order_status"]["completed"] == 2
    assert board["order_status"]["returned"] == 1
    assert board["order_status"]["cancelled"] == 0
    assert life["orders"] == 2


def test_inventory_counts_sold_stock_and_skips_closed_orders():
    db = _session()
    _user(db, uid=USER_ID, email="u@test.com", role="user", created_at=JAN)
    band = _kit(db, slug="day-khang-luc", name="Dây kháng lực", stock=5)
    hidden = _kit(db, slug="ta-an", name="Tạ ẩn", stock=1)
    hidden.is_active = False
    db.commit()

    completed = ShopOrder(
        user_id=USER_ID,
        phone="0901111111",
        order_status="completed",
        total_vnd=1000000,
        created_at=JAN,
        payment_method="cod",
        payment_status="cod",
    )
    returned = ShopOrder(
        user_id=USER_ID,
        phone="0902222222",
        order_status="returned",
        total_vnd=500000,
        created_at=JAN,
        payment_method="cod",
        payment_status="cod",
    )
    cancelled = ShopOrder(
        user_id=USER_ID,
        phone="0903333333",
        order_status="cancelled",
        total_vnd=500000,
        created_at=FEB,
        payment_method="cod",
        payment_status="cod",
    )
    db.add_all([completed, returned, cancelled])
    db.flush()
    db.add_all(
        [
            ShopOrderItem(
                order_id=completed.id,
                product_id=band.id,
                name_vi=band.name_vi,
                unit_price_vnd=500000,
                quantity=2,
            ),
            ShopOrderItem(
                order_id=completed.id,
                product_id=None,
                name_vi="Đã xóa",
                unit_price_vnd=100000,
                quantity=9,
            ),
            ShopOrderItem(
                order_id=returned.id,
                product_id=band.id,
                name_vi=band.name_vi,
                unit_price_vnd=500000,
                quantity=1,
            ),
            ShopOrderItem(
                order_id=cancelled.id,
                product_id=band.id,
                name_vi=band.name_vi,
                unit_price_vnd=500000,
                quantity=4,
            ),
        ]
    )
    db.commit()

    board = AdminStatsService(db).inventory()
    assert board["totals"] == {"total": 8, "sold": 2, "remaining": 6}
    by_name = {row["name_vi"]: row for row in board["products"]}
    assert list(by_name) == ["Dây kháng lực", "Tạ ẩn"]
    assert by_name["Dây kháng lực"] == {
        "id": band.id,
        "name_vi": "Dây kháng lực",
        "total": 7,
        "sold": 2,
        "remaining": 5,
    }
    assert by_name["Tạ ẩn"]["sold"] == 0
    assert by_name["Tạ ẩn"]["remaining"] == 1
    assert by_name["Tạ ẩn"]["total"] == 1


def test_finance_cash_collected_and_product_profit():
    db = _session()
    _user(db, uid=USER_ID, email="u@test.com", role="user", created_at=JAN)
    band = _kit(db, slug="day-khang-luc", name="Dây kháng lực ngũ sắc", stock=5)
    db.commit()

    delivered = ShopOrder(
        user_id=USER_ID,
        phone="0901111111",
        order_status="completed",
        total_vnd=500000,
        created_at=JAN,
        payment_method="cod",
        payment_status="cod",
    )
    packing = ShopOrder(
        user_id=USER_ID,
        phone="0902222222",
        order_status="packing",
        total_vnd=200000,
        created_at=JAN,
        payment_method="cod",
        payment_status="cod",
    )
    paid = ShopOrder(
        user_id=USER_ID,
        phone="0903333333",
        order_status="shipping",
        total_vnd=300000,
        created_at=JAN,
        payment_method="bank_transfer",
        payment_status="paid",
    )
    waiting = ShopOrder(
        user_id=USER_ID,
        phone="0904444444",
        order_status="completed",
        total_vnd=100000,
        created_at=JAN,
        payment_method="bank_transfer",
        payment_status="awaiting_transfer",
    )
    db.add_all([delivered, packing, paid, waiting])
    db.flush()
    db.add(
        ShopOrderItem(
            order_id=delivered.id,
            product_id=band.id,
            name_vi=band.name_vi,
            unit_price_vnd=500000,
            quantity=1,
        )
    )
    db.commit()
    AdminStatsService(db).set_month_costs(
        2026,
        1,
        0,
        0,
        [{"product_id": band.id, "cost_vnd": 100000}],
    )

    board = AdminStatsService(db).finance_board(2026)
    assert board["lifetime"]["collected_vnd"] == 800000
    assert board["lifetime"]["uncollected_vnd"] == 300000
    january = board["products"][0]["months"][0]
    assert january["revenue_vnd"] == 500000
    assert january["profit_vnd"] == 400000
    assert board["months"][0]["profit_vnd"] == 1100000 - 100000
