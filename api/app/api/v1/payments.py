from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


class CheckoutRequest(BaseModel):
    plan_slug: str


@router.post("/checkout")
def checkout(payload: CheckoutRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return PaymentService(db).create_checkout(user.id, payload.plan_slug)


@router.post("/webhook/{provider}")
def webhook(
    provider: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
):
    return PaymentService(db).handle_webhook(provider, payload, x_signature)
