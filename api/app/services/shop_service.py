from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import ShopCartItem, ShopOrder, ShopOrderItem, ShopProduct
from app.services.slug import unique_slug

ORDER_PLACED = "placed"
ORDER_CANCELLED = "cancelled"


def _now() -> datetime:
    return datetime.now(UTC)


def _is_sqlite(db: Session) -> bool:
    bind = db.get_bind()
    return bool(bind is not None and bind.dialect.name == "sqlite")


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


def order_to_dict(row: ShopOrder, items: list[ShopOrderItem] | None = None) -> dict:
    payload = {
        "id": row.id,
        "user_id": str(row.user_id),
        "order_status": row.order_status,
        "total_vnd": row.total_vnd,
        "note": row.note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    if items is not None:
        payload["items"] = [order_item_to_dict(i) for i in items]
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
            raise ConflictError(
                f"Chỉ còn {product.stock_qty} sản phẩm trong kho"
            )
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

    def checkout(self, user_id: str, note: str | None = None) -> dict:
        cart_rows = (
            self.db.query(ShopCartItem)
            .filter(ShopCartItem.user_id == user_id)
            .all()
        )
        if not cart_rows:
            raise BadRequestError("Giỏ hàng trống")

        product_ids = [r.product_id for r in cart_rows]
        query = self.db.query(ShopProduct).filter(ShopProduct.id.in_(product_ids))
        if not _is_sqlite(self.db):
            query = query.with_for_update()
        products = {p.id: p for p in query.all()}

        shortages: list[str] = []
        lines: list[tuple[ShopCartItem, ShopProduct]] = []
        for cart in cart_rows:
            product = products.get(cart.product_id)
            if not product or not product.is_active:
                shortages.append("Một sản phẩm không còn bán")
                continue
            if cart.quantity > product.stock_qty:
                shortages.append(
                    f"{product.name_vi}: chỉ còn {product.stock_qty}"
                )
                continue
            lines.append((cart, product))
        if shortages:
            raise ConflictError("; ".join(shortages))
        if not lines:
            raise BadRequestError("Giỏ hàng không hợp lệ")

        total = 0
        order = ShopOrder(
            user_id=user_id,
            order_status=ORDER_PLACED,
            total_vnd=0,
            note=(note or "").strip() or None,
            created_at=_now(),
        )
        self.db.add(order)
        self.db.flush()

        items: list[ShopOrderItem] = []
        for cart, product in lines:
            product.stock_qty -= cart.quantity
            product.updated_at = _now()
            line_total = product.price_vnd * cart.quantity
            total += line_total
            item = ShopOrderItem(
                order_id=order.id,
                product_id=product.id,
                name_vi=product.name_vi,
                unit_price_vnd=product.price_vnd,
                quantity=cart.quantity,
            )
            self.db.add(item)
            items.append(item)
            self.db.delete(cart)

        order.total_vnd = total
        self.db.commit()
        self.db.refresh(order)
        for item in items:
            self.db.refresh(item)
        return order_to_dict(order, items)

    def list_user_orders(
        self, user_id: str, pagination: PaginationParams
    ) -> PaginatedResponse[dict]:
        query = self.db.query(ShopOrder).filter(ShopOrder.user_id == user_id)
        total = query.count()
        rows = (
            query.order_by(ShopOrder.created_at.desc(), ShopOrder.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            [self._order_with_items(r) for r in rows],
            total,
            pagination.page,
            pagination.page_size,
        )

    def get_user_order(self, user_id: str, order_id: int) -> dict:
        row = self.db.get(ShopOrder, order_id)
        if not row or str(row.user_id) != str(user_id):
            raise NotFoundError("ShopOrder", order_id)
        return self._order_with_items(row)

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
            [self._order_with_items(r) for r in rows],
            total,
            pagination.page,
            pagination.page_size,
        )

    def cancel_order(self, order_id: int) -> dict:
        query = self.db.query(ShopOrder).filter(ShopOrder.id == order_id)
        if not _is_sqlite(self.db):
            query = query.with_for_update()
        row = query.first()
        if not row:
            raise NotFoundError("ShopOrder", order_id)
        if row.order_status != ORDER_PLACED:
            raise BadRequestError("Chỉ hủy được đơn đang chờ xử lý")
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
        self.db.commit()
        self.db.refresh(row)
        return self._order_with_items(row)

    def _order_with_items(self, row: ShopOrder) -> dict:
        items = (
            self.db.query(ShopOrderItem)
            .filter(ShopOrderItem.order_id == row.id)
            .all()
        )
        return order_to_dict(row, items)
