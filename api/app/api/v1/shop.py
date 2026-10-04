from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    CurrentUser,
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_admin_write,
)
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import PaginationParams
from app.services.redeem_code_service import RedeemCodeService
from app.services.shop_service import PAYMENT_BANK, PAYMENT_COD, ShopService

router = APIRouter(tags=["Shop"])


class ProductIn(BaseModel):
    name_vi: str = Field(min_length=2, max_length=255)
    description_vi: str | None = None
    price_vnd: int = Field(ge=0)
    stock_qty: int = Field(default=0, ge=0)
    image_url: str | None = None
    slug: str | None = Field(default=None, max_length=150)
    is_active: bool = True


class ProductPatch(BaseModel):
    name_vi: str | None = Field(default=None, min_length=2, max_length=255)
    description_vi: str | None = None
    price_vnd: int | None = Field(default=None, ge=0)
    stock_qty: int | None = Field(default=None, ge=0)
    image_url: str | None = None
    slug: str | None = Field(default=None, max_length=150)
    is_active: bool | None = None


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


class CartQtyIn(BaseModel):
    quantity: int = Field(ge=0)


class CartMergeIn(BaseModel):
    items: list[CartItemIn] = Field(default_factory=list)


class CheckoutItemIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class CheckoutIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    recipient_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    province_code: str | None = Field(default=None, max_length=20)
    province_name: str | None = Field(default=None, max_length=120)
    district_code: str | None = Field(default=None, max_length=20)
    district_name: str | None = Field(default=None, max_length=120)
    ward_code: str | None = Field(default=None, max_length=20)
    ward_name: str | None = Field(default=None, max_length=120)
    address_line: str | None = Field(default=None, max_length=500)
    payment_method: Literal["cod", "bank_transfer"] | None = None
    items: list[CheckoutItemIn] | None = None
    pushup_ticket: str | None = Field(default=None, max_length=4000)


class TrackOrderIn(BaseModel):
    phone: str = Field(min_length=1, max_length=20)
    public_code: str | None = Field(default=None, max_length=32)

    @field_validator("public_code", mode="before")
    @classmethod
    def upper_code(cls, v: str | None) -> str | None:
        code = (v or "").strip().upper()
        return code or None


class AdminOrderPatch(BaseModel):
    order_status: str | None = None


class RedeemBatchIn(BaseModel):
    product_id: int | None = None
    qty: int = Field(ge=1, le=200)
    note: str | None = Field(default=None, max_length=200)


@router.get("/shop/products")
def list_shop_products(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
):
    return ShopService(db).list_public_products(pagination)


@router.get("/shop/products/{product_id}")
def get_shop_product(product_id: int, db: Session = Depends(get_db)):
    return ShopService(db).get_public_product(product_id)


@router.get("/shop/payment-info")
def shop_payment_info(db: Session = Depends(get_db)):
    return ShopService(db).payment_config()


