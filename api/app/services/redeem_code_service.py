"""One-time gift codes printed on product stickers (QR + text)."""

from __future__ import annotations

import html
import io
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import (
    ProductRedeemBatch,
    ProductRedeemCode,
    ShopProduct,
    UserDailyPlan,
)

STATUS_UNUSED = "unused"
STATUS_PROCESSING = "processing"
STATUS_REDEEMED = "redeemed"
STATUS_VOID = "void"
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_BODY_LEN = 8
MAX_BATCH_QTY = 200
RESERVATION_TTL = timedelta(minutes=30)


def _now() -> datetime:
    return datetime.now(UTC)


def _reservation_active(row: ProductRedeemCode) -> bool:
    if not row.reservation_token or not row.reserved_at:
        return False
    reserved_at = row.reserved_at
    if reserved_at.tzinfo is None:
        reserved_at = reserved_at.replace(tzinfo=UTC)
    return reserved_at >= _now() - RESERVATION_TTL


def normalize_code(raw: str | None) -> str | None:
    """Accept TT-7K3M-P2QX or tt7k3mp2qx. Return canonical form or None."""
    compact = re.sub(r"[^A-Za-z0-9]", "", str(raw or "")).upper()
    if compact.startswith("TT"):
        compact = compact[2:]
    if len(compact) != CODE_BODY_LEN:
        return None
    if any(ch not in CODE_ALPHABET for ch in compact):
        return None
    return f"TT-{compact[:4]}-{compact[4:]}"


def new_code() -> str:
    body = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_BODY_LEN))
    return f"TT-{body[:4]}-{body[4:]}"


def gift_landing_url(code: str) -> str:
    base = (get_settings().frontend_url or "http://localhost:3000").rstrip("/")
    return f"{base}/qua-tang?code={code}"


