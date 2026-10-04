"""Upsert knowledge articles (Cơ bản / Trung cấp / Nâng cao) from markdown files."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import KnowledgeArticle
from app.services.knowledge_slug_aliases import KNOWLEDGE_SLUG_ALIASES

ROOT = API_DIR / "app" / "data" / "knowledge"

ARTICLES = (
    {
        'slug': 'xac-dinh-muc-tieu-tap-luyen',
        'title_vi': '1.0 — Xác định mục tiêu tập luyện',
        'level': 'beginner',
        'sort_order': 0,
        'read_time_min': 6,
        'seo_title': 'Xác định mục tiêu tập luyện — Hướng dẫn khoa học cho người mới',
        'seo_description': 'Cách xác định một mục tiêu tập luyện thực tế, đo lường được trong 8–12 tuần cho người mới bắt đầu.',
        'file': 'xac-dinh-muc-tieu-tap-luyen.md',
    },
    {
        'slug': 'cach-doc-lich-tap-quy-uoc-buoi-tap',
        'title_vi': '1.1 — Cách đọc lịch tập & Quy ước buổi tập',
        'level': 'beginner',
        'sort_order': 1,
        'read_time_min': 6,
        'seo_title': 'Cách đọc lịch tập gym, calisthenics cho người mới — Hiểu Set, Rep, Rest',
        'seo_description': 'Hướng dẫn chi tiết cách đọc lịch tập TAPTOT: Hiệp (Set), Số cái (Rep), Thời gian nghỉ (Rest) và thứ tự thực hiện chuẩn xác.',
        'file': 'cach-doc-lich-tap-quy-uoc-buoi-tap.md',
    },
    {
        'slug': 'ban-do-cac-nhom-co-chinh-co-che-chuyen-dong',
        'title_vi': '1.2 — Bản đồ các nhóm cơ chính & Cơ chế chuyển động',
        'level': 'beginner',
        'sort_order': 2,
        'read_time_min': 6,
        'seo_title': 'Bản đồ nhóm cơ trên cơ thể người cho người mới bắt đầu tập luyện',
        'seo_description': 'Hiểu giải phẫu và vai trò sinh cơ học của 6 nhóm cơ lớn: Ngực, Lưng, Vai, Tay, Chân và Core giúp bạn tập đúng điểm mỏi.',
        'file': 'ban-do-cac-nhom-co-chinh-co-che-chuyen-dong.md',
    },
    {
        'slug': 'khoi-dong-warm-up-van-dong-khop-mobility',
        'title_vi': '1.3 — Khởi động (Warm-up) & Vận động khớp (Mobility)',
        'level': 'beginner',
        'sort_order': 3,
        'read_time_min': 5,
        'seo_title': 'Cách khởi động đúng cách trước khi tập gym và calisthenics',
        'seo_description': 'Quy trình khởi động 2 bước chuẩn khoa học: Tăng nhiệt độ mô và Kích hoạt tầm vận động khớp (Mobility) giúp phòng tránh chấn thương.',
        'file': 'khoi-dong-warm-up-van-dong-khop-mobility.md',
    },
    {
        'slug': 'ky-thuat-tap-chuan-form-an-toan-co-xuong-khop',
        'title_vi': '1.4 — Kỹ thuật tập chuẩn (Form) & An toàn cơ xương khớp',
        'level': 'beginner',
        'sort_order': 4,
        'read_time_min': 5,
        'seo_title': 'Kỹ thuật tập chuẩn (Form) trong tập gym và calisthenics cho người mới',
        'seo_description': 'Thế nào là một form tập chuẩn? Nguyên tắc giữ cột sống trung tính, quỹ đạo khớp và cách nén bụng (Bracing) để bảo vệ đĩa đệm.',
        'file': 'ky-thuat-tap-chuan-form-an-toan-co-xuong-khop.md',
    },
    {
        'slug': 'ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency',
        'title_vi': '1.5 — Ba nút chỉnh: Khối lượng (Volume), Độ nặng (Intensity), Tần suất (Frequency)',
        'level': 'beginner',
        'sort_order': 5,
        'read_time_min': 5,
        'seo_title': 'Hiểu Volume, Intensity, Frequency trong thể hình cho người mới',
        'seo_description': 'Làm chủ 3 biến số quan trọng nhất của giáo án tập luyện: Khối lượng, Độ nặng và Tần suất giúp bạn tiến bộ bền vững không kiệt sức.',
        'file': 'ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency.md',
    },
    {
        'slug': 'nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban',
        'title_vi': '1.6 — Nguyên tắc Quá tải lũy tiến (Progressive Overload) cơ bản',
        'level': 'beginner',
        'sort_order': 6,
        'read_time_min': 5,
        'seo_title': 'Nguyên tắc Progressive Overload trong thể hình và calisthenics cho người mới',
        'seo_description': 'Hiểu bản chất của Quá tải lũy tiến: Làm thế nào để cơ bắp liên tục thích nghi và phát triển qua từng tuần mà không cần tăng tạ ẩu.',
        'file': 'nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban.md',
    },
    {
        'slug': 'dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly',
        'title_vi': '1.7 — Đau mỏi cơ (DOMS) và Chấn thương: Cách phân biệt và xử lý',
        'level': 'beginner',
        'sort_order': 7,
        'read_time_min': 5,
        'seo_title': 'Phân biệt đau mỏi cơ DOMS và chấn thương khi tập gym cho người mới',
        'seo_description': 'Làm sao biết mình đang mỏi cơ phát triển bình thường hay đã bị chấn thương khớp? Dấu hiệu cảnh báo nguy hiểm và quy tắc xử lý an toàn.',
        'file': 'dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly.md',
    },
    {
        'slug': 'tuan-xa-tai-nhe-deload-cho-nguoi-moi',
        'title_vi': '1.8 — Tuần xả tải nhẹ (Deload) cho người mới',
        'level': 'beginner',
        'sort_order': 8,
        'read_time_min': 5,
        'seo_title': 'Tuần xả tải Deload là gì? Tại sao người mới cần tuần tập nhẹ?',
        'seo_description': 'Hiểu đúng về Deload: Tuần tập nhẹ có chủ đích giúp gân khớp và hệ thần kinh hồi phục trọn vẹn để bứt phá giai đoạn tiếp theo.',
        'file': 'tuan-xa-tai-nhe-deload-cho-nguoi-moi.md',
    },
    {
        'slug': 'nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo',
        'title_vi': '1.9 — Năng lượng và Cân nặng: Thâm hụt, Thặng dư và Cân bằng Calo',
        'level': 'beginner',
        'sort_order': 9,
        'read_time_min': 5,
        'seo_title': 'Calories trong thể hình: Thâm hụt, thặng dư và cân bằng năng lượng',
        'seo_description': 'Hiểu bản chất của Calo: Cách kiểm soát năng lượng nạp vào và tiêu hao để tăng cơ hoặc giảm mỡ hiệu quả mà không cần nhịn ăn cực đoan.',
        'file': 'nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo.md',
    },
    {
        'slug': 'cach-tinh-tdee-theo-muc-van-dong-thuc-te',
        'title_vi': '1.10 — Cách tính TDEE theo mức vận động thực tế',
        'level': 'beginner',
        'sort_order': 10,
        'read_time_min': 6,
        'seo_title': 'Cách tính TDEE và BMR chuẩn xác cho người tập gym, thể hình',
        'seo_description': 'Hiểu cấu trúc của TDEE (BMR, NEAT, EAT, TEF) và cách chọn hệ số vận động trung thực để không bị tính thừa calo.',
        'file': 'cach-tinh-tdee-theo-muc-van-dong-thuc-te.md',
    },
    {
        'slug': 'dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat',
        'title_vi': '1.11 — Dinh dưỡng đa lượng: Chất đạm (Protein), Tinh bột (Carb) và Chất béo (Fat)',
        'level': 'beginner',
        'sort_order': 11,
        'read_time_min': 6,
        'seo_title': 'Macronutrients là gì? Cách phân chia Protein, Carb, Fat cho người mới tập',
        'seo_description': 'Hiểu đúng vai trò của Protein, Carb và Fat trong thể hình. Cách phân bổ macro theo đĩa ăn người Việt không cần cân tiểu ly phức tạp.',
        'file': 'dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat.md',
    },
    {
        'slug': 'phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien',
        'title_vi': '1.12 — Phục hồi cơ bắp, Giấc ngủ và Tối ưu phát triển',
        'level': 'beginner',
        'sort_order': 12,
        'read_time_min': 5,
        'seo_title': 'Vai trò của giấc ngủ và phục hồi trong thể hình cho người mới',
        'seo_description': 'Cơ bắp phát triển khi bạn ngủ, không phải khi bạn tập. Tìm hiểu khoa học về giấc ngủ, hormone tăng trưởng GH và phục hồi chủ động.',
        'file': 'phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien.md',
    },
    {
        'slug': 'tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi',
        'title_vi': '1.13 — Từ điển thuật ngữ tập luyện cho người mới',
        'level': 'beginner',
        'sort_order': 13,
        'read_time_min': 5,
        'seo_title': 'Từ điển thuật ngữ gym và tập luyện cho người mới',
        'seo_description': 'Giải thích dễ hiểu Set, Rep, ROM, RIR, RPE, Volume, Intensity, Frequency và các thuật ngữ tập luyện thường gặp.',
        'file': 'tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi.md',
    },
    {
        'slug': 'mau-van-dong-va-cach-tang-giam-do-kho-bai-tap',
        'title_vi': '1.14 — Mẫu vận động và cách tăng, giảm độ khó bài tập',
        'level': 'beginner',
        'sort_order': 14,
        'read_time_min': 7,
        'seo_title': 'Mẫu vận động và cách điều chỉnh bài tập cho người mới',
        'seo_description': 'Hiểu squat, hinge, lunge, push, pull và core; biết cách chọn biến thể, tăng hoặc giảm độ khó an toàn.',
        'file': 'mau-van-dong-va-cach-tang-giam-do-kho-bai-tap.md',
    },
    {
        'slug': 'cardio-cho-suc-khoe-va-giam-mo',
        'title_vi': '1.15 — Cardio cho sức khỏe và giảm mỡ',
        'level': 'beginner',
        'sort_order': 15,
        'read_time_min': 6,
        'seo_title': 'Cardio cho sức khỏe và giảm mỡ dành cho người mới',
        'seo_description': 'Cách bắt đầu cardio, nhận biết cường độ và kết hợp với tập sức mạnh để cải thiện sức khỏe, hỗ trợ giảm mỡ.',
        'file': 'cardio-cho-suc-khoe-va-giam-mo.md',
    },
    {
        'slug': 'theo-doi-dau-va-dau-hieu-can-kham',
        'title_vi': '1.16 — Theo dõi đau và dấu hiệu cần đi khám',
        'level': 'beginner',
        'sort_order': 16,
        'read_time_min': 5,
        'seo_title': 'Theo dõi đau khi tập và dấu hiệu cần đi khám',
        'seo_description': 'Quy trình dừng, đổi bài, theo dõi đau và nhận biết những dấu hiệu cần bác sĩ hoặc chuyên gia vật lý trị liệu.',
        'file': 'theo-doi-dau-va-dau-hieu-can-kham.md',
    },
    {
        'slug': 'nuoc-dien-giai-va-ruou-bia-khi-tap-luyen',
        'title_vi': '1.17 — Nước, điện giải và rượu bia khi tập luyện',
        'level': 'beginner',
        'sort_order': 17,
        'read_time_min': 5,
        'seo_title': 'Nước, điện giải và rượu bia khi tập luyện',
        'seo_description': 'Hướng dẫn uống nước, dùng điện giải theo nhu cầu và hiểu ảnh hưởng của rượu bia đến hiệu suất, giấc ngủ và phục hồi.',
        'file': 'nuoc-dien-giai-va-ruou-bia-khi-tap-luyen.md',
    },
    {
        'slug': 'thuc-pham-bo-sung-theo-muc-do-bang-chung',
        'title_vi': '1.18 — Thực phẩm bổ sung theo mức độ bằng chứng',
        'level': 'beginner',
        'sort_order': 18,
        'read_time_min': 6,
        'seo_title': 'Thực phẩm bổ sung fitness theo mức độ bằng chứng',
        'seo_description': 'Hiểu đúng creatine, caffeine, protein powder, vitamin và những sản phẩm bị quảng cáo quá mức.',
        'file': 'thuc-pham-bo-sung-theo-muc-do-bang-chung.md',
    },
    {
        'slug': 'toi-uu-progressive-overload-nang-cao',
        'title_vi': '2.0 — Tối ưu Progressive Overload nâng cao',
        'level': 'intermediate',
        'sort_order': 20,
        'read_time_min': 6,
        'seo_title': 'Tối ưu Progressive Overload nâng cao',
        'seo_description': 'Tối ưu Progressive Overload nâng cao — kiến thức fitness Trung cấp cho người Việt. Đọc khoảng 5 phút, có dẫn chứng.',
        'file': 'toi-uu-progressive-overload-nang-cao.md',
    },
    {
        'slug': 'rpe-va-rir-trong-tung-set',
        'title_vi': '2.1 — RPE và RIR trong từng set',
        'level': 'intermediate',
        'sort_order': 21,
        'read_time_min': 5,
        'seo_title': 'RPE và RIR trong từng set',
        'seo_description': 'RPE và RIR trong từng set — kiến thức fitness Trung cấp cho người Việt. Đọc khoảng 5 phút, có dẫn chứng.',
        'file': 'rpe-va-rir-trong-tung-set.md',
    },
    {
        'slug': 'quan-ly-volume-theo-nhom-co',
        'title_vi': '2.2 — Quản lý Volume theo nhóm cơ',
        'level': 'intermediate',
        'sort_order': 22,
        'read_time_min': 5,
        'seo_title': 'Quản lý Volume theo nhóm cơ',
        'seo_description': 'Quản lý Volume theo nhóm cơ — kiến thức fitness Trung cấp cho người Việt. Đọc khoảng 5 phút, có dẫn chứng.',
        'file': 'quan-ly-volume-theo-nhom-co.md',
    },
    {
        'slug': 'deload-dung-thoi-diem',
        'title_vi': '2.3 — Deload đúng thời điểm',
        'level': 'intermediate',
        'sort_order': 23,
        'read_time_min': 5,
        'seo_title': 'Deload đúng thời điểm',
        'seo_description': 'Deload đúng thời điểm — kiến thức fitness Trung cấp cho người Việt. Đọc khoảng 5 phút, có dẫn chứng.',
        'file': 'deload-dung-thoi-diem.md',
    },
    {
        'slug': 'carb-cycling-co-ban',
        'title_vi': '2.4 — Carb cycling cơ bản',
        'level': 'intermediate',
        'sort_order': 24,
        'read_time_min': 5,
        'seo_title': 'Carb cycling cơ bản',
        'seo_description': 'Carb cycling cơ bản — kiến thức fitness Trung cấp cho người Việt. Đọc khoảng 5 phút, có dẫn chứng.',
        'file': 'carb-cycling-co-ban.md',
    },
    {
        'slug': 'refeed-va-diet-break',
        'title_vi': '2.5 — Refeed và diet break',
        'level': 'intermediate',
        'sort_order': 25,
        'read_time_min': 5,
        'seo_title': 'Refeed và diet break',
        'seo_description': 'Refeed và diet break — kiến thức fitness Trung cấp cho người Việt. Đọc khoảng 5 phút, có dẫn chứng.',
        'file': 'refeed-va-diet-break.md',
    },
    {
        'slug': 'mind-muscle-connection-nang-cao',
        'title_vi': '2.6 — Mind-Muscle Connection nâng cao',
        'level': 'intermediate',
        'sort_order': 26,
        'read_time_min': 6,
        'seo_title': 'Mind-Muscle Connection nâng cao',
        'seo_description': 'Mind-Muscle Connection nâng cao — kiến thức fitness Trung cấp cho người Việt. Đọc khoảng 5 phút, có dẫn chứng.',
        'file': 'mind-muscle-connection-nang-cao.md',
    },
    {
        'slug': 'ky-thuat-drop-set-superset-rest-pause',
        'title_vi': '2.7 — Kỹ thuật Drop set, Superset, Rest-pause',
        'level': 'intermediate',
        'sort_order': 27,
        'read_time_min': 5,
        'seo_title': 'Kỹ thuật Drop set, Superset, Rest-pause',
        'seo_description': 'Kỹ thuật Drop set, Superset, Rest-pause — kiến thức fitness Trung cấp cho người Việt. Đọc khoảng 5 phút, có dẫn chứng.',
        'file': 'ky-thuat-drop-set-superset-rest-pause.md',
    },
    {
        'slug': 'periodization-co-ban',
        'title_vi': '2.8 — Periodization cơ bản',
        'level': 'intermediate',
        'sort_order': 28,
        'read_time_min': 5,
        'seo_title': 'Periodization cơ bản',
        'seo_description': 'Periodization cơ bản — kiến thức fitness Trung cấp cho người Việt. Đọc khoảng 5 phút, có dẫn chứng.',
        'file': 'periodization-co-ban.md',
    },
)


def upsert() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    db = SessionLocal()
    try:
        for spec in ARTICLES:
            path = ROOT / spec["file"]
            content = path.read_text(encoding="utf-8").strip() + "\n"
            row = db.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == spec["slug"]))
            if row is None:
                for old, new in KNOWLEDGE_SLUG_ALIASES.items():
                    if new == spec["slug"]:
                        row = db.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == old))
                        if row is not None:
                            row.slug = new
                            break
            if row is None:
                row = KnowledgeArticle(slug=spec["slug"], is_published=True, published_at=now)
                db.add(row)
            row.title_vi = spec["title_vi"]
            row.content_md = content
            row.level = spec["level"]
            row.sort_order = spec["sort_order"]
            row.read_time_min = spec["read_time_min"]
            row.seo_title = spec.get("seo_title") or None
            row.seo_description = spec["seo_description"]
            row.is_published = True
            if row.published_at is None:
                row.published_at = now
            print(f"upsert {spec['slug']}")
        removed = db.query(KnowledgeArticle).filter(KnowledgeArticle.level == "advanced").all()
        for row in removed:
            print(f"delete advanced {row.slug}")
            db.delete(row)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    upsert()
