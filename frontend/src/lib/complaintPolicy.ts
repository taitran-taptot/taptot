import {
  LEGAL_CONTACT_EMAIL,
  LEGAL_CONTACT_ZALO,
  COMPLAINT_HREF,
} from "@/lib/legalMeta";
import type { LegalSection } from "@/lib/legalMeta";

export { COMPLAINT_HREF };

export const COMPLAINT_TITLE = "Tiếp nhận và giải quyết khiếu nại";
export const COMPLAINT_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 25 tháng 10 năm 2026.";
export const COMPLAINT_VERSION = "2026-10-25";

export const COMPLAINT_INTRO =
  "Trang này là cách gửi phản ánh, yêu cầu và khiếu nại về phụ kiện, lịch tập, thực đơn, tài khoản và dữ liệu cá nhân. Thời hạn trả lời dưới đây là cam kết vận hành của TAPTOT, không phải thời hạn do luật ấn định.";

export const COMPLAINT_SECTIONS: LegalSection[] = [
  {
    id: "1",
    title: "Những việc có thể khiếu nại",
    paragraphs: ["Bạn có thể gửi khiếu nại về:"],
    bullets: [
      "Đơn phụ kiện: sai hàng, lỗi hàng, giao hàng, giá, mã ưu đãi hoặc hoàn tiền.",
      "Lịch tập, thực đơn, kiểm tra thể lực hoặc tài khoản: không xem được nội dung, mất quyền truy cập, hoặc nội dung lệch so với thông tin bạn đã cung cấp.",
      "Dữ liệu cá nhân: yêu cầu xem, sửa, xóa hoặc rút đồng ý.",
    ],
  },
  {
    id: "2",
    title: "Nơi nhận",
    paragraphs: [
      `Email: ${LEGAL_CONTACT_EMAIL}.`,
      `Zalo: ${LEGAL_CONTACT_ZALO}.`,
      "Form Góp ý trên website, nếu bạn muốn gửi qua form.",
      "Ghi rõ họ tên, số điện thoại, email, mã đơn nếu có, và mô tả việc cần xử lý. Với hàng đã nhận, gửi thêm ảnh hoặc video. Với chuyển khoản, gửi thêm biên lai.",
    ],
  },
  {
    id: "3",
    title: "Các bước xử lý",
    paragraphs: ["Sau khi nhận đủ thông tin, chúng tôi làm lần lượt:"],
    bullets: [
      "Ghi nhận yêu cầu và mã đơn hoặc tài khoản liên quan.",
      "Đối chiếu đơn hàng, lịch sử chuyển khoản, tồn kho hoặc dữ liệu tài khoản.",
      "Trả lời hướng xử lý: đổi hàng, giao lại, hoàn tiền, sửa dữ liệu, khôi phục quyền xem trong hạn lịch còn hiệu lực, hoặc từ chối kèm lý do.",
      "Thực hiện phương án đã báo. Hoàn tiền chuyển khoản làm theo Chính sách thanh toán, hoàn tiền.",
    ],
  },
  {
    id: "4",
    title: "Thời hạn cam kết",
    paragraphs: [
      "Chúng tôi xác nhận đã nhận yêu cầu trong 3 ngày làm việc kể từ khi email, Zalo hoặc form tới nơi.",
      "Chúng tôi trả lời hướng xử lý trong 15 ngày làm việc kể từ khi nhận đủ thông tin để đối soát. Nếu thiếu ảnh, mã đơn hoặc biên lai, thời hạn tính từ lúc bạn gửi bổ sung.",
      "Hai mốc này là cam kết của TAPTOT. Nếu luật hoặc cơ quan nhà nước đặt thời hạn ngắn hơn cho một vụ việc cụ thể, thời hạn đó được áp dụng.",
    ],
  },
  {
    id: "5",
    title: "Quyền khác của bạn",
    paragraphs: [
      "Quy trình này không cấm bạn khiếu nại với cơ quan bảo vệ người tiêu dùng, cơ quan bảo vệ dữ liệu cá nhân, hoặc khởi kiện tại Tòa án có thẩm quyền.",
      "Với hàng khuyết tật hoặc không đúng mô tả, quyền theo luật bảo vệ người tiêu dùng vẫn còn song song với cam kết đổi trả 7 ngày của gian hàng.",
      `Phiên bản: ${COMPLAINT_VERSION}.`,
    ],
  },
];
