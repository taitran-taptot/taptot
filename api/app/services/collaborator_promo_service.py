"""Collaborator shop promo codes and order attribution."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.pagination import PaginationParams
from app.core.security import Role, hash_password
from app.models.entities import AuthSession, CollaboratorPromo, ShopOrder, ShopOrderItem, User

_CODE_RE = re.compile(r"[A-Z0-9-]{4,32}")
_CANCELLED = "cancelled"
_COMPLETED = "completed"
_LIST_STATUSES = {
    "awaiting_confirm": ("awaiting_confirm", "placed"),
    "packing": ("packing",),
    "shipping": ("shipping",),
    "completed": ("completed",),
    "cancelled": ("cancelled",),
}
_VN_TZ = timezone(timedelta(hours=7))
_PERIODS = frozenset({"day", "month", "year"})


def normalize_promo_code(raw: str | None) -> str | None:
    code = (raw or "").strip().upper()
    if not code:
        return None
    if not _CODE_RE.fullmatch(code):
        raise BadRequestError("Mã giảm giá không hợp lệ")
    return code


def lookup_promo(db: Session, raw: str | None) -> CollaboratorPromo | None:
    code = normalize_promo_code(raw)
    if code is None:
        return None
    row = db.query(CollaboratorPromo).filter(CollaboratorPromo.code == code).one_or_none()
    if row is None:
        raise BadRequestError("Mã giảm giá không hợp lệ")
    return row


def merchandise_discounts(subtotal: int, event_percent: int, promo_percent: int) -> tuple[int, int]:
    """Percent of merchandise, added together. Payable amount never goes below zero."""
    event_vnd = (subtotal * event_percent) // 100 if event_percent else 0
    promo_vnd = (subtotal * promo_percent) // 100 if promo_percent else 0
    overflow = event_vnd + promo_vnd - subtotal
    if overflow > 0:
        promo_cut = min(promo_vnd, overflow)
        promo_vnd -= promo_cut
        overflow -= promo_cut
        event_vnd -= overflow
    return event_vnd, promo_vnd


def _vn_day_start(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=_VN_TZ)


def _period_bounds(period: str, raw_on: str) -> tuple[datetime, datetime, str]:
    kind = (period or "").strip().lower()
    text = (raw_on or "").strip()
    if kind not in _PERIODS:
        raise BadRequestError("Chọn ngày, tháng hoặc năm")
    try:
        if kind == "day":
            day = date.fromisoformat(text)
            return _vn_day_start(day), _vn_day_start(day + timedelta(days=1)), day.strftime("%d/%m/%Y")
        if kind == "month":
            year_s, month_s = text.split("-", 1)
            year, month = int(year_s), int(month_s)
            start_day = date(year, month, 1)
            end_day = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
            return _vn_day_start(start_day), _vn_day_start(end_day), f"{month:02d}/{year}"
        year = int(text)
        return _vn_day_start(date(year, 1, 1)), _vn_day_start(date(year + 1, 1, 1)), str(year)
    except (ValueError, OverflowError) as exc:
        raise BadRequestError("Mốc thời gian không hợp lệ") from exc


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _item_dict(row: ShopOrderItem) -> dict:
    return {
        "id": row.id,
        "product_id": row.product_id,
        "name_vi": row.name_vi,
        "unit_price_vnd": row.unit_price_vnd,
        "quantity": row.quantity,
        "line_total_vnd": row.unit_price_vnd * row.quantity,
    }


def _order_dict(order: ShopOrder, items: list[ShopOrderItem], *, full: bool) -> dict:
    payload = {
        "id": order.id,
        "public_code": order.public_code,
        "order_status": order.order_status,
        "created_at": _iso(order.created_at),
        "recipient_name": order.recipient_name,
        "province_name": order.province_name,
        "district_name": order.district_name,
        "total_vnd": int(order.total_vnd or 0),
        "discount_percent": int(order.discount_percent or 0),
        "discount_vnd": int(order.discount_vnd or 0),
        "promo_code": order.promo_code,
        "promo_percent": int(order.promo_percent or 0),
        "promo_discount_vnd": int(order.promo_discount_vnd or 0),
        "items": [_item_dict(item) for item in items],
    }
    if full:
        payload["phone"] = order.phone
        payload["ward_name"] = order.ward_name
        payload["address_line"] = order.address_line
    return payload


def _page(items: list, total: int, pagination: PaginationParams) -> dict:
    pages = max(1, (total + pagination.page_size - 1) // pagination.page_size)
    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": pages,
    }


class CollaboratorPromoService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _stats_by_owner(self) -> dict[str, tuple[int, int]]:
        rows = (
            self.db.query(
                ShopOrder.promo_owner_user_id,
                func.count(ShopOrder.id),
                func.coalesce(func.sum(ShopOrder.promo_discount_vnd), 0),
            )
            .filter(
                ShopOrder.promo_owner_user_id.isnot(None),
                ShopOrder.order_status != _CANCELLED,
            )
            .group_by(ShopOrder.promo_owner_user_id)
            .all()
        )
        return {str(owner): (int(count), int(total)) for owner, count, total in rows}

    def _account_payload(self, user: User, promo: CollaboratorPromo | None, stats: tuple[int, int]) -> dict:
        count, discount_vnd = stats
        return {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "code": promo.code if promo else None,
            "discount_percent": int(promo.discount_percent) if promo else 10,
            "order_count": count,
            "discount_vnd": discount_vnd,
            "created_at": _iso(user.created_at),
        }

    def list_accounts(self) -> dict:
        rows = (
            self.db.query(User, CollaboratorPromo)
            .outerjoin(CollaboratorPromo, CollaboratorPromo.user_id == User.id)
            .filter(User.role == Role.CTV.value)
            .order_by(User.created_at.desc())
            .all()
        )
        stats = self._stats_by_owner()
        items = [
            self._account_payload(user, promo, stats.get(str(user.id), (0, 0)))
            for user, promo in rows
        ]
        return {"items": items}

    def _require_ctv(self, user_id: str) -> tuple[User, CollaboratorPromo]:
        user = self.db.get(User, user_id)
        if user is None or user.role != Role.CTV.value:
            raise NotFoundError("Collaborator", user_id)
        promo = self.db.get(CollaboratorPromo, user_id)
        if promo is None:
            raise NotFoundError("CollaboratorPromo", user_id)
        return user, promo

    def update_account(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        email: str | None = None,
        password: str | None = None,
        discount_percent: int | None = None,
    ) -> dict:
        user, promo = self._require_ctv(user_id)
        if display_name is not None:
            name = display_name.strip()
            if not name:
                raise BadRequestError("Tên hiển thị không được để trống")
            user.display_name = name
        if email is not None and email != user.email:
            taken = self.db.query(User.id).filter(User.email == email, User.id != user.id).first()
            if taken:
                raise ConflictError("Email đã được dùng")
            user.email = email
        if password is not None:
            user.password_hash = hash_password(password)
            now = datetime.now(UTC)
            (
                self.db.query(AuthSession)
                .filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
                .update({AuthSession.revoked_at: now}, synchronize_session=False)
            )
        if discount_percent is not None:
            promo.discount_percent = discount_percent
        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(promo)
        stats = self._stats_by_owner().get(str(user.id), (0, 0))
        return self._account_payload(user, promo, stats)

    def delete_account(self, user_id: str) -> None:
        user, promo = self._require_ctv(user_id)
        self.db.delete(promo)
        self.db.delete(user)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Không xóa được tài khoản vì còn dữ liệu liên kết") from exc

    def _order_page(self, query, pagination: PaginationParams, *, full: bool, sort: str = "desc") -> dict:
        total = query.count()
        if sort == "asc":
            ordering = (ShopOrder.created_at.asc(), ShopOrder.id.asc())
        else:
            ordering = (ShopOrder.created_at.desc(), ShopOrder.id.desc())
        rows = (
            query.order_by(*ordering)
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        ids = [row.id for row in rows]
        grouped: dict[int, list[ShopOrderItem]] = {row.id: [] for row in rows}
        if ids:
            for item in self.db.query(ShopOrderItem).filter(ShopOrderItem.order_id.in_(ids)).all():
                grouped.setdefault(item.order_id, []).append(item)
        payload = [_order_dict(row, grouped.get(row.id, []), full=full) for row in rows]
        return _page(payload, total, pagination)

    def orders_for(self, user_id: str, pagination: PaginationParams, *, full: bool) -> dict:
        self._require_ctv(user_id)
        query = self.db.query(ShopOrder).filter(ShopOrder.promo_owner_user_id == user_id)
        return self._order_page(query, pagination, full=full)

    def period_stats(
        self,
        user_id: str,
        period: str,
        raw_on: str,
        pagination: PaginationParams,
        *,
        code: str = "",
        sort: str = "desc",
        status: str = "",
    ) -> dict:
        self._require_ctv(user_id)
        start, end, label = _period_bounds(period, raw_on)
        in_period = self.db.query(ShopOrder).filter(
            ShopOrder.promo_owner_user_id == user_id,
            ShopOrder.created_at >= start,
            ShopOrder.created_at < end,
        )
        direction = "asc" if (sort or "").strip().lower() == "asc" else "desc"
        listed = in_period
        needle = (code or "").strip().upper().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        if needle:
            listed = listed.filter(ShopOrder.public_code.ilike(f"%{needle}%", escape="\\"))
        chosen = (status or "").strip().lower()
        if chosen:
            allowed = _LIST_STATUSES.get(chosen)
            if allowed is None:
                raise BadRequestError("Trạng thái đơn không hợp lệ")
            listed = listed.filter(ShopOrder.order_status.in_(allowed))
        order_count = in_period.filter(ShopOrder.order_status != _CANCELLED).count()
        total_vnd, discount_vnd = (
            self.db.query(
                func.coalesce(func.sum(ShopOrder.total_vnd), 0),
                func.coalesce(func.sum(ShopOrder.promo_discount_vnd), 0),
            )
            .filter(
                ShopOrder.promo_owner_user_id == user_id,
                ShopOrder.order_status == _COMPLETED,
                ShopOrder.created_at >= start,
                ShopOrder.created_at < end,
            )
            .one()
        )
        return {
            "period": period,
            "label": label,
            "order_count": int(order_count or 0),
            "total_vnd": int(total_vnd or 0),
            "discount_vnd": int(discount_vnd or 0),
            "orders": self._order_page(listed, pagination, full=False, sort=direction),
        }

    def own_dashboard(self, user_id: str, pagination: PaginationParams) -> dict:
        user, promo = self._require_ctv(user_id)
        stats = self._stats_by_owner().get(str(user.id), (0, 0))
        account = self._account_payload(user, promo, stats)
        completed_discount = (
            self.db.query(func.coalesce(func.sum(ShopOrder.promo_discount_vnd), 0))
            .filter(
                ShopOrder.promo_owner_user_id == user_id,
                ShopOrder.order_status == _COMPLETED,
            )
            .scalar()
        )
        account["discount_vnd"] = int(completed_discount or 0)
        account["orders"] = self.orders_for(user_id, pagination, full=False)
        return account

    def assign_code(self, user_id: str, raw_code: str) -> dict:
        _user, promo = self._require_ctv(user_id)
        if promo.code:
            raise ConflictError("Cộng tác viên này đã có mã giảm giá")
        code = normalize_promo_code(raw_code)
        if code is None:
            raise BadRequestError("Mã giảm giá không hợp lệ")
        taken = (
            self.db.query(CollaboratorPromo.user_id)
            .filter(CollaboratorPromo.code == code, CollaboratorPromo.user_id != user_id)
            .first()
        )
        if taken:
            raise ConflictError("Mã giảm giá đã được dùng")
        promo.code = code
        promo.code_created_at = datetime.now(UTC)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Mã giảm giá đã được dùng") from exc
        self.db.refresh(promo)
        return {
            "code": promo.code,
            "discount_percent": int(promo.discount_percent),
            "code_created_at": _iso(promo.code_created_at),
        }
