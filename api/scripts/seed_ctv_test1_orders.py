"""One-off seed: 10 shop orders attributed to test1@taptot.vn."""

from datetime import UTC, datetime, timedelta

from app.core.database import SessionLocal
from app.models.entities import CollaboratorPromo, ShopOrder, ShopOrderItem, ShopProduct, User
from app.services.collaborator_promo_service import merchandise_discounts
from app.services.shop_service import ShopService

EMAIL = "test1@taptot.vn"
NOTE = "Đơn mẫu test CTV"


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).one()
        promo = db.get(CollaboratorPromo, user.id)
        if promo is None or not promo.code:
            raise SystemExit("CTV chưa có mã giảm giá")

        existing = (
            db.query(ShopOrder)
            .filter(ShopOrder.promo_owner_user_id == user.id, ShopOrder.note == NOTE)
            .count()
        )
        if existing:
            print(f"Đã có {existing} đơn mẫu, bỏ qua.")
            return

        products = {
            row.id: row
            for row in db.query(ShopProduct).filter(ShopProduct.id.in_([24, 28, 29])).all()
        }
        if len(products) < 3:
            raise SystemExit(f"Thiếu sản phẩm, chỉ thấy {list(products)}")

        specs = [
            ("awaiting_confirm", "cod", "cod", 0, [(24, 1)], "Nguyễn An", "0901000001", "01", "Hà Nội", "001", "Ba Đình", "00001", "Phúc Xá", "12 phố Nguyễn Thái Học"),
            ("awaiting_confirm", "bank_transfer", "awaiting_transfer", 10, [(28, 2)], "Trần Bình", "0901000002", "79", "TP. Hồ Chí Minh", "760", "Quận 1", "26734", "Bến Nghé", "45 Lê Lợi"),
            ("packing", "cod", "cod", 0, [(29, 1)], "Lê Chi", "0901000003", "48", "Đà Nẵng", "490", "Hải Châu", "20194", "Hải Châu I", "8 Bạch Đằng"),
            ("packing", "bank_transfer", "paid", 5, [(24, 1), (28, 1)], "Phạm Dung", "0901000004", "92", "Cần Thơ", "916", "Ninh Kiều", "31120", "An Hòa", "21 đường 30/4"),
            ("shipping", "cod", "cod", 0, [(29, 2)], "Hoàng Em", "0901000005", "31", "Hải Phòng", "303", "Hồng Bàng", "11353", "Hoàng Văn Thụ", "99 Lạch Tray"),
            ("shipping", "bank_transfer", "paid", 10, [(24, 2)], "Võ Giang", "0901000006", "01", "Hà Nội", "005", "Cầu Giấy", "00157", "Dịch Vọng", "18 Trần Thái Tông"),
            ("completed", "cod", "paid", 0, [(28, 1)], "Đặng Hoa", "0901000007", "79", "TP. Hồ Chí Minh", "769", "Quận 3", "27106", "Võ Thị Sáu", "6 Cách Mạng Tháng 8"),
            ("completed", "bank_transfer", "paid", 15, [(29, 1), (24, 1)], "Bùi Khôi", "0901000008", "48", "Đà Nẵng", "491", "Thanh Khê", "20260", "Thanh Khê Tây", "3 Điện Biên Phủ"),
            ("cancelled", "cod", "cod", 0, [(24, 1)], "Ngô Lan", "0901000009", "92", "Cần Thơ", "917", "Bình Thủy", "31174", "Bình Thủy", "15 Cách Mạng Tháng 8"),
            ("cancelled", "bank_transfer", "awaiting_transfer", 10, [(28, 1), (29, 1)], "Lý Minh", "0901000010", "31", "Hải Phòng", "305", "Lê Chân", "11413", "An Biên", "27 Tô Hiệu"),
        ]

        shop = ShopService(db)
        now = datetime.now(UTC)
        created_codes: list[str] = []
        for index, spec in enumerate(specs):
            (
                status,
                method,
                pay_status,
                event_percent,
                lines,
                name,
                phone,
                province_code,
                province_name,
                district_code,
                district_name,
                ward_code,
                ward_name,
                address,
            ) = spec
            subtotal = sum(products[pid].price_vnd * qty for pid, qty in lines)
            event_vnd, promo_vnd = merchandise_discounts(subtotal, event_percent, int(promo.discount_percent))
            order = ShopOrder(
                user_id=None,
                order_status=status,
                total_vnd=subtotal - event_vnd - promo_vnd,
                shipping_fee_vnd=0,
                discount_percent=event_percent,
                discount_vnd=event_vnd,
                note=NOTE,
                created_at=now - timedelta(hours=10 - index),
                public_code=shop._alloc_public_code(),
                recipient_name=name,
                phone=phone,
                province_code=province_code,
                province_name=province_name,
                district_code=district_code,
                district_name=district_name,
                ward_code=ward_code,
                ward_name=ward_name,
                address_line=address,
                payment_method=method,
                payment_status=pay_status,
                promo_code=promo.code,
                promo_owner_user_id=user.id,
                promo_percent=int(promo.discount_percent),
                promo_discount_vnd=promo_vnd,
            )
            db.add(order)
            db.flush()
            for pid, qty in lines:
                product = products[pid]
                db.add(
                    ShopOrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        name_vi=product.name_vi,
                        unit_price_vnd=product.price_vnd,
                        quantity=qty,
                    )
                )
            created_codes.append(f"{order.public_code} {status} {name}")
        db.commit()
        print("\n".join(created_codes))
    finally:
        db.close()


if __name__ == "__main__":
    main()
