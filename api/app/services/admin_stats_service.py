"""Monthly ops dashboard for admin: plans, shop orders, users, challenge, redeem."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models.entities import (
    PaymentTransaction,
    ProductRedeemCode,
    PushupChallengeSession,
    ShopOrder,
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


class AdminStatsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def year_stats(self, year: int | None = None) -> dict[str, Any]:
        y = int(year or datetime.now(UTC).year)
        if y < 2000 or y > 2100:
            raise BadRequestError("Năm không hợp lệ")

        months = [_empty_month(f"{y}-{m:02d}") for m in range(1, 13)]
        by_key = {row["month"]: row for row in months}
        prefix = f"{y}-"

        self._fill_plans(by_key, prefix)
        self._fill_orders(by_key, prefix)
        self._fill_users(by_key, prefix)
        self._fill_challenge(by_key, prefix)
        self._fill_redeem(by_key, prefix)

        kpis = {
            "plans_generated": sum(m["plans"]["generated"] for m in months),
            "plans_admin_created": sum(m["plans"]["admin_created"] for m in months),
            "plans_hlv_created": sum(m["plans"]["hlv_created"] for m in months),
            "orders_count": sum(m["orders"]["count"] for m in months),
            "orders_gmv_vnd": sum(m["orders"]["gmv_vnd"] for m in months),
            "orders_collected_vnd": sum(m["orders"]["collected_vnd"] for m in months),
            "users_new": sum(m["users"]["new"] for m in months),
            "challenge_paid_vnd": sum(m["challenge"]["paid_vnd"] for m in months),
            "redeem_used": sum(m["redeem"]["used"] for m in months),
            "redeem_unused": self._unused_codes(),
            "pushup_completed": self._pushup_completed(prefix),
        }
        return {
            "year": y,
            "kpis": kpis,
            "months": months,
            "hlv_accounts": self._hlv_accounts(prefix),
            "open_orders": self._open_orders(),
        }

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