def qr_png_data_uri(payload: str) -> str:
    import base64

    import qrcode

    img = qrcode.make(payload, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class RedeemCodeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def lookup(self, raw: str | None) -> dict[str, Any]:
        code = normalize_code(raw)
        if not code:
            return {"valid": False, "status": "invalid", "product_name_vi": None, "code": None}
        row = (
            self.db.query(ProductRedeemCode)
            .filter(ProductRedeemCode.code == code)
            .first()
        )
        if row is None:
            return {"valid": False, "status": "invalid", "product_name_vi": None, "code": code}
        product_name = None
        batch = self.db.get(ProductRedeemBatch, row.batch_id)
        if batch and batch.product_id:
            product = self.db.get(ShopProduct, batch.product_id)
            if product:
                product_name = product.name_vi
        processing = row.status == STATUS_UNUSED and _reservation_active(row)
        unused = row.status == STATUS_UNUSED and not processing
        return {
            "valid": unused,
            "status": STATUS_PROCESSING if processing else row.status,
            "product_name_vi": product_name,
            "code": code,
        }

    def create_batch(
        self,
        *,
        admin_user_id: str,
        qty: int,
        product_id: int | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        if qty < 1 or qty > MAX_BATCH_QTY:
            raise BadRequestError(f"Số lượng mã từ 1 đến {MAX_BATCH_QTY}.")
        if product_id is not None:
            product = self.db.get(ShopProduct, int(product_id))
            if product is None:
                raise NotFoundError("ShopProduct", product_id)
        batch = ProductRedeemBatch(
            product_id=product_id,
            qty=qty,
            note=(note or "").strip() or None,
            created_by=admin_user_id,
            created_at=_now(),
        )
        self.db.add(batch)
        self.db.flush()
        existing = {c for (c,) in self.db.query(ProductRedeemCode.code).all()}
        created: list[ProductRedeemCode] = []
        while len(created) < qty:
            candidate = new_code()
            if candidate in existing:
                continue
            existing.add(candidate)
            row = ProductRedeemCode(
                batch_id=batch.id,
                code=candidate,
                status=STATUS_UNUSED,
            )
            self.db.add(row)
            created.append(row)
        self.db.commit()
        self.db.refresh(batch)
        return self.batch_to_dict(batch, codes=created)

    def list_codes(
        self,
        pagination: PaginationParams,
        *,
        batch_id: int | None = None,
        product_id: int | None = None,
        status: str | None = None,
        include_qr: bool = False,
    ) -> PaginatedResponse[dict]:
        query = self.db.query(ProductRedeemCode)
        if batch_id is not None:
            query = query.filter(ProductRedeemCode.batch_id == int(batch_id))
        if status:
            query = query.filter(ProductRedeemCode.status == status)
        if product_id is not None:
            query = query.join(
                ProductRedeemBatch,
                ProductRedeemBatch.id == ProductRedeemCode.batch_id,
            ).filter(ProductRedeemBatch.product_id == int(product_id))
        total = query.count()
        rows = (
            query.order_by(ProductRedeemCode.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            [self.code_to_dict(r, include_qr=include_qr) for r in rows],
            total,
            pagination.page,
            pagination.page_size,
        )

    def list_batches(self, pagination: PaginationParams) -> PaginatedResponse[dict]:
        query = self.db.query(ProductRedeemBatch)
        total = query.count()
        rows = (
            query.order_by(ProductRedeemBatch.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            [self.batch_to_dict(r) for r in rows],
            total,
            pagination.page,
            pagination.page_size,
        )

    def void_code(self, code_id: int) -> dict[str, Any]:
        row = self.db.get(ProductRedeemCode, int(code_id))
        if row is None:
            raise NotFoundError("ProductRedeemCode", code_id)
        if row.status != STATUS_UNUSED or _reservation_active(row):
            raise BadRequestError("Chỉ hủy được mã chưa dùng.")
        row.status = STATUS_VOID
        self.db.commit()
        self.db.refresh(row)
        return self.code_to_dict(row)

    def reserve(self, raw: str | None) -> str | None:
        """Atomically reserve one unused code while a plan is being generated."""
        code = normalize_code(raw)
        if not code:
            return None
        now = _now()
        token = secrets.token_urlsafe(24)
        updated = (
            self.db.query(ProductRedeemCode)
            .filter(
                ProductRedeemCode.code == code,
                ProductRedeemCode.status == STATUS_UNUSED,
                or_(
                    ProductRedeemCode.reservation_token.is_(None),
                    ProductRedeemCode.reserved_at.is_(None),
                    ProductRedeemCode.reserved_at < now - RESERVATION_TTL,
                ),
            )
            .update(
                {
                    "reservation_token": token,
                    "reserved_at": now,
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        return token if updated == 1 else None

    def release(self, raw: str | None, reservation_token: str) -> bool:
        """Release this caller's reservation after generation fails."""
        code = normalize_code(raw)
        if not code or not reservation_token:
            return False
        updated = (
            self.db.query(ProductRedeemCode)
            .filter(
                ProductRedeemCode.code == code,
                ProductRedeemCode.status == STATUS_UNUSED,
                ProductRedeemCode.reservation_token == reservation_token,
            )
            .update(
                {
                    "reservation_token": None,
                    "reserved_at": None,
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        return updated == 1

    def complete(
        self,
        raw: str | None,
        reservation_token: str,
        *,
        plan_id: int,
        user_id: str | None,
    ) -> bool:
        """Consume a code only when the matching generation has succeeded."""
        code = normalize_code(raw)
        if not code or not reservation_token or not plan_id:
            return False
        updated = (
            self.db.query(ProductRedeemCode)
            .filter(
                ProductRedeemCode.code == code,
                ProductRedeemCode.status == STATUS_UNUSED,
                ProductRedeemCode.reservation_token == reservation_token,
            )
            .update(
                {
                    "status": STATUS_REDEEMED,
                    "reservation_token": None,
                    "reserved_at": None,
                    "redeemed_at": _now(),
                    "plan_id": int(plan_id),
                    "redeemed_user_id": user_id,
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        return updated == 1

    def try_redeem(
        self,
        raw: str | None,
        *,
        plan_id: int | None,
        user_id: str | None,
    ) -> bool:
        """Compatibility helper for admin/tests: reserve and immediately consume."""
        if not plan_id:
            return False
        reservation_token = self.reserve(raw)
        if not reservation_token:
            return False
        return self.complete(
            raw,
            reservation_token,
            plan_id=int(plan_id),
            user_id=user_id,
        )

    def print_html(self, batch_id: int) -> str:
        batch = self.db.get(ProductRedeemBatch, int(batch_id))
        if batch is None:
            raise NotFoundError("ProductRedeemBatch", batch_id)
        rows = (
            self.db.query(ProductRedeemCode)
            .filter(ProductRedeemCode.batch_id == batch.id)
            .order_by(ProductRedeemCode.id.asc())
            .all()
        )
        product_name = ""
        if batch.product_id:
            product = self.db.get(ShopProduct, batch.product_id)
            if product:
                product_name = product.name_vi or ""
        cards = []
        for row in rows:
            url = gift_landing_url(row.code)
            uri = qr_png_data_uri(url)
            name_html = html.escape(product_name) if product_name else "TAPTOT"
            code_html = html.escape(row.code)
            cards.append(
                "<article class='label'>"
                f"<p class='brand'>TAPTOT</p>"
                f"<p class='product'>{name_html}</p>"
                f"<img src='{uri}' alt='QR {code_html}' />"
                f"<p class='code'>{code_html}</p>"
                "<p class='hint'>Quét QR hoặc nhập mã · dùng 1 lần</p>"
                "</article>"
            )
        note = html.escape(batch.note or f"Lô #{batch.id}")
        return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <title>Tem mã TAPTOT — {note}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: "Be Vietnam Pro", Arial, sans-serif; margin: 12px; color: #0f172a; }}
    h1 {{ font-size: 14px; margin: 0 0 12px; }}
    .sheet {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
    .label {{
      border: 1px solid #cbd5e1; border-radius: 10px; padding: 10px 8px 8px;
      text-align: center; break-inside: avoid; page-break-inside: avoid;
    }}
    .brand {{ font-weight: 800; letter-spacing: 0.08em; margin: 0; font-size: 13px; color: #16a34a; }}
    .product {{ margin: 2px 0 6px; font-size: 11px; color: #64748b; }}
    img {{ width: 112px; height: 112px; }}
    .code {{ font-family: ui-monospace, Consolas, monospace; font-size: 16px; font-weight: 800; margin: 6px 0 2px; }}
    .hint {{ margin: 0; font-size: 10px; color: #64748b; }}
    @media print {{
      body {{ margin: 8mm; }}
      h1 {{ display: none; }}
    }}
  </style>
</head>
<body>
  <h1>Tem mã trên sản phẩm — {note} ({len(rows)} tem)</h1>
  <div class="sheet">
    {"".join(cards)}
  </div>
</body>
</html>"""

    def batch_to_dict(
        self,
        batch: ProductRedeemBatch,
        *,
        codes: list[ProductRedeemCode] | None = None,
    ) -> dict[str, Any]:
        unused = (
            self.db.query(ProductRedeemCode)
            .filter(
                ProductRedeemCode.batch_id == batch.id,
                ProductRedeemCode.status == STATUS_UNUSED,
            )
            .count()
        )
        product_name = None
        if batch.product_id:
            product = self.db.get(ShopProduct, batch.product_id)
            if product:
                product_name = product.name_vi
        payload: dict[str, Any] = {
            "id": batch.id,
            "product_id": batch.product_id,
            "product_name_vi": product_name,
            "qty": batch.qty,
            "unused_count": unused,
            "note": batch.note,
            "created_by": str(batch.created_by),
            "created_at": _iso(batch.created_at),
        }
        if codes is not None:
            payload["codes"] = [self.code_to_dict(c) for c in codes]
        return payload

    def code_to_dict(self, row: ProductRedeemCode, *, include_qr: bool = False) -> dict[str, Any]:
        share_path = None
        if row.plan_id:
            plan = self.db.get(UserDailyPlan, row.plan_id)
            if plan and plan.share_token:
                share_path = f"/lich/{plan.share_token}"
        status = STATUS_PROCESSING if row.status == STATUS_UNUSED and _reservation_active(row) else row.status
        payload: dict[str, Any] = {
            "id": row.id,
            "batch_id": row.batch_id,
            "code": row.code,
            "status": status,
            "redeemed_at": _iso(row.redeemed_at),
            "plan_id": row.plan_id,
            "share_url_path": share_path,
        }
        if include_qr:
            payload["qr_data_uri"] = qr_png_data_uri(gift_landing_url(row.code))
        return payload
