import {
  LEGAL_BRAND,
  LEGAL_CONTACT_EMAIL,
  LEGAL_CONTACT_ZALO,
  SALES_POLICY_HREF,
} from "@/lib/legalMeta";
import type { LegalSection } from "@/lib/legalMeta";

export { SALES_POLICY_HREF };

export const SALES_POLICY_TITLE = "Chính sách bán hàng, giao nhận và đổi trả";
export const SALES_POLICY_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 24 tháng 09 năm 2026.";
export const SALES_POLICY_VERSION = "2026-09-24";

export const SALES_POLICY_INTRO =
  `Chính sách này áp dụng khi bạn đặt mua phụ kiện thể thao hoặc sử dụng mã ưu đãi / thanh toán gói trên ${LEGAL_BRAND}. Bạn có thể đặt hàng không cần tài khoản; hãy lưu mã đơn (dạng TAPTOT-xxxxx) để tra cứu trạng thái giao hàng.`;

export const SALES_POLICY_SECTIONS: LegalSection[] = [
  {
    id: "1",
    title: "Phạm vi",
    paragraphs: [
      "Áp dụng cho đơn hàng phụ kiện trên gian hàng của Hệ thống, mã redeem gắn sản phẩm/kế hoạch, ưu đãi từ thử thách (ví dụ chống đẩy), và thanh toán gói dịch vụ trực tuyến khi tính năng được bật.",
    ],
  },
  {
    id: "2",
    title: "Đặt hàng và xác nhận",
    paragraphs: [
      "Bạn chọn sản phẩm, đưa vào giỏ, điền họ tên / số điện thoại / địa chỉ giao hàng và chọn phương thức thanh toán (COD hoặc chuyển khoản). Hệ thống ghi nhận đơn, trừ tồn kho ngay khi đặt thành công, và gửi SMS xác nhận (khi cấu hình gửi tin nhắn).",
      "Mỗi đơn có mã công khai dạng TAPTOT-xxxxx. Vui lòng lưu mã này. Tra cứu trạng thái tại trang Tra cứu đơn hàng bằng đúng cặp Số điện thoại + Mã đơn.",
      `Nếu đã đăng nhập, bạn còn xem được danh sách đơn trong tài khoản. Hỗ trợ thêm: ${LEGAL_CONTACT_EMAIL} / Zalo ${LEGAL_CONTACT_ZALO}.`,
    ],
  },
  {
    id: "3",
    title: "Thanh toán đơn phụ kiện",
    paragraphs: [
      "COD: thanh toán tiền mặt (hoặc hình thức thu hộ) khi nhận hàng. Trạng thái thanh toán ghi nhận là COD cho đến khi giao xong theo quy trình vận hành.",
      "Chuyển khoản: quét QR VietQR hoặc chuyển đúng số tài khoản hiển thị, với nội dung chuyển khoản đúng mã đơn. Đơn ở trạng thái chờ chuyển khoản cho đến khi quản trị xác nhận đã nhận tiền trên sao kê.",
      "Giá và tồn kho hiển thị trên trang sản phẩm tại thời điểm đặt. Nếu hết hàng hoặc sai lệch tồn, chúng tôi sẽ thông báo và đề xuất phương án (chờ hàng, đổi sản phẩm hoặc hủy).",
      "Hủy đơn do quản trị (ví dụ hoàn kho khi đơn còn chờ xác nhận) được xử lý theo từng trường hợp. Nếu bạn đã chuyển khoản, hoàn tiền được thỏa thuận qua kênh liên hệ.",
    ],
  },
  {
    id: "4",
    title: "Giao nhận",
    paragraphs: [
      "Hiện tại đơn phụ kiện được miễn phí vận chuyển (free ship) trên toàn quốc, trừ khi trang sản phẩm hoặc thông báo chiến dịch ghi rõ khác.",
      "Trạng thái đơn: Chờ xác nhận → Đang đóng gói → Đang giao → Hoàn thành. Bạn có trách nhiệm cung cấp địa chỉ / số liên hệ chính xác. Chúng tôi không chịu trách nhiệm nếu giao thất bại do thông tin sai hoặc người nhận không nghe máy sau nhiều lần liên hệ hợp lý.",
    ],
  },
  {
    id: "5",
    title: "Đổi trả và bảo hành phụ kiện",
    paragraphs: [
      "Đổi trả do lỗi nhà sản xuất hoặc sai hàng so với đơn: liên hệ trong vòng bảy (07) ngày kể từ khi nhận hàng, giữ bao bì và bằng chứng (ảnh/video). Chúng tôi hỗ trợ đổi hàng tương đương hoặc phương án khác tùy tồn kho.",
      "Không áp dụng đổi trả nếu sản phẩm đã qua sử dụng sai hướng dẫn, vượt tải trọng an toàn, hao mòn tự nhiên, hoặc hư hỏng do người dùng — phù hợp với điều khoản miễn trừ liên quan phụ kiện trên trang Điều khoản sử dụng.",
      "Bảo hành (nếu có ghi trên sản phẩm/bao bì) thực hiện theo điều kiện nhà sản xuất hoặc thông báo kèm đơn.",
    ],
  },
  {
    id: "6",
    title: "Mã redeem và ưu đãi thử thách",
    paragraphs: [
      "Mã redeem / mã ưu đãi có điều kiện riêng (thời hạn, sản phẩm áp dụng, tỷ lệ giảm). Mã không được bán lại, chuyển nhượng trái phép hoặc gian lận (ví dụ giả mạo kết quả thử thách).",
      "Ưu đãi từ thử thách chống đẩy dựa trên kết quả phiên đã ghi nhận và ticket ký số. Áp dụng trực tiếp trên giỏ hàng, tối đa 1 ngày, 1 lần cho một đơn, không chuyển nhượng. Đóng tab hoặc trình duyệt thì mất phiếu trên máy. Hệ thống từ chối ticket hết hạn, giả mạo hoặc đã dùng.",
      "Mã hết hạn hoặc đã dùng hết lượt sẽ không còn hiệu lực.",
    ],
  },
  {
    id: "7",
    title: "Thanh toán gói dịch vụ / cổng thanh toán",
    paragraphs: [
      "Khi tính năng thanh toán gói (ví dụ qua VNPay) được bật, bạn sẽ được chuyển tới trang thanh toán của nhà cung cấp. Trạng thái giao dịch có thể là thành công hoặc thất bại theo phản hồi từ cổng thanh toán.",
      "Hệ thống hiện không hoàn tiền tự động trên mọi giao dịch. Nếu cần hoàn tiền theo chính sách hoặc lỗi kỹ thuật, hãy gửi yêu cầu tới email liên hệ kèm mã giao dịch; chúng tôi sẽ xem xét và phản hồi trong thời gian hợp lý.",
    ],
  },
  {
    id: "8",
    title: "Khiếu nại và liên hệ",
    paragraphs: [
      `Khiếu nại về đơn hàng, giao nhận, đổi trả hoặc thanh toán: ${LEGAL_CONTACT_EMAIL} hoặc Zalo ${LEGAL_CONTACT_ZALO}.`,
      `Phiên bản chính sách: ${SALES_POLICY_VERSION}. Chúng tôi có thể cập nhật nội dung; bản mới được công bố trên trang này.`,
    ],
  },
];
