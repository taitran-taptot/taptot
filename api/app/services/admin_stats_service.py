"""Monthly ops dashboard for admin: plans, shop orders, users, challenge, redeem."""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models.entities import (
    PaymentTransaction,
    ProductRedeemCode,
    PushupChallengeSession,
    ShopOrder,
    ShopOrderItem,
    ShopProduct,
    User,
    UserDailyPlan,
)
from app.services.payment_service import PURPOSE_CHALLENGE_GENERATE
from app.services.redeem_code_service import STATUS_REDEEMED, STATUS_UNUSED
from app.services.shop_service import (
    ORDER_AWAITING,
    ORDER_CANCELLED,
    ORDER_COMPLETED,
    ORDER_PACKING,
    ORDER_SHIPPING,
    PAY_STATUS_AWAITING,
    PAY_STATUS_COD,
    PAY_STATUS_PAID,
)

ORDER_STATUSES = (
    ORDER_AWAITING,
    ORDER_PACKING,
    ORDER_SHIPPING,
    ORDER_COMPLETED,
    ORDER_CANCELLED,
)
STAFF_ROLES = frozenset({"admin", "hlv"})
_COLLECTED_PAY = frozenset({PAY_STATUS_PAID, PAY_STATUS_COD})
_ADMIN_SOURCES = frozenset({"manual", "imported"})


def _is_sqlite(db: Session) -> bool:
    bind = db.get_bind()
    return bool(bind is not None and bind.dialect.name == "sqlite")


def _month_expr(db: Session, column: Any):
    if _is_sqlite(db):
        return func.strftime("%Y-%m", column)
    # Naive UTC timestamps — avoid session TimeZone shifting the month.
    return func.to_char(column, "YYYY-MM")


def _empty_month(ym: str) -> dict[str, Any]:
    return {
        "month": ym,
        "plans": {
            "generated": 0,
            "admin_created": 0,
            "hlv_created": 0,
            "templates": 0,
            "challenge_100": 0,
            "guest": 0,
        },
        "orders": {
            "count": 0,
            "gmv_vnd": 0,
            "collected_vnd": 0,
            "by_status": {status: 0 for status in ORDER_STATUSES},
            "by_payment_method": {},
        },
        "users": {"new": 0, "staff": 0},
        "challenge": {"paid_count": 0, "paid_vnd": 0},
        "redeem": {"used": 0},
    }


