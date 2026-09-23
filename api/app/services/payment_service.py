"""Checkout (VNPay stub + MoMo 100-day generate) and webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.entities import PaymentEntitlement, PaymentTransaction, Subscription, SubscriptionPlan
from app.services import momo as momo_sign

logger = logging.getLogger(__name__)

PURPOSE_CHALLENGE_GENERATE = "challenge_100_generate"
ENTITLEMENT_TTL = timedelta(hours=24)
MOMO_REQUEST_TYPE = "captureWallet"


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


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
            created_at=_now(),
        )
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)

        settings = get_settings()
        return {
            "transaction_id": txn.id,
            "external_id": external_id,
            "amount_vnd": plan.price_vnd,
            "payment_url": f"{settings.frontend_url}/checkout/{external_id}",
            "provider": "vnpay",
        }

    def create_challenge_checkout(self, user_id: str | None) -> dict[str, Any]:
        settings = get_settings()
        amount = int(settings.ai_generate_price_vnd)
        if amount < 1000:
            raise BadRequestError("Giá tạo lịch chưa được cấu hình.")
        external_id = f"TT-{uuid.uuid4().hex[:12].upper()}"
        extra = momo_sign.extra_data_encode({"purpose": PURPOSE_CHALLENGE_GENERATE})
        txn = PaymentTransaction(
            user_id=user_id,
            amount_vnd=amount,
            currency="VND",
            status="pending",
            payment_provider="momo",
            external_id=external_id,
            description="Lộ trình 100 ngày TAPTOT",
            transaction_metadata={
                "purpose": PURPOSE_CHALLENGE_GENERATE,
                "stub": not settings.momo_configured,
            },
            created_at=_now(),
        )
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)

        if not settings.momo_configured:
            if settings.app_env.lower() in {"production", "prod"} or not settings.debug:
                raise BadRequestError("MoMo chưa được cấu hình.")
            pay_url = f"{settings.frontend_url.rstrip('/')}/batdau?paid={external_id}&stub=1"
            return {
                "transaction_id": txn.id,
                "external_id": external_id,
                "amount_vnd": amount,
                "pay_url": pay_url,
                "provider": "momo",
                "stub": True,
            }

        request_id = f"{external_id}-{uuid.uuid4().hex[:8]}"
        redirect_url = f"{settings.frontend_url.rstrip('/')}/batdau"
        ipn_url = (settings.momo_ipn_url or "").strip() or f"{_api_public_base()}/payments/webhook/momo"
        order_info = "Lo trinh 100 ngay TAPTOT"
        fields = {
            "accessKey": settings.momo_access_key,
            "amount": str(amount),
            "extraData": extra,
            "ipnUrl": ipn_url,
            "orderId": external_id,
            "orderInfo": order_info,
            "partnerCode": settings.momo_partner_code,
            "redirectUrl": redirect_url,
            "requestId": request_id,
            "requestType": MOMO_REQUEST_TYPE,
        }
        payload = {
            **fields,
            "partnerName": "TAPTOT",
            "storeId": "TAPTOT",
            "lang": "vi",
            "autoCapture": True,
            "signature": momo_sign.sign_create(settings.momo_secret_key, fields),
        }
        try:
            with httpx.Client(timeout=20) as client:
                response = client.post(settings.momo_endpoint, json=payload)
            body = response.json()
        except Exception as exc:
            txn.status = "failed"
            self.db.commit()
            logger.exception("MoMo create failed for %s", external_id)
            raise BadRequestError("Không kết nối được MoMo. Thử lại sau.") from exc

        result_code = body.get("resultCode")
        pay_url = body.get("payUrl") or body.get("deeplink") or ""
        if response.status_code >= 400 or result_code not in (0, "0") or not pay_url:
            txn.status = "failed"
            meta = dict(txn.transaction_metadata or {})
            meta["momo_error"] = body
            txn.transaction_metadata = meta
            self.db.commit()
            message = body.get("message") or "MoMo từ chối thanh toán."
            raise BadRequestError(str(message))

        meta = dict(txn.transaction_metadata or {})
        meta["request_id"] = request_id
        txn.transaction_metadata = meta
        self.db.commit()
        return {
            "transaction_id": txn.id,
            "external_id": external_id,
            "amount_vnd": amount,
            "pay_url": pay_url,
            "provider": "momo",
            "stub": False,
        }

    def challenge_status(self, external_id: str) -> dict[str, Any]:
        txn = self._txn_by_external(external_id)
        if txn is None:
            raise NotFoundError("PaymentTransaction", external_id)
        meta = txn.transaction_metadata or {}
        if meta.get("purpose") != PURPOSE_CHALLENGE_GENERATE:
            raise NotFoundError("PaymentTransaction", external_id)
        entitlement = self._entitlement_for_txn(txn.id)
        token = None
        consumed = False
        if entitlement:
            consumed = entitlement.consumed_at is not None and entitlement.plan_id is not None
            if entitlement.consumed_at is None or entitlement.plan_id is None:
                if _aware(entitlement.expires_at) and _aware(entitlement.expires_at) >= _now():
                    token = entitlement.token
                if entitlement.consumed_at is not None and entitlement.plan_id is None:
                    token = entitlement.token
        return {
            "external_id": txn.external_id,
            "status": txn.status,
            "amount_vnd": txn.amount_vnd,
            "stub": bool(meta.get("stub")),
            "entitlement_token": token if txn.status == "completed" else None,
            "consumed": consumed,
        }

    def simulate_challenge_success(self, external_id: str) -> dict[str, Any]:
        settings = get_settings()
        if settings.app_env.lower() in {"production", "prod"} or not settings.debug:
            raise BadRequestError("Giả lập thanh toán chỉ dùng khi debug.")
        txn = self._txn_by_external(external_id)
        if txn is None:
            raise NotFoundError("PaymentTransaction", external_id)
        meta = txn.transaction_metadata or {}
        if meta.get("purpose") != PURPOSE_CHALLENGE_GENERATE:
            raise BadRequestError("Không phải giao dịch lộ trình 100 ngày.")
        self._complete_challenge(txn)
        self.db.commit()
        return self.challenge_status(external_id)

    def handle_webhook(self, provider: str, payload: dict, signature: str | None = None) -> dict:
        provider = (provider or "").strip().lower()
        if provider == "manual":
            if get_settings().app_env.lower() in {"production", "prod"} or not get_settings().debug:
                raise BadRequestError("Manual payment provider is disabled")
            return self._handle_vnpay({**payload, "status": "success"}, None)
        if provider == "vnpay":
            return self._handle_vnpay(payload, signature)
        if provider == "momo":
            return self._handle_momo(payload)
        raise BadRequestError(f"Unsupported payment provider: {provider}")

    def lock_entitlement(self, token: str | None) -> bool:
        raw = (token or "").strip()
        if not raw:
            return False
        now = _now()
        row = (
            self.db.query(PaymentEntitlement)
            .filter(
                PaymentEntitlement.token == raw,
                PaymentEntitlement.consumed_at.is_(None),
            )
            .first()
        )
        if row is None:
            return False
        expires = _aware(row.expires_at)
        if expires is None or expires < now:
            return False
        row.consumed_at = now
        self.db.commit()
        return True

    def bind_entitlement_plan(self, token: str | None, plan_id: int) -> bool:
        raw = (token or "").strip()
        if not raw or not plan_id:
            return False
        updated = (
            self.db.query(PaymentEntitlement)
            .filter(
                PaymentEntitlement.token == raw,
                PaymentEntitlement.plan_id.is_(None),
            )
            .update({"plan_id": int(plan_id)}, synchronize_session=False)
        )
        self.db.commit()
        return updated == 1

    def release_entitlement(self, token: str | None) -> None:
        raw = (token or "").strip()
        if not raw:
            return
        (
            self.db.query(PaymentEntitlement)
            .filter(
                PaymentEntitlement.token == raw,
                PaymentEntitlement.plan_id.is_(None),
            )
            .update({"consumed_at": None}, synchronize_session=False)
        )
        self.db.commit()

    def _handle_vnpay(self, payload: dict, signature: str | None) -> dict:
        secret = get_settings().payment_webhook_secret
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
        elif get_settings().app_env.lower() in {"production", "prod"}:
            raise BadRequestError("PAYMENT_WEBHOOK_SECRET is required in production")

        external_id = payload.get("external_id") or payload.get("vnp_TxnRef")
        txn = self._txn_by_external(str(external_id or ""))
        if not txn:
            raise NotFoundError("PaymentTransaction", external_id or "unknown")

        if payload.get("status") in ("success", "00"):
            meta = txn.transaction_metadata or {}
            if meta.get("purpose") == PURPOSE_CHALLENGE_GENERATE:
                self._complete_challenge(txn)
            else:
                txn.status = "completed"
                txn.completed_at = _now()
                self._activate_subscription(txn)
        else:
            txn.status = "failed"

        self.db.commit()
        return {"transaction_id": txn.id, "status": txn.status}

    def _handle_momo(self, payload: dict) -> dict:
        settings = get_settings()
        if not settings.momo_configured:
            raise BadRequestError("MoMo chưa được cấu hình.")
        fields = {key: payload.get(key, "") for key in momo_sign.IPN_SIGN_KEYS}
        fields["accessKey"] = settings.momo_access_key
        if not momo_sign.signature_matches(
            settings.momo_secret_key,
            momo_sign.IPN_SIGN_KEYS,
            fields,
            str(payload.get("signature") or ""),
        ):
            raise BadRequestError("Chữ ký MoMo không hợp lệ.")
        external_id = str(payload.get("orderId") or "")
        txn = self._txn_by_external(external_id)
        if not txn:
            raise NotFoundError("PaymentTransaction", external_id or "unknown")
        result_code = payload.get("resultCode")
        if result_code in (0, "0"):
            self._complete_challenge(txn)
        else:
            txn.status = "failed"
        self.db.commit()
        return {"transaction_id": txn.id, "status": txn.status}

    def _complete_challenge(self, txn: PaymentTransaction) -> None:
        if txn.status == "completed" and self._entitlement_for_txn(txn.id):
            return
        txn.status = "completed"
        txn.completed_at = _now()
        if self._entitlement_for_txn(txn.id):
            return
        now = _now()
        row = PaymentEntitlement(
            token=secrets.token_urlsafe(24),
            transaction_id=txn.id,
            purpose=PURPOSE_CHALLENGE_GENERATE,
            created_at=now,
            expires_at=now + ENTITLEMENT_TTL,
        )
        self.db.add(row)

    def _entitlement_for_txn(self, txn_id: int) -> PaymentEntitlement | None:
        return (
            self.db.query(PaymentEntitlement)
            .filter(PaymentEntitlement.transaction_id == txn_id)
            .order_by(PaymentEntitlement.id.desc())
            .first()
        )

    def _txn_by_external(self, external_id: str) -> PaymentTransaction | None:
        token = (external_id or "").strip()
        if not token:
            return None
        return (
            self.db.query(PaymentTransaction)
            .filter(PaymentTransaction.external_id == token)
            .first()
        )

    def _activate_subscription(self, txn: PaymentTransaction) -> None:
        meta = txn.transaction_metadata or {}
        plan_id = meta.get("plan_id")
        if not plan_id or not txn.user_id:
            return

        plan = self.db.get(SubscriptionPlan, plan_id)
        if not plan:
            return

        expires = _now() + timedelta(days=30 if plan.billing_period == "monthly" else 365)
        sub = Subscription(
            user_id=txn.user_id,
            plan_id=plan_id,
            status="active",
            started_at=_now(),
            expires_at=expires,
            payment_provider=txn.payment_provider,
            external_id=txn.external_id,
        )
        self.db.add(sub)
        txn.subscription_id = sub.id


def _api_public_base() -> str:
    settings = get_settings()
    prefix = (settings.api_v1_prefix or "/api/v1").rstrip("/")
    media = (settings.media_base_url or "").rstrip("/")
    if media.endswith("/media"):
        origin = media[: -len("/media")]
        if origin:
            return f"{origin}{prefix}"
    # Local default: API on :8000 when frontend is :3000.
    frontend = (settings.frontend_url or "http://localhost:3000").rstrip("/")
    if frontend.endswith(":3000"):
        return frontend[:-5] + ":8000" + prefix
    return f"{frontend}{prefix}"
