"""Shop finance and inventory for the admin stats page."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models.entities import (
    ShopMonthCost,
    ShopMonthProductCost,
    ShopOrder,
    ShopOrderItem,
    ShopProduct,
)
from app.services.shop_service import (
    ORDER_AWAITING,
    ORDER_CANCELLED,
    ORDER_COMPLETED,
    ORDER_RETURNED,
    ORDER_PACKING,
    ORDER_SHIPPING,
    PAY_STATUS_COD,
    PAY_STATUS_PAID,
)

ORDER_STATUSES = (
    ORDER_AWAITING,
    ORDER_PACKING,
    ORDER_SHIPPING,
    ORDER_COMPLETED,
    ORDER_CANCELLED,
    ORDER_RETURNED,
)


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


class AdminStatsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def year_stats(self, year: int | None = None, month: int | None = None) -> dict[str, Any]:
        y = int(year or datetime.now(UTC).year)
        if y < 2000 or y > 2100:
            raise BadRequestError("Năm không hợp lệ")
        m = int(month) if month is not None else None
        if m is not None and (m < 1 or m > 12):
            raise BadRequestError("Tháng không hợp lệ")

        return {
            "year": y,
            "month": m,
            "finance": self.finance_board(y),
            "inventory": self.inventory(),
        }

    def inventory(self) -> dict[str, Any]:
        products = sorted(
            (product for product in self.db.query(ShopProduct).all() if product.slug),
            key=lambda product: (str(product.name_vi or ""), str(product.slug)),
        )
        sold_by_id = {int(product.id): 0 for product in products}
        closed = {ORDER_CANCELLED, ORDER_RETURNED}
        order_ids = [
            int(order.id)
            for order in self.db.query(ShopOrder).all()
            if str(order.order_status or "") not in closed
        ]
        if order_ids:
            items = (
                self.db.query(ShopOrderItem)
                .filter(ShopOrderItem.order_id.in_(order_ids))
                .all()
            )
            for item in items:
                if item.product_id is None:
                    continue
                product_id = int(item.product_id)
                if product_id in sold_by_id:
                    sold_by_id[product_id] += int(item.quantity or 0)

        rows: list[dict[str, Any]] = []
        sold_total = 0
        remaining_total = 0
        for product in products:
            sold = sold_by_id[int(product.id)]
            remaining = int(product.stock_qty or 0)
            rows.append(
                {
                    "id": int(product.id),
                    "name_vi": product.name_vi or str(product.slug),
                    "total": sold + remaining,
                    "sold": sold,
                    "remaining": remaining,
                }
            )
            sold_total += sold
            remaining_total += remaining
        return {
            "totals": {
                "total": sold_total + remaining_total,
                "sold": sold_total,
                "remaining": remaining_total,
            },
            "products": rows,
        }

    def finance_board(self, year: int) -> dict[str, Any]:
        y = int(year)
        if y < 2000 or y > 2100:
            raise BadRequestError("Năm không hợp lệ")

        catalog = sorted(
            (
                product
                for product in self.db.query(ShopProduct).all()
                if product.slug and bool(product.is_active)
            ),
            key=lambda product: (str(product.name_vi or ""), str(product.slug)),
        )
        product_ids = [int(product.id) for product in catalog]
        sales = self._finance_sales(set(product_ids))
        month_costs = {
            (int(row.year), int(row.month)): row for row in self.db.query(ShopMonthCost).all()
        }
        unit_costs: dict[tuple[int, int, int], int] = {}
        for row in self.db.query(ShopMonthProductCost).all():
            unit_costs[(int(row.year), int(row.month), int(row.product_id))] = int(row.cost_vnd or 0)

        lifetime_revenue = 0
        lifetime_orders = 0
        lifetime_operating = 0
        lifetime_marketing = 0
        lifetime_profit = 0
        keys = set(sales) | set(month_costs)
        for key in keys:
            bucket = sales.get(key)
            revenue = int(bucket["revenue_vnd"]) if bucket else 0
            orders = int(bucket["orders"]) if bucket else 0
            cogs = 0
            if bucket is not None:
                for product_id in product_ids:
                    cogs += int(bucket["units"].get(product_id, 0)) * int(unit_costs.get((*key, product_id), 0))
            stored = month_costs.get(key)
            operating = int(stored.operating_vnd or 0) if stored is not None else 0
            marketing = int(stored.marketing_vnd or 0) if stored is not None else 0
            lifetime_revenue += revenue
            lifetime_orders += orders
            lifetime_operating += operating
            lifetime_marketing += marketing
            lifetime_profit += revenue - cogs - operating - marketing

        products_out: list[dict[str, Any]] = []
        for product in catalog:
            months_out = []
            for month in range(1, 13):
                bucket = sales.get((y, month))
                units = int(bucket["units"].get(product.id, 0)) if bucket else 0
                revenue = int(bucket["revenue"].get(product.id, 0)) if bucket else 0
                unit_cost = int(unit_costs.get((y, month, int(product.id)), 0))
                months_out.append(
                    {
                        "month": month,
                        "units": units,
                        "revenue_vnd": revenue,
                        "profit_vnd": revenue - units * unit_cost,
                    }
                )
            products_out.append(
                {
                    "id": int(product.id),
                    "slug": str(product.slug),
                    "name_vi": product.name_vi or str(product.slug),
                    "months": months_out,
                }
            )

        months_payload: list[dict[str, Any]] = []
        for month in range(1, 13):
            key = (y, month)
            bucket = sales.get(key)
            revenue = int(bucket["revenue_vnd"]) if bucket else 0
            stored = month_costs.get(key)
            operating = int(stored.operating_vnd or 0) if stored is not None else 0
            marketing = int(stored.marketing_vnd or 0) if stored is not None else 0
            units_by_product = []
            product_costs = []
            cogs = 0
            for product in catalog:
                units = int(bucket["units"].get(product.id, 0)) if bucket else 0
                cost = int(unit_costs.get((y, month, int(product.id)), 0))
                units_by_product.append({"product_id": int(product.id), "units": units})
                product_costs.append({"product_id": int(product.id), "cost_vnd": cost})
                cogs += units * cost
            months_payload.append(
                {
                    "month": month,
                    "revenue_vnd": revenue,
                    "units_by_product": units_by_product,
                    "costs": {
                        "operating_vnd": operating,
                        "marketing_vnd": marketing,
                        "product_costs": product_costs,
                    },
                    "cogs_vnd": cogs,
                    "profit_vnd": revenue - cogs - operating - marketing,
                }
            )

        status_counts = {status: 0 for status in ORDER_STATUSES}
        collected_vnd = 0
        uncollected_vnd = 0
        for order in self.db.query(ShopOrder).all():
            status = str(order.order_status or "")
            if status == "placed":
                status = ORDER_AWAITING
            if status in status_counts:
                status_counts[status] += 1
            if status in {ORDER_CANCELLED, ORDER_RETURNED}:
                continue
            amount = int(order.total_vnd or 0)
            pay = str(order.payment_status or "")
            money_in = pay == PAY_STATUS_PAID or (pay == PAY_STATUS_COD and status == ORDER_COMPLETED)
            if money_in:
                collected_vnd += amount
            else:
                uncollected_vnd += amount

        return {
            "lifetime": {
                "revenue_vnd": lifetime_revenue,
                "profit_vnd": lifetime_profit,
                "operating_vnd": lifetime_operating,
                "marketing_vnd": lifetime_marketing,
                "orders": lifetime_orders,
                "collected_vnd": collected_vnd,
                "uncollected_vnd": uncollected_vnd,
            },
            "order_status": status_counts,
            "products": products_out,
            "months": months_payload,
        }

    def set_month_costs(
        self,
        year: int,
        month: int,
        operating_vnd: int,
        marketing_vnd: int,
        product_costs: list[dict[str, int]],
    ) -> dict[str, Any]:
        y = int(year)
        m = int(month)
        if y < 2000 or y > 2100:
            raise BadRequestError("Năm không hợp lệ")
        if m < 1 or m > 12:
            raise BadRequestError("Tháng không hợp lệ")
        operating = int(operating_vnd)
        marketing = int(marketing_vnd)
        if operating < 0 or marketing < 0:
            raise BadRequestError("Chi phí phải ≥ 0")

        active_ids = {
            int(product.id)
            for product in self.db.query(ShopProduct).all()
            if product.slug and bool(product.is_active)
        }
        cleaned: list[tuple[int, int]] = []
        seen: set[int] = set()
        for row in product_costs:
            product_id = int(row["product_id"])
            cost = int(row["cost_vnd"])
            if cost < 0:
                raise BadRequestError("Giá nhập phải ≥ 0")
            if product_id not in active_ids:
                raise BadRequestError("Sản phẩm không hợp lệ")
            if product_id in seen:
                raise BadRequestError("Sản phẩm bị lặp")
            seen.add(product_id)
            cleaned.append((product_id, cost))

        stored = self.db.get(ShopMonthCost, (y, m))
        if stored is None:
            stored = ShopMonthCost(year=y, month=m, operating_vnd=operating, marketing_vnd=marketing)
            self.db.add(stored)
        else:
            stored.operating_vnd = operating
            stored.marketing_vnd = marketing
        for product_id, cost in cleaned:
            unit = self.db.get(ShopMonthProductCost, (y, m, product_id))
            if unit is None:
                self.db.add(
                    ShopMonthProductCost(year=y, month=m, product_id=product_id, cost_vnd=cost)
                )
            else:
                unit.cost_vnd = cost
        self.db.commit()
        return {
            "year": y,
            "month": m,
            "operating_vnd": operating,
            "marketing_vnd": marketing,
            "product_costs": [
                {"product_id": product_id, "cost_vnd": cost} for product_id, cost in cleaned
            ],
        }

    def _finance_sales(self, product_ids: set[int]) -> dict[tuple[int, int], dict[str, Any]]:
        orders = self.db.query(ShopOrder).all()
        order_ids = [int(order.id) for order in orders]
        items_by_order: dict[int, list[ShopOrderItem]] = {oid: [] for oid in order_ids}
        if order_ids:
            for item in self.db.query(ShopOrderItem).filter(ShopOrderItem.order_id.in_(order_ids)).all():
                items_by_order.setdefault(int(item.order_id), []).append(item)

        products = {int(product.id): product for product in self.db.query(ShopProduct).all()}
        buckets: dict[tuple[int, int], dict[str, Any]] = {}

        def bucket_for(key: tuple[int, int]) -> dict[str, Any]:
            found = buckets.get(key)
            if found is None:
                found = {
                    "revenue_vnd": 0,
                    "orders": 0,
                    "units": {product_id: 0 for product_id in product_ids},
                    "revenue": {product_id: 0 for product_id in product_ids},
                }
                buckets[key] = found
            return found

        for order in orders:
            created = _naive_utc(order.created_at)
            if created is None:
                continue
            if str(order.order_status or "") in {ORDER_CANCELLED, ORDER_RETURNED}:
                continue
            bucket = bucket_for((created.year, created.month))
            net = int(order.total_vnd or 0)
            bucket["revenue_vnd"] += net
            bucket["orders"] += 1

            lines: list[tuple[int, int, ShopProduct | None]] = []
            line_gross = 0
            for item in items_by_order.get(int(order.id), []):
                qty = int(item.quantity or 0)
                line = int(item.unit_price_vnd or 0) * qty
                line_gross += line
                product = products.get(int(item.product_id)) if item.product_id else None
                lines.append((qty, line, product))

            remaining_net = net
            for index, (qty, line, product) in enumerate(lines):
                if index == len(lines) - 1:
                    share = remaining_net
                elif line_gross:
                    share = int(round(net * line / line_gross))
                    remaining_net -= share
                else:
                    share = 0
                if product is not None and int(product.id) in product_ids:
                    bucket["units"][int(product.id)] += qty
                    bucket["revenue"][int(product.id)] += share
        return buckets