def _ym(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m")


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _period_bounds(year: int, month: int | None) -> tuple[datetime, datetime]:
    start = datetime(year, month or 1, 1)
    if month:
        last = monthrange(year, month)[1]
        end = datetime(year, month, last) + timedelta(days=1)
    else:
        end = datetime(year + 1, 1, 1)
    return start, end


def _empty_shop_bucket(period: str, slugs: list[str]) -> dict[str, Any]:
    return {
        "period": period,
        "orders": 0,
        "cancelled": 0,
        "units": 0,
        "gross_vnd": 0,
        "discount_vnd": 0,
        "net_vnd": 0,
        "collected_vnd": 0,
        "shipping_vnd": 0,
        "units_by_slug": {slug: 0 for slug in slugs},
    }


class AdminStatsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def year_stats(self, year: int | None = None, month: int | None = None) -> dict[str, Any]:
        y = int(year or datetime.now(UTC).year)
        if y < 2000 or y > 2100:
            raise BadRequestError("Năm không hợp lệ")
        m = int(month) if month is not None else None
        if m is not None and (m < 1 or m > 12):
            raise BadRequestError("Tháng không hợp lệ")

        months = [_empty_month(f"{y}-{i:02d}") for i in range(1, 13)]
        by_key = {row["month"]: row for row in months}
        prefix = f"{y}-"

        self._fill_plans(by_key, prefix)
        self._fill_orders(by_key, prefix)
        self._fill_users(by_key, prefix)
        self._fill_challenge(by_key, prefix)
        self._fill_redeem(by_key, prefix)

        kpis = {
            "plans_generated": sum(row["plans"]["generated"] for row in months),
            "plans_admin_created": sum(row["plans"]["admin_created"] for row in months),
            "plans_hlv_created": sum(row["plans"]["hlv_created"] for row in months),
            "orders_count": sum(row["orders"]["count"] for row in months),
            "orders_gmv_vnd": sum(row["orders"]["gmv_vnd"] for row in months),
            "orders_collected_vnd": sum(row["orders"]["collected_vnd"] for row in months),
            "users_new": sum(row["users"]["new"] for row in months),
            "challenge_paid_vnd": sum(row["challenge"]["paid_vnd"] for row in months),
            "redeem_used": sum(row["redeem"]["used"] for row in months),
            "redeem_unused": self._unused_codes(),
            "pushup_completed": self._pushup_completed(prefix),
        }
        return {
            "year": y,
            "month": m,
            "kpis": kpis,
            "months": months,
            "hlv_accounts": self._hlv_accounts(prefix),
            "open_orders": self._open_orders(),
            "shop": self.shop_stats(y, m),
        }

    def shop_stats(self, year: int, month: int | None = None) -> dict[str, Any]:
        grain = "day" if month else "month"
        start, end = _period_bounds(year, month)

        products = {p.id: p for p in self.db.query(ShopProduct).all()}
        catalog: dict[str, dict[str, Any]] = {}
        for product in products.values():
            slug = str(product.slug or "")
            if not slug or not bool(product.is_active):
                continue
            catalog[slug] = {
                "slug": slug,
                "name_vi": product.name_vi or slug,
                "units": 0,
                "line_vnd": 0,
                "order_count": 0,
                "stock_qty": int(product.stock_qty or 0),
            }
        series = self._shop_series_shell(year, month, list(catalog.keys()))
        by_key = {row["period"]: row for row in series}

        orders = self.db.query(ShopOrder).all()
        order_ids = []
        active_ids: set[int] = set()
        for order in orders:
            created = _naive_utc(order.created_at)
            if created is None or created < start or created >= end:
                continue
            order_ids.append(order.id)
            if str(order.order_status or "") != ORDER_CANCELLED:
                active_ids.add(order.id)

        items_by_order: dict[int, list[ShopOrderItem]] = {oid: [] for oid in order_ids}
        if order_ids:
            item_rows = (
                self.db.query(ShopOrderItem).filter(ShopOrderItem.order_id.in_(order_ids)).all()
            )
            for item in item_rows:
                items_by_order.setdefault(item.order_id, []).append(item)

        kpis = {
            "orders": 0,
            "cancelled": 0,
            "units": 0,
            "gross_vnd": 0,
            "discount_vnd": 0,
            "net_vnd": 0,
            "collected_vnd": 0,
            "shipping_vnd": 0,
            "aov_vnd": 0,
            "cancel_rate": 0.0,
            "discount_orders": 0,
            "discount_order_rate": 0.0,
            "repeat_customers": 0,
            "unique_customers": 0,
        }
        by_status = {status: 0 for status in ORDER_STATUSES}
        by_pay: dict[str, int] = {}
        by_percent = {"5": 0, "10": 0, "15": 0, "other": 0}
        customer_orders: dict[str, int] = {}
        product_orders: dict[str, set[int]] = {slug: set() for slug in catalog}

        for order in orders:
            created = _naive_utc(order.created_at)
            if created is None or created < start or created >= end:
                continue
            key = created.strftime("%Y-%m-%d") if grain == "day" else created.strftime("%Y-%m")
            bucket = by_key.get(key)
            status = str(order.order_status or "")
            if status in by_status:
                by_status[status] += 1
            else:
                by_status[status] = 1
            cancelled = status == ORDER_CANCELLED
            if cancelled:
                kpis["cancelled"] += 1
                if bucket is not None:
                    bucket["cancelled"] += 1
                continue

            kpis["orders"] += 1
            net = int(order.total_vnd or 0)
            discount = int(order.discount_vnd or 0)
            ship = int(order.shipping_fee_vnd or 0)
            kpis["net_vnd"] += net
            kpis["discount_vnd"] += discount
            kpis["shipping_vnd"] += ship
            pay = str(order.payment_status or "")
            if pay in _COLLECTED_PAY:
                kpis["collected_vnd"] += net
            method = str(order.payment_method or "").strip()
            if method:
                by_pay[method] = int(by_pay.get(method, 0)) + 1
            percent = int(order.discount_percent or 0)
            if discount > 0 or percent > 0:
                kpis["discount_orders"] += 1
                label = str(percent) if str(percent) in by_percent else "other"
                if percent in (5, 10, 15):
                    label = str(percent)
                by_percent[label] = int(by_percent.get(label, 0)) + 1
            cust = (order.phone or "").strip() or (str(order.user_id) if order.user_id else f"order:{order.id}")
            customer_orders[cust] = int(customer_orders.get(cust, 0)) + 1

            line_gross = 0
            line_units = 0
            if bucket is not None:
                bucket["orders"] += 1
                bucket["net_vnd"] += net
                bucket["discount_vnd"] += discount
                bucket["shipping_vnd"] += ship
                if pay in _COLLECTED_PAY:
                    bucket["collected_vnd"] += net

            for item in items_by_order.get(order.id, []):
                qty = int(item.quantity or 0)
                line = int(item.unit_price_vnd or 0) * qty
                line_gross += line
                line_units += qty
                product = products.get(item.product_id) if item.product_id else None
                slug = str(product.slug) if product and product.slug else ""
                if slug in catalog:
                    catalog[slug]["units"] += qty
                    catalog[slug]["line_vnd"] += line
                    product_orders[slug].add(order.id)
                    if bucket is not None:
                        bucket["units_by_slug"][slug] = int(
                            bucket["units_by_slug"].get(slug, 0)
                        ) + qty

            kpis["gross_vnd"] += line_gross
            kpis["units"] += line_units
            if bucket is not None:
                bucket["gross_vnd"] += line_gross
                bucket["units"] += line_units

        for slug, ids in product_orders.items():
            if slug in catalog:
                catalog[slug]["order_count"] = len(ids)

        total_seen = kpis["orders"] + kpis["cancelled"]
        kpis["cancel_rate"] = round(kpis["cancelled"] / total_seen, 4) if total_seen else 0.0
        kpis["aov_vnd"] = int(kpis["net_vnd"] / kpis["orders"]) if kpis["orders"] else 0
        kpis["discount_order_rate"] = (
            round(kpis["discount_orders"] / kpis["orders"], 4) if kpis["orders"] else 0.0
        )
        kpis["unique_customers"] = len(customer_orders)
        kpis["repeat_customers"] = sum(1 for n in customer_orders.values() if n >= 2)

        pushup_done = 0
        for (finished,) in (
            self.db.query(PushupChallengeSession.finished_at)
            .filter(PushupChallengeSession.finished_at.isnot(None))
            .all()
        ):
            stamp = _naive_utc(finished)
            if stamp is not None and start <= stamp < end:
                pushup_done += 1

        product_rows = sorted(
            catalog.values(),
            key=lambda row: (-int(row["units"]), row["name_vi"], row["slug"]),
        )
        return {
            "grain": grain,
            "kpis": kpis,
            "products": product_rows,
            "series": series,
            "funnel": by_status,
            "payments": by_pay,
            "pushup": {
                "sessions_completed": pushup_done,
                "discount_orders": kpis["discount_orders"],
                "discount_vnd": kpis["discount_vnd"],
                "by_percent": by_percent,
            },
        }

    def _shop_series_shell(
        self, year: int, month: int | None, slugs: list[str]
    ) -> list[dict[str, Any]]:
        if month:
            days = monthrange(year, month)[1]
            return [
                _empty_shop_bucket(f"{year}-{month:02d}-{d:02d}", slugs) for d in range(1, days + 1)
            ]
        return [_empty_shop_bucket(f"{year}-{m:02d}", slugs) for m in range(1, 13)]

    def _month_col(self, column: Any):
        return _month_expr(self.db, column)

    def _fill_plans(self, by_key: dict[str, dict[str, Any]], prefix: str) -> None:
        month = self._month_col(UserDailyPlan.created_at)
        year_filter = month.like(f"{prefix}%")

        def add(field: str, rows: list) -> None:
            for ym, n in rows:
                bucket = by_key.get(str(ym or ""))
                if bucket is not None:
                    bucket["plans"][field] += int(n or 0)

        add(
            "generated",
            self.db.query(month, func.count(UserDailyPlan.id))
            .filter(year_filter, UserDailyPlan.source == "ai")
            .group_by(month)
            .all(),
        )
        add(
            "admin_created",
            self.db.query(month, func.count(UserDailyPlan.id))
            .join(User, User.id == UserDailyPlan.user_id)
            .filter(
                year_filter,
                UserDailyPlan.source.in_(_ADMIN_SOURCES),
                User.role == "admin",
            )
            .group_by(month)
            .all(),
        )
        add(
            "hlv_created",
            self.db.query(month, func.count(UserDailyPlan.id))
            .join(User, User.id == UserDailyPlan.user_id)
            .filter(year_filter, User.role == "hlv")
            .group_by(month)
            .all(),
        )
        add(
            "templates",
            self.db.query(month, func.count(UserDailyPlan.id))
            .filter(year_filter, UserDailyPlan.is_template.is_(True))
            .group_by(month)
            .all(),
        )
        add(
            "challenge_100",
            self.db.query(month, func.count(UserDailyPlan.id))
            .filter(year_filter, UserDailyPlan.challenge_100_days.is_(True))
            .group_by(month)
            .all(),
        )
        add(
            "guest",
            self.db.query(month, func.count(UserDailyPlan.id))
            .filter(year_filter, UserDailyPlan.user_id.is_(None))
            .group_by(month)
            .all(),
        )

    def _hlv_accounts(self, prefix: str) -> list[dict[str, Any]]:
        month = self._month_col(UserDailyPlan.created_at)
        hlvs = self.db.query(User).filter(User.role == "hlv").all()
        accounts: dict[str, dict[str, Any]] = {}
        for user in hlvs:
            uid = str(user.id)
            accounts[uid] = {
                "user_id": uid,
                "email": user.email,
                "display_name": user.display_name,
                "total": 0,
                "generated": 0,
                "manual": 0,
                "template": 0,
                "imported": 0,
            }
        rows = (
            self.db.query(UserDailyPlan.user_id, UserDailyPlan.source, func.count(UserDailyPlan.id))
            .join(User, User.id == UserDailyPlan.user_id)
            .filter(month.like(f"{prefix}%"), User.role == "hlv")
            .group_by(UserDailyPlan.user_id, UserDailyPlan.source)
            .all()
        )
        source_fields = {
            "ai": "generated",
            "manual": "manual",
            "template": "template",
            "imported": "imported",
        }
        for user_id, source, n in rows:
            uid = str(user_id or "")
            bucket = accounts.get(uid)
            if bucket is None:
                continue
            count = int(n or 0)
            bucket["total"] += count
            field = source_fields.get(str(source or ""))
            if field:
                bucket[field] += count
        return sorted(
            accounts.values(),
            key=lambda row: (-int(row["total"]), str(row["email"] or ""), str(row["display_name"] or "")),
        )

    def _fill_orders(self, by_key: dict[str, dict[str, Any]], prefix: str) -> None:
        month = self._month_col(ShopOrder.created_at)
        rows = (
            self.db.query(
                month,
                ShopOrder.order_status,
                ShopOrder.payment_status,
                ShopOrder.payment_method,
                func.count(ShopOrder.id),
                func.coalesce(func.sum(ShopOrder.total_vnd), 0),
            )
            .filter(month.like(f"{prefix}%"))
            .group_by(
                month,
                ShopOrder.order_status,
                ShopOrder.payment_status,
                ShopOrder.payment_method,
            )
            .all()
        )
        for ym, status, pay_status, method, n, total in rows:
            bucket = by_key.get(str(ym or ""))
            if bucket is None:
                continue
            count = int(n or 0)
            amount = int(total or 0)
            st = str(status or "")
            if st in bucket["orders"]["by_status"]:
                bucket["orders"]["by_status"][st] += count
            else:
                bucket["orders"]["by_status"][st] = count
            if st != ORDER_CANCELLED:
                bucket["orders"]["count"] += count
                bucket["orders"]["gmv_vnd"] += amount
                if str(pay_status or "") in _COLLECTED_PAY:
                    bucket["orders"]["collected_vnd"] += amount
            pay_method = str(method or "").strip()
            if pay_method:
                methods = bucket["orders"]["by_payment_method"]
                methods[pay_method] = int(methods.get(pay_method, 0)) + count

    def _fill_users(self, by_key: dict[str, dict[str, Any]], prefix: str) -> None:
        month = self._month_col(User.created_at)
        rows = (
            self.db.query(month, User.role, func.count(User.id))
            .filter(month.like(f"{prefix}%"))
            .group_by(month, User.role)
            .all()
        )
        for ym, role, n in rows:
            bucket = by_key.get(str(ym or ""))
            if bucket is None:
                continue
            count = int(n or 0)
            if str(role or "") in STAFF_ROLES:
                bucket["users"]["staff"] += count
            else:
                bucket["users"]["new"] += count

    def _fill_challenge(self, by_key: dict[str, dict[str, Any]], prefix: str) -> None:
        rows = self.db.query(PaymentTransaction).all()
        for txn in rows:
            ym = _ym(txn.created_at)
            if not ym or not ym.startswith(prefix):
                continue
            meta = txn.transaction_metadata or {}
            if not isinstance(meta, dict):
                continue
            if meta.get("purpose") != PURPOSE_CHALLENGE_GENERATE:
                continue
            if str(txn.status or "") != "completed":
                continue
            bucket = by_key.get(ym)
            if bucket is None:
                continue
            bucket["challenge"]["paid_count"] += 1
            bucket["challenge"]["paid_vnd"] += int(txn.amount_vnd or 0)

    def _fill_redeem(self, by_key: dict[str, dict[str, Any]], prefix: str) -> None:
        rows = (
            self.db.query(ProductRedeemCode)
            .filter(
                ProductRedeemCode.status == STATUS_REDEEMED,
                ProductRedeemCode.redeemed_at.isnot(None),
            )
            .all()
        )
        for row in rows:
            ym = _ym(row.redeemed_at)
            if not ym or not ym.startswith(prefix):
                continue
            bucket = by_key.get(ym)
            if bucket is not None:
                bucket["redeem"]["used"] += 1

    def _unused_codes(self) -> int:
        return int(
            self.db.query(func.count(ProductRedeemCode.id))
            .filter(ProductRedeemCode.status == STATUS_UNUSED)
            .scalar()
            or 0
        )

    def _pushup_completed(self, prefix: str) -> int:
        n = 0
        rows = (
            self.db.query(PushupChallengeSession.finished_at)
            .filter(PushupChallengeSession.finished_at.isnot(None))
            .all()
        )
        for (finished,) in rows:
            ym = _ym(finished)
            if ym and ym.startswith(prefix):
                n += 1
        return n

    def _open_orders(self) -> dict[str, int]:
        awaiting_confirm = int(
            self.db.query(func.count(ShopOrder.id))
            .filter(ShopOrder.order_status == ORDER_AWAITING)
            .scalar()
            or 0
        )
        awaiting_transfer = int(
            self.db.query(func.count(ShopOrder.id))
            .filter(ShopOrder.payment_status == PAY_STATUS_AWAITING)
            .scalar()
            or 0
        )
        return {
            "awaiting_confirm": awaiting_confirm,
            "awaiting_transfer": awaiting_transfer,
        }