@router.get("/shop/cart")
def get_cart(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ShopService(db).get_cart(user.id)


@router.post("/shop/cart/items")
def add_cart_item(
    payload: CartItemIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ShopService(db).add_to_cart(user.id, payload.product_id, payload.quantity)


@router.post("/shop/cart/merge")
def merge_cart(
    payload: CartMergeIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ShopService(db).merge_cart(
        user.id, [i.model_dump() for i in payload.items]
    )


@router.patch("/shop/cart/items/{product_id}")
def set_cart_item(
    product_id: int,
    payload: CartQtyIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ShopService(db).set_cart_item(user.id, product_id, payload.quantity)


@router.delete("/shop/cart/items/{product_id}")
def remove_cart_item(
    product_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ShopService(db).set_cart_item(user.id, product_id, 0)


@router.post("/shop/orders", status_code=201)
def checkout(
    payload: CheckoutIn,
    request: Request,
    user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    _ = request  # reserved for future IP logging
    data = payload.model_dump()
    items = data.pop("items", None)
    note = data.pop("note", None)
    return ShopService(db).checkout(
        user.id if user else None,
        note,
        items=items,
        **data,
    )


@router.post("/shop/orders/track")
def track_order(payload: TrackOrderIn, db: Session = Depends(get_db)):
    service = ShopService(db)
    if payload.public_code:
        return service.track_order(payload.phone, payload.public_code)
    return {"items": service.list_orders_by_phone(payload.phone)}


@router.get("/admin/shop/products")
def admin_list_products(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
    q: str | None = Query(default=None),
    is_active: bool | None = None,
):
    return ShopService(db).list_admin_products(pagination, q=q, is_active=is_active)


@router.post("/admin/shop/products", status_code=201)
def admin_create_product(
    payload: ProductIn,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin_write),
):
    return ShopService(db).create_product(payload.model_dump())


@router.patch("/admin/shop/products/{product_id}")
def admin_update_product(
    product_id: int,
    payload: ProductPatch,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin_write),
):
    return ShopService(db).update_product(product_id, payload.model_dump(exclude_unset=True))


@router.get("/admin/shop/orders")
def admin_list_orders(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
    order_status: str | None = Query(default=None),
):
    return ShopService(db).list_admin_orders(pagination, order_status=order_status)


@router.patch("/admin/shop/orders/{order_id}")
def admin_update_order(
    order_id: int,
    payload: AdminOrderPatch,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin_write),
):
    service = ShopService(db)
    if payload.order_status:
        return service.update_order_status(order_id, payload.order_status)
    raise BadRequestError("Cần order_status")


@router.get("/admin/shop/orders/{order_id}/activation-covers.pdf")
def admin_order_activation_covers(
    order_id: int,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    from app.models.entities import ShopOrder
    from app.services.activation_cover import covers_pdf_bytes

    order = db.get(ShopOrder, order_id)
    if not order:
        raise NotFoundError("ShopOrder", order_id)
    codes = RedeemCodeService(db).list_for_order(order_id)
    slugs = [str(c["code"]) for c in codes if c.get("code")]
    if not slugs:
        raise NotFoundError("ProductRedeemCode", order_id)
    slug = order.public_code or str(order_id)
    return Response(
        content=covers_pdf_bytes(slugs),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="bia-{slug}.pdf"'},
    )


@router.get("/admin/shop/redeem-codes/{code_id}/cover.png")
def admin_redeem_cover(
    code_id: int,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    from app.models.entities import ProductRedeemCode
    from app.services.activation_cover import cover_png_bytes

    row = db.get(ProductRedeemCode, code_id)
    if not row:
        raise NotFoundError("ProductRedeemCode", code_id)
    return Response(
        content=cover_png_bytes(row.code),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="bia-{row.code}.png"'},
    )


@router.get("/shop/redeem-codes/lookup")
def lookup_redeem_code(code: str = Query(min_length=1), db: Session = Depends(get_db)):
    return RedeemCodeService(db).lookup(code)


@router.post("/shop/redeem-codes/batches", status_code=201)
def create_redeem_batch(
    payload: RedeemBatchIn,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_admin_write),
):
    return RedeemCodeService(db).create_batch(
        admin_user_id=admin.id,
        qty=payload.qty,
        product_id=payload.product_id,
        note=payload.note,
    )


@router.get("/shop/redeem-codes/batches")
def list_redeem_batches(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    return RedeemCodeService(db).list_batches(pagination)


@router.get("/shop/redeem-codes/batches/{batch_id}/print", response_class=HTMLResponse)
def print_redeem_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    return HTMLResponse(RedeemCodeService(db).print_html(batch_id))


@router.get("/shop/redeem-codes")
def list_redeem_codes(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
    batch_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    include_qr: bool = Query(default=False),
):
    return RedeemCodeService(db).list_codes(
        pagination,
        batch_id=batch_id,
        product_id=product_id,
        status=status,
        include_qr=include_qr,
    )


@router.post("/shop/redeem-codes/{code_id}/void")
def void_redeem_code(
    code_id: int,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin_write),
):
    return RedeemCodeService(db).void_code(code_id)


# Silence unused import warnings for payment constants re-export if needed
_ = (PAYMENT_BANK, PAYMENT_COD)
