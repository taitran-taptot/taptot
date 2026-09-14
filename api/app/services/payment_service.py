import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.entities import PaymentTransaction, Subscription, SubscriptionPlan

settings = get_settings()


class PaymentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_checkout(self, user_id: str, plan_slug: str) -> dict:
        plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.slug == plan_slug).first()
        if not plan or not plan.is_active:
            raise NotFoundError("SubscriptionPlan", plan_slug)

        external_id = f"VF-{uuid.uuid4().hex[:12].upper()}"
        txn = PaymentTransaction(
            user_id=user_id,
            amount_vnd=plan.price_vnd,
            currency="VND",
            status="pending",
            payment_provider="vnpay",
            external_id=external_id,
            description=f"Đăng ký {plan.name_vi}",
            transaction_metadata={"plan_slug": plan_slug, "plan_id": plan.id},
            created_at=datetime.now(UTC),
        )
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)

        return {
            "transaction_id": txn.id,
            "external_id": external_id,
            "amount_vnd": plan.price_vnd,
            "payment_url": f"{settings.frontend_url}/checkout/{external_id}",
            "provider": "vnpay",
        }

    def handle_webhook(self, provider: str, payload: dict, signature: str | None = None) -> dict:
        if provider == "manual":
            # Only allowed in local debug — never in production
            if settings.app_env.lower() in {"production", "prod"} or not settings.debug:
                raise BadRequestError("Manual payment provider is disabled")
            return self._handle_vnpay({**payload, "status": "success"}, None)
        if provider == "vnpay":
            return self._handle_vnpay(payload, signature)
        raise BadRequestError(f"Unsupported payment provider: {provider}")

    def _handle_vnpay(self, payload: dict, signature: str | None) -> dict:
        secret = settings.payment_webhook_secret
        if secret:
            if not signature:
                raise BadRequestError("Missing webhook signature")
            expected = hmac.new(
                secret.encode(),
                str(payload.get("external_id", "")).encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise BadRequestError("Invalid webhook signature")
        elif settings.app_env.lower() in {"production", "prod"}:
            raise BadRequestError("PAYMENT_WEBHOOK_SECRET is required in production")

        external_id = payload.get("external_id") or payload.get("vnp_TxnRef")
        txn = (
            self.db.query(PaymentTransaction)
            .filter(PaymentTransaction.external_id == external_id)
            .first()
        )
        if not txn:
            raise NotFoundError("PaymentTransaction", external_id or "unknown")

        if payload.get("status") in ("success", "00"):
            txn.status = "completed"
            txn.completed_at = datetime.now(UTC)
            self._activate_subscription(txn)
        else:
            txn.status = "failed"

        self.db.commit()
        return {"transaction_id": txn.id, "status": txn.status}

    def _activate_subscription(self, txn: PaymentTransaction) -> None:
        meta = txn.transaction_metadata or {}
        plan_id = meta.get("plan_id")
        if not plan_id:
            return

        plan = self.db.get(SubscriptionPlan, plan_id)
        if not plan:
            return

        expires = datetime.now(UTC) + timedelta(days=30 if plan.billing_period == "monthly" else 365)
        sub = Subscription(
            user_id=txn.user_id,
            plan_id=plan_id,
            status="active",
            started_at=datetime.now(UTC),
            expires_at=expires,
            payment_provider=txn.payment_provider,
            external_id=txn.external_id,
        )
        self.db.add(sub)
        txn.subscription_id = sub.id
