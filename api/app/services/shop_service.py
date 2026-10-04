from __future__ import annotations

import logging
import re
import secrets
import string
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import ShopCartItem, ShopOrder, ShopOrderItem, ShopProduct
from app.services.slug import unique_slug
from app.services.sms_service import SmsService

logger = logging.getLogger(__name__)

ORDER_AWAITING = "awaiting_confirm"
ORDER_PACKING = "packing"
ORDER_SHIPPING = "shipping"
ORDER_COMPLETED = "completed"
ORDER_CANCELLED = "cancelled"

# Backward-compatible alias used by older tests/callers
ORDER_PLACED = ORDER_AWAITING

PAYMENT_COD = "cod"
PAYMENT_BANK = "bank_transfer"

PAY_STATUS_UNPAID = "unpaid"
PAY_STATUS_AWAITING = "awaiting_transfer"
PAY_STATUS_PAID = "paid"
PAY_STATUS_COD = "cod"

FULFILLMENT_FLOW = (
    ORDER_AWAITING,
    ORDER_PACKING,
    ORDER_SHIPPING,
    ORDER_COMPLETED,
)

PHONE_RE = re.compile(r"^0\d{9}$")
PUBLIC_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _now() -> datetime:
    return datetime.now(UTC)


def _is_sqlite(db: Session) -> bool:
    bind = db.get_bind()
    return bool(bind is not None and bind.dialect.name == "sqlite")


def normalize_vn_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", (raw or "").strip())
    if digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    return digits


def validate_vn_phone(raw: str) -> str:
    phone = normalize_vn_phone(raw)
    if not PHONE_RE.match(phone):
        raise BadRequestError("Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0")
    return phone


