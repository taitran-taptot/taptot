import {
  LEGAL_BRAND,
  LEGAL_CONTACT_EMAIL,
  LEGAL_CONTACT_ZALO,
  SALES_POLICY_HREF,
} from "@/lib/legalMeta";
import type { LegalSection } from "@/lib/legalMeta";

export { SALES_POLICY_HREF };

export const SALES_POLICY_TITLE = "Chính sách bán hàng, giao nhận và đổi trả";
export const SALES_POLICY_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 25 tháng 10 năm 2026.";
export const SALES_POLICY_VERSION = "2026-10-25";

export const SALES_POLICY_INTRO =
  `Chính sách này áp dụng khi bạn đặt phụ kiện thể thao trên gian hàng của ${LEGAL_BRAND}. Bạn có thể đặt không cần tài khoản. Hãy giữ mã đơn dạng TAPTOT-xxxxx để tra cứu. Cách trả tiền và hoàn tiền nằm ở Chính sách thanh toán, hoàn tiền.`;

export const SALES_POLICY_SECTIONS: LegalSection[] = [
  {
    id: "1",
    title: "Phạm vi",
    paragraphs: [
      "Áp dụng cho đơn phụ kiện do TAPTOT tự bán, gồm cả đơn có mã redeem hoặc ưu đãi từ thử thách thể lực.",
      "Lịch tập và thực đơn không phải hàng hóa trong chính sách này. Cách cung cấp và thời hạn xem các nội dung đó nằm ở Chính sách thanh toán, hoàn tiền và Điều khoản sử dụng.",
    ],
  },
  {
    id: "2",
    title: "Đặt hàng và xác nhận",
    paragraphs: [
      "Bạn chọn sản phẩm, đưa vào giỏ, điền họ tên, số điện thoại, địa chỉ giao hàng và chọn chuyển khoản ngân hàng hoặc COD. Khi đặt thành công, hệ thống ghi nhận đơn và trừ tồn kho.",
      "Mỗi đơn có mã công khai dạng TAPTOT-xxxxx. Tra cứu tại trang Tra cứu đơn hàng bằng đúng số điện thoại và mã đơn.",
      `Nếu đã đăng nhập, bạn có thể xem đơn trong tài khoản. Hỗ trợ thêm: ${LEGAL_CONTACT_EMAIL} hoặc Zalo ${LEGAL_CONTACT_ZALO}.`,
    ],
  },
  {
    id: "3",
    title: "Giá và vận chuyển",
    paragraphs: [
      "Giá và số lượng còn lại là số hiển thị trên trang sản phẩm lúc bạn đặt. Nếu hết hàng hoặc tồn kho lệch, chúng tôi báo và đề xuất chờ hàng, đổi sản phẩm hoặc hủy đơn.",
      "Đơn do hệ thống tạo hiện có phí vận chuyển bằng không đồng, tức miễn phí giao hàng, trừ khi trang sản phẩm hoặc thông báo của chiến dịch ghi mức phí khác.",
      "Bạn chịu trách nhiệm về địa chỉ và số điện thoại. Chúng tôi không chịu trách nhiệm nếu giao không được vì thông tin sai hoặc người nhận không nghe máy sau các lần liên hệ hợp lý.",
    ],
  },
  {
    id: "4",
    title: "Giao nhận",
    paragraphs: [
      "Trạng thái đơn đi theo thứ tự: Chờ xác nhận, Đang đóng gói, Đang giao, Hoàn thành.",
      "Thời điểm bạn phải trả tiền phụ thuộc cách thanh toán đã chọn và được mô tả ở Chính sách thanh toán, hoàn tiền.",
    ],
  },
  {
    id: "5",
    title: "Đổi trả và bảo hành",
    paragraphs: [
      "Với hàng lỗi của nhà sản xuất hoặc giao sai so với đơn, hãy liên hệ trong 7 ngày kể từ khi nhận hàng. Giữ bao bì và ảnh hoặc video. Chúng tôi đổi hàng tương đương hoặc phương án khác tùy hàng còn trong kho. Đây là cam kết của gian hàng.",
      "Cam kết 7 ngày không thay thế quyền của bạn đối với hàng khuyết tật, hàng không đúng mô tả hoặc hàng không bảo đảm chất lượng theo luật bảo vệ người tiêu dùng.",
      "Không đổi trả theo cam kết 7 ngày nếu hàng đã dùng sai hướng dẫn, vượt tải trọng an toàn, hao mòn tự nhiên, hoặc hỏng do người dùng. Trường hợp này không xóa quyền đối với lỗi vốn có của hàng.",
      "Bảo hành chỉ áp dụng khi sản phẩm hoặc bao bì ghi điều kiện bảo hành, và thực hiện theo điều kiện đó.",
    ],
  },
  {
    id: "6",
    title: "Mã ưu đãi và thử thách",
    paragraphs: [
      "Mã redeem và mã ưu đãi có hạn dùng, sản phẩm áp dụng và mức giảm riêng. Không bán lại, chuyển nhượng trái phép hoặc gian lận, kể cả giả kết quả thử thách.",
      "Ưu đãi từ thử thách chống đẩy hoặc plank dựa trên kết quả phiên đã ghi và phiếu đã ký. Áp dụng trên giỏ hàng, tối đa một lần cho một đơn, trong thời hạn ghi trên phiếu, không chuyển nhượng. Đóng trình duyệt thì phiếu trên máy có thể mất. Hệ thống từ chối phiếu hết hạn, giả hoặc đã dùng.",
    ],
  },
  {
    id: "7",
    title: "Khiếu nại",
    paragraphs: [
      `Khiếu nại về đơn, giao hàng hoặc đổi trả: ${LEGAL_CONTACT_EMAIL} hoặc Zalo ${LEGAL_CONTACT_ZALO}. Các bước xử lý nằm ở trang Khiếu nại.`,
      `Phiên bản chính sách: ${SALES_POLICY_VERSION}. Bản mới được đăng trên trang này.`,
    ],
  },
];
