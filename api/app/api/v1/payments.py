from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user_optional
from app.core.exceptions import BadRequestError
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/challenge-checkout")
def challenge_checkout(
    user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    return PaymentService(db).create_challenge_checkout(user.id if user else None)


@router.get("/challenge/{external_id}")
def challenge_status(external_id: str, db: Session = Depends(get_db)):
    return PaymentService(db).challenge_status(external_id)


@router.post("/challenge/{external_id}/simulate")
def challenge_simulate(external_id: str, db: Session = Depends(get_db)):
    return PaymentService(db).simulate_challenge_success(external_id)


@router.post("/webhook/{provider}")
async def webhook(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
):
    try:
        payload = await request.json()
    except Exception as exc:
        raise BadRequestError("Webhook body phải là JSON.") from exc
    if not isinstance(payload, dict):
        raise BadRequestError("Webhook body phải là JSON object.")
    return PaymentService(db).handle_webhook(provider, payload, x_signature)