def product_to_dict(row: ShopProduct) -> dict:
    return {
        "id": row.id,
        "slug": row.slug,
        "name_vi": row.name_vi,
        "description_vi": row.description_vi,
        "price_vnd": row.price_vnd,
        "stock_qty": row.stock_qty,
        "image_url": row.image_url,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def order_item_to_dict(row: ShopOrderItem) -> dict:
    return {
        "id": row.id,
        "product_id": row.product_id,
        "name_vi": row.name_vi,
        "unit_price_vnd": row.unit_price_vnd,
        "quantity": row.quantity,
        "line_total_vnd": row.unit_price_vnd * row.quantity,
    }


def bank_transfer_info(total_vnd: int, public_code: str) -> dict:
    settings = get_settings()
    bin_code = (settings.shop_bank_bin or "").strip()
    account = (settings.shop_bank_account or "").strip()
    name = (settings.shop_bank_account_name or "").strip()
    bank_name = (settings.shop_bank_name or "").strip()
    qr_url = None
    if bin_code and account:
        qr_url = (
            f"https://img.vietqr.io/image/{bin_code}-{account}-compact2.png"
            f"?amount={int(total_vnd)}"
            f"&addInfo={quote(public_code)}"
            f"&accountName={quote(name or 'TAPTOT')}"
        )
    return {
        "bank_name": bank_name or None,
        "bank_bin": bin_code or None,
        "account_number": account or None,
        "account_name": name or None,
        "transfer_content": public_code,
        "amount_vnd": int(total_vnd),
        "qr_image_url": qr_url,
    }


def order_to_dict(
    row: ShopOrder,
    items: list[ShopOrderItem] | None = None,
    *,
    include_payment_details: bool = False,
    gift_codes: list[dict[str, Any]] | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "id": row.id,
        "user_id": str(row.user_id) if row.user_id else None,
        "public_code": row.public_code,
        "order_status": row.order_status,
        "fulfillment_status": row.order_status,
        "total_vnd": row.total_vnd,
        "shipping_fee_vnd": int(row.shipping_fee_vnd or 0),
        "note": row.note,
        "recipient_name": row.recipient_name,
        "phone": row.phone,
        "province_code": row.province_code,
        "province_name": row.province_name,
        "district_code": row.district_code,
        "district_name": row.district_name,
        "ward_code": row.ward_code,
        "ward_name": row.ward_name,
        "address_line": row.address_line,
        "payment_method": row.payment_method,
        "payment_status": row.payment_status,
        "discount_percent": int(row.discount_percent or 0),
        "discount_vnd": int(row.discount_vnd or 0),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    if items is not None:
        payload["items"] = [order_item_to_dict(i) for i in items]
    if gift_codes is not None:
        payload["gift_codes"] = gift_codes
    if include_payment_details and row.payment_method == PAYMENT_BANK and row.public_code:
        payload["bank_transfer"] = bank_transfer_info(row.total_vnd, row.public_code)
    return payload


class ShopService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_public_products(self, pagination: PaginationParams) -> PaginatedResponse[dict]:
        query = self.db.query(ShopProduct).filter(ShopProduct.is_active.is_(True))
        total = query.count()
        rows = (
            query.order_by(ShopProduct.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            [product_to_dict(r) for r in rows],
            total,
            pagination.page,
            pagination.page_size,
        )

    def get_public_product(self, product_id: int) -> dict:
        row = self.db.get(ShopProduct, product_id)
        if not row or not row.is_active:
            raise NotFoundError("ShopProduct", product_id)
        return product_to_dict(row)

    def list_admin_products(
        self,
        pagination: PaginationParams,
        *,
        q: str | None = None,
        is_active: bool | None = None,
    ) -> PaginatedResponse[dict]:
        query = self.db.query(ShopProduct)
        if q and q.strip():
            term = f"%{q.strip()}%"
            query = query.filter(
                (ShopProduct.name_vi.ilike(term)) | (ShopProduct.slug.ilike(term))
            )
        if is_active is not None:
            query = query.filter(ShopProduct.is_active.is_(is_active))
        total = query.count()
        rows = (
            query.order_by(ShopProduct.updated_at.desc(), ShopProduct.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            [product_to_dict(r) for r in rows],
            total,
            pagination.page,
            pagination.page_size,
        )

    def create_product(self, data: dict) -> dict:
        name = (data.get("name_vi") or "").strip()
        if not name:
            raise BadRequestError("name_vi không được trống")
        price = int(data.get("price_vnd") or 0)
        stock = int(data.get("stock_qty") or 0)
        if price < 0:
            raise BadRequestError("price_vnd phải ≥ 0")
        if stock < 0:
            raise BadRequestError("stock_qty phải ≥ 0")
        now = _now()
        row = ShopProduct(
            slug=unique_slug(
                self.db, ShopProduct, data.get("slug") or name, fallback="san-pham"
            ),
            name_vi=name,
            description_vi=(data.get("description_vi") or "").strip() or None,
            price_vnd=price,
            stock_qty=stock,
            image_url=(data.get("image_url") or "").strip() or None,
            is_active=bool(data.get("is_active", True)),
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return product_to_dict(row)

    def update_product(self, product_id: int, data: dict) -> dict:
        row = self.db.get(ShopProduct, product_id)
        if not row:
            raise NotFoundError("ShopProduct", product_id)
        if "name_vi" in data and data["name_vi"] is not None:
            name = str(data["name_vi"]).strip()
            if not name:
                raise BadRequestError("name_vi không được trống")
            row.name_vi = name
        if "description_vi" in data:
            desc = (data["description_vi"] or "").strip() if data["description_vi"] else ""
            row.description_vi = desc or None
        if "price_vnd" in data and data["price_vnd"] is not None:
            price = int(data["price_vnd"])
            if price < 0:
                raise BadRequestError("price_vnd phải ≥ 0")
            row.price_vnd = price
        if "stock_qty" in data and data["stock_qty"] is not None:
            stock = int(data["stock_qty"])
            if stock < 0:
                raise BadRequestError("stock_qty phải ≥ 0")
            row.stock_qty = stock
        if "image_url" in data:
            url = (data["image_url"] or "").strip() if data["image_url"] else ""
            row.image_url = url or None
        if "is_active" in data and data["is_active"] is not None:
            row.is_active = bool(data["is_active"])
        if "slug" in data and data["slug"]:
            row.slug = unique_slug(
                self.db,
                ShopProduct,
                str(data["slug"]),
                exclude_id=row.id,
                fallback="san-pham",
            )
        row.updated_at = _now()
        self.db.commit()
        self.db.refresh(row)
        return product_to_dict(row)

    def get_cart(self, user_id: str) -> dict:
        rows = (
            self.db.query(ShopCartItem, ShopProduct)
            .join(ShopProduct, ShopProduct.id == ShopCartItem.product_id)
            .filter(ShopCartItem.user_id == user_id)
            .all()
        )
        items = []
        total = 0
        for cart, product in rows:
            line = cart.quantity * product.price_vnd
            total += line
            items.append(
                {
                    "product_id": product.id,
                    "name_vi": product.name_vi,
                    "price_vnd": product.price_vnd,
                    "stock_qty": product.stock_qty,
                    "image_url": product.image_url,
                    "is_active": bool(product.is_active),
                    "quantity": cart.quantity,
                    "line_total_vnd": line,
                }
            )
        return {"items": items, "total_vnd": total}

    def add_to_cart(self, user_id: str, product_id: int, quantity: int) -> dict:
        if quantity < 1:
            raise BadRequestError("quantity phải ≥ 1")
        product = self.db.get(ShopProduct, product_id)
        if not product or not product.is_active:
            raise NotFoundError("ShopProduct", product_id)
        if product.stock_qty < 1:
            raise ConflictError("Sản phẩm đã hết hàng")
        row = (
            self.db.query(ShopCartItem)
            .filter(
                ShopCartItem.user_id == user_id,
                ShopCartItem.product_id == product_id,
            )
            .first()
        )
        next_qty = quantity if not row else row.quantity + quantity
        if next_qty > product.stock_qty:
            raise ConflictError(f"Chỉ còn {product.stock_qty} sản phẩm trong kho")
        if row:
            row.quantity = next_qty
        else:
            self.db.add(
                ShopCartItem(user_id=user_id, product_id=product_id, quantity=quantity)
            )
        self.db.commit()
        return self.get_cart(user_id)

    def set_cart_item(self, user_id: str, product_id: int, quantity: int) -> dict:
        row = (
            self.db.query(ShopCartItem)
            .filter(
                ShopCartItem.user_id == user_id,
                ShopCartItem.product_id == product_id,
            )
            .first()
        )
        if quantity <= 0:
            if row:
                self.db.delete(row)
                self.db.commit()
            return self.get_cart(user_id)
        product = self.db.get(ShopProduct, product_id)
        if not product or not product.is_active:
            raise NotFoundError("ShopProduct", product_id)
        if quantity > product.stock_qty:
            raise ConflictError(f"Chỉ còn {product.stock_qty} sản phẩm trong kho")
        if row:
            row.quantity = quantity
        else:
            self.db.add(
                ShopCartItem(user_id=user_id, product_id=product_id, quantity=quantity)
            )
        self.db.commit()
        return self.get_cart(user_id)

    def merge_cart(self, user_id: str, items: list[dict]) -> dict:
        """Merge guest localStorage lines into the authenticated cart."""
        for raw in items or []:
            try:
                product_id = int(raw.get("product_id"))
                quantity = int(raw.get("quantity") or 0)
            except (TypeError, ValueError):
                continue
            if quantity < 1:
                continue
            try:
                self.add_to_cart(user_id, product_id, quantity)
            except (NotFoundError, ConflictError, BadRequestError) as exc:
                logger.info("merge_cart skip product=%s: %s", product_id, exc)
        return self.get_cart(user_id)

    def _alloc_public_code(self) -> str:
        for _ in range(20):
            suffix = "".join(secrets.choice(PUBLIC_CODE_ALPHABET) for _ in range(5))
            code = f"TAPTOT-{suffix}"
            exists = (
                self.db.query(ShopOrder.id)
                .filter(ShopOrder.public_code == code)
                .first()
            )
            if not exists:
                return code
        raise ConflictError("Không tạo được mã đơn, thử lại")

    def _resolve_checkout_lines(
        self,
        *,
        user_id: str | None,
        raw_items: list[dict] | None,
        clear_user_cart: bool,
    ) -> tuple[list[tuple[int, int, ShopProduct]], list[ShopCartItem]]:
        """Return (lines of product_id, qty, product) and cart rows to delete."""
        cart_rows: list[ShopCartItem] = []
        desired: list[tuple[int, int]] = []

        if raw_items:
            for raw in raw_items:
                try:
                    pid = int(raw["product_id"])
                    qty = int(raw.get("quantity") or 0)
                except (KeyError, TypeError, ValueError) as exc:
                    raise BadRequestError("Giỏ hàng không hợp lệ") from exc
                if qty < 1:
                    raise BadRequestError("quantity phải ≥ 1")
                desired.append((pid, qty))
        elif user_id:
            cart_rows = (
                self.db.query(ShopCartItem)
                .filter(ShopCartItem.user_id == user_id)
                .all()
            )
            if not cart_rows:
                raise BadRequestError("Giỏ hàng trống")
            desired = [(r.product_id, r.quantity) for r in cart_rows]
        else:
            raise BadRequestError("Giỏ hàng trống")

        product_ids = [pid for pid, _ in desired]
        query = self.db.query(ShopProduct).filter(ShopProduct.id.in_(product_ids))
        if not _is_sqlite(self.db):
            query = query.with_for_update()
        products = {p.id: p for p in query.all()}

        shortages: list[str] = []
        lines: list[tuple[int, int, ShopProduct]] = []
        for pid, qty in desired:
            product = products.get(pid)
            if not product or not product.is_active:
                shortages.append("Một sản phẩm không còn bán")
                continue
            if qty > product.stock_qty:
                shortages.append(f"{product.name_vi}: chỉ còn {product.stock_qty}")
                continue
            lines.append((pid, qty, product))
        if shortages:
            raise ConflictError("; ".join(shortages))
        if not lines:
            raise BadRequestError("Giỏ hàng không hợp lệ")

        to_clear = cart_rows if (clear_user_cart and user_id) else []
        return lines, to_clear

    def checkout(
        self,
        user_id: str | None = None,
        note: str | None = None,
        *,
        recipient_name: str | None = None,
        phone: str | None = None,
        province_code: str | None = None,
        province_name: str | None = None,
        district_code: str | None = None,
        district_name: str | None = None,
        ward_code: str | None = None,
        ward_name: str | None = None,
        address_line: str | None = None,
        payment_method: str | None = None,
        items: list[dict] | None = None,
        pushup_ticket: str | None = None,
    ) -> dict:
        # Backward-compatible: old callers checkout(user_id, note) with server cart only.
        shipping_required = any(
            [
                recipient_name,
                phone,
                province_code,
                province_name,
                district_code,
                district_name,
                ward_code,
                ward_name,
                address_line,
                payment_method,
                items,
            ]
        )

        if shipping_required or not user_id:
            name = (recipient_name or "").strip()
            if len(name) < 2:
                raise BadRequestError("Họ và tên người nhận bắt buộc")
            phone_norm = validate_vn_phone(phone or "")
            for label, value in (
                ("Tỉnh/Thành phố", province_name),
                ("Quận/Huyện", district_name),
                ("Phường/Xã", ward_name),
            ):
                if not (value or "").strip():
                    raise BadRequestError(f"{label} bắt buộc")
            addr = (address_line or "").strip()
            if len(addr) < 3:
                raise BadRequestError("Địa chỉ số nhà / đường bắt buộc")
            method = (payment_method or "").strip().lower()
            if method not in {PAYMENT_COD, PAYMENT_BANK}:
                raise BadRequestError("Chọn COD hoặc chuyển khoản")
            pay_status = PAY_STATUS_COD if method == PAYMENT_COD else PAY_STATUS_AWAITING
        else:
            # Legacy logged-in note-only checkout
            name = None
            phone_norm = None
            province_code = province_name = None
            district_code = district_name = None
            ward_code = ward_name = None
            addr = None
            method = PAYMENT_COD
            pay_status = PAY_STATUS_COD

        lines, cart_to_clear = self._resolve_checkout_lines(
            user_id=user_id,
            raw_items=items,
            clear_user_cart=True,
        )

        discount_percent = 0
        ticket_session = None
        raw_ticket = (pushup_ticket or "").strip()
        if raw_ticket:
            from app.services.pushup_challenge import ticket_for_checkout

            discount_percent, ticket_session = ticket_for_checkout(self.db, raw_ticket)

        public_code = self._alloc_public_code()
        total = 0
        order = ShopOrder(
            user_id=user_id,
            order_status=ORDER_AWAITING,
            total_vnd=0,
            shipping_fee_vnd=0,
            discount_percent=0,
            discount_vnd=0,
            note=(note or "").strip() or None,
            created_at=_now(),
            public_code=public_code,
            recipient_name=name,
            phone=phone_norm,
            province_code=(province_code or "").strip() or None,
            province_name=(province_name or "").strip() or None,
            district_code=(district_code or "").strip() or None,
            district_name=(district_name or "").strip() or None,
            ward_code=(ward_code or "").strip() or None,
            ward_name=(ward_name or "").strip() or None,
            address_line=addr,
            payment_method=method,
            payment_status=pay_status,
        )
        self.db.add(order)
        self.db.flush()

        order_items: list[ShopOrderItem] = []
        for _pid, qty, product in lines:
            product.stock_qty -= qty
            product.updated_at = _now()
            line_total = product.price_vnd * qty
            total += line_total
            item = ShopOrderItem(
                order_id=order.id,
                product_id=product.id,
                name_vi=product.name_vi,
                unit_price_vnd=product.price_vnd,
                quantity=qty,
            )
            self.db.add(item)
            order_items.append(item)

        for cart in cart_to_clear:
            self.db.delete(cart)

        discount_vnd = (total * discount_percent) // 100 if discount_percent else 0
        total -= discount_vnd
        if ticket_session is not None:
            ticket_session.entry_used_at = _now()
        order.discount_percent = discount_percent
        order.discount_vnd = discount_vnd
        order.total_vnd = total
        self.db.flush()
        from app.services.redeem_code_service import RedeemCodeService

        RedeemCodeService(self.db).issue_for_order(order, order_items, created_by=user_id)
        self.db.commit()
        self.db.refresh(order)
        for item in order_items:
            self.db.refresh(item)

        if phone_norm and public_code:
            try:
                SmsService().send_order_placed(phone_norm, public_code, total)
            except Exception:
                logger.exception("SMS order confirm failed for %s", public_code)

        return order_to_dict(order, order_items, include_payment_details=True)

    def track_order(self, phone: str, public_code: str) -> dict:
        phone_norm = validate_vn_phone(phone)
        code = (public_code or "").strip().upper()
        if not code.startswith("TAPTOT-"):
            raise NotFoundError("ShopOrder", code)
        row = (
            self.db.query(ShopOrder)
            .filter(ShopOrder.phone == phone_norm, ShopOrder.public_code == code)
            .first()
        )
        if not row:
            raise NotFoundError("ShopOrder", code)
        return self._order_with_items(row, include_payment_details=True)

    def list_orders_by_phone(self, phone: str) -> list[dict]:
        phone_norm = validate_vn_phone(phone)
        rows = (
            self.db.query(ShopOrder)
            .filter(ShopOrder.phone == phone_norm)
            .order_by(ShopOrder.created_at.desc(), ShopOrder.id.desc())
            .limit(30)
            .all()
        )
        return [self._order_with_items(r, include_payment_details=True) for r in rows]

    def list_admin_orders(
        self,
        pagination: PaginationParams,
        *,
        order_status: str | None = None,
    ) -> PaginatedResponse[dict]:
        query = self.db.query(ShopOrder)
        if order_status:
            query = query.filter(ShopOrder.order_status == order_status)
        total = query.count()
        rows = (
            query.order_by(ShopOrder.created_at.desc(), ShopOrder.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            [self._order_with_items(r, include_gift_codes=True) for r in rows],
            total,
            pagination.page,
            pagination.page_size,
        )

    def update_order_status(self, order_id: int, order_status: str) -> dict:
        status = (order_status or "").strip().lower()
        if status == "cancelled":
            return self.cancel_order(order_id)
        if status not in FULFILLMENT_FLOW:
            raise BadRequestError("Trạng thái đơn không hợp lệ")
        query = self.db.query(ShopOrder).filter(ShopOrder.id == order_id)
        if not _is_sqlite(self.db):
            query = query.with_for_update()
        row = query.first()
        if not row:
            raise NotFoundError("ShopOrder", order_id)
        if row.order_status == ORDER_CANCELLED:
            raise BadRequestError("Đơn đã hủy, không đổi trạng thái")
        row.order_status = status
        self.db.commit()
        self.db.refresh(row)
        return self._order_with_items(row, include_gift_codes=True)

    def cancel_order(self, order_id: int) -> dict:
        query = self.db.query(ShopOrder).filter(ShopOrder.id == order_id)
        if not _is_sqlite(self.db):
            query = query.with_for_update()
        row = query.first()
        if not row:
            raise NotFoundError("ShopOrder", order_id)
        if row.order_status not in {ORDER_AWAITING, ORDER_PLACED, "placed"}:
            raise BadRequestError("Chỉ hủy được đơn đang chờ xác nhận")
        items = (
            self.db.query(ShopOrderItem)
            .filter(ShopOrderItem.order_id == row.id)
            .all()
        )
        product_ids = [i.product_id for i in items if i.product_id]
        products: dict[int, ShopProduct] = {}
        if product_ids:
            pquery = self.db.query(ShopProduct).filter(ShopProduct.id.in_(product_ids))
            if not _is_sqlite(self.db):
                pquery = pquery.with_for_update()
            products = {p.id: p for p in pquery.all()}
        for item in items:
            if item.product_id and item.product_id in products:
                product = products[item.product_id]
                product.stock_qty += item.quantity
                product.updated_at = _now()
        row.order_status = ORDER_CANCELLED
        from app.services.redeem_code_service import RedeemCodeService

        RedeemCodeService(self.db).revoke_for_order(row.id)
        self.db.commit()
        self.db.refresh(row)
        return self._order_with_items(row, include_gift_codes=True)

    def payment_config(self) -> dict:
        settings = get_settings()
        return {
            "bank_name": (settings.shop_bank_name or "").strip() or None,
            "bank_bin": (settings.shop_bank_bin or "").strip() or None,
            "account_number": (settings.shop_bank_account or "").strip() or None,
            "account_name": (settings.shop_bank_account_name or "").strip() or None,
            "shipping_fee_vnd": 0,
        }

    def _order_with_items(
        self,
        row: ShopOrder,
        *,
        include_payment_details: bool = False,
        include_gift_codes: bool = False,
    ) -> dict:
        items = (
            self.db.query(ShopOrderItem)
            .filter(ShopOrderItem.order_id == row.id)
            .all()
        )
        gift_codes = None
        if include_gift_codes:
            from app.services.redeem_code_service import RedeemCodeService

            gift_codes = RedeemCodeService(self.db).list_for_order(row.id)
        return order_to_dict(
            row,
            items,
            include_payment_details=include_payment_details,
            gift_codes=gift_codes,
        )
