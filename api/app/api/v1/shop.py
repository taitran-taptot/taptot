from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_admin
from app.core.exceptions import BadRequestError
from app.core.pagination import PaginationParams
from app.services.redeem_code_service import RedeemCodeService
from app.services.shop_service import ShopService

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


class CheckoutIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class CancelOrderIn(BaseModel):
    order_status: str = Field(description="cancelled")


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
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ShopService(db).checkout(user.id, payload.note)


@router.get("/shop/orders")
def list_my_orders(
    pagination: Annotated[PaginationParams, Depends()],
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ShopService(db).list_user_orders(user.id, pagination)


@router.get("/shop/orders/{order_id}")
def get_my_order(
    order_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ShopService(db).get_user_order(user.id, order_id)


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
    _admin: CurrentUser = Depends(require_admin),
):
    return ShopService(db).create_product(payload.model_dump())


@router.patch("/admin/shop/products/{product_id}")
def admin_update_product(
    product_id: int,
    payload: ProductPatch,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
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
    payload: CancelOrderIn,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    if payload.order_status != "cancelled":
        raise BadRequestError("Chỉ hỗ trợ hủy đơn (order_status=cancelled)")
    return ShopService(db).cancel_order(order_id)


@router.get("/shop/redeem-codes/lookup")
def lookup_redeem_code(code: str = Query(min_length=1), db: Session = Depends(get_db)):
    return RedeemCodeService(db).lookup(code)


@router.post("/shop/redeem-codes/batches", status_code=201)
def create_redeem_batch(
    payload: RedeemBatchIn,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_admin),
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
    _admin: CurrentUser = Depends(require_admin),
):
    return RedeemCodeService(db).void_code(code_id)
