"""Admin and collaborator promo dashboards."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, require_admin, require_admin_write, require_ctv
from app.core.pagination import PaginationParams
from app.schemas.auth import _password_has_letter_and_digit
from app.services.auth_service import AuthService
from app.services.collaborator_promo_service import CollaboratorPromoService

router = APIRouter(tags=["Collaborator promo"])


class CreateCollaboratorIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    discount_percent: int = Field(default=10, ge=0, le=100)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _password_has_letter_and_digit(v)


class CollaboratorCodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class UpdateCollaboratorIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    discount_percent: int | None = Field(default=None, ge=0, le=100)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _password_has_letter_and_digit(value)

    @model_validator(mode="after")
    def require_a_change(self) -> "UpdateCollaboratorIn":
        if (
            self.display_name is None
            and self.email is None
            and self.password is None
            and self.discount_percent is None
        ):
            raise ValueError("Cần ít nhất một trường để cập nhật")
        return self


@router.get("/admin/collaborators")
def admin_list_collaborators(
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    return CollaboratorPromoService(db).list_accounts()


@router.post("/admin/collaborators", status_code=201)
def admin_create_collaborator(
    payload: CreateCollaboratorIn,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin_write),
):
    user, promo = AuthService(db).create_collaborator(
        payload.email,
        payload.password,
        payload.display_name,
        payload.discount_percent,
    )
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "code": promo.code,
        "discount_percent": int(promo.discount_percent),
        "order_count": 0,
        "discount_vnd": 0,
    }


@router.patch("/admin/collaborators/{user_id}")
def admin_update_collaborator(
    user_id: str,
    payload: UpdateCollaboratorIn,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin_write),
):
    return CollaboratorPromoService(db).update_account(
        user_id,
        display_name=payload.display_name,
        email=str(payload.email) if payload.email is not None else None,
        password=payload.password,
        discount_percent=payload.discount_percent,
    )


@router.delete("/admin/collaborators/{user_id}", status_code=204)
def admin_delete_collaborator(
    user_id: str,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin_write),
):
    CollaboratorPromoService(db).delete_account(user_id)


@router.post("/admin/collaborators/{user_id}/code", status_code=201)
def admin_create_collaborator_code(
    user_id: str,
    payload: CollaboratorCodeIn,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin_write),
):
    return CollaboratorPromoService(db).assign_code(user_id, payload.code)


@router.get("/admin/collaborators/{user_id}/orders")
def admin_collaborator_orders(
    user_id: str,
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
):
    return CollaboratorPromoService(db).orders_for(user_id, pagination, full=True)


@router.get("/collaborator/promo/stats")
def collaborator_promo_stats(
    pagination: Annotated[PaginationParams, Depends()],
    period: str = Query(min_length=3, max_length=5),
    on: str = Query(min_length=4, max_length=10),
    q: str = Query(default="", max_length=32),
    sort: str = Query(default="desc", pattern="^(asc|desc)$"),
    status: str = Query(default="", max_length=32),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_ctv),
):
    return CollaboratorPromoService(db).period_stats(
        user.id, period, on, pagination, code=q, sort=sort, status=status
    )


@router.get("/collaborator/promo")
def collaborator_promo(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_ctv),
):
    return CollaboratorPromoService(db).own_dashboard(user.id, pagination)
