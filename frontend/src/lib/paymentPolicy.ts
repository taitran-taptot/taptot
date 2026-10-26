import {
  LEGAL_BRAND,
  LEGAL_CONTACT_EMAIL,
  LEGAL_CONTACT_ZALO,
  PAYMENT_POLICY_HREF,
} from "@/lib/legalMeta";
import type { LegalSection } from "@/lib/legalMeta";

export { PAYMENT_POLICY_HREF };

export const PAYMENT_POLICY_TITLE = "Chính sách thanh toán, hoàn tiền và chấm dứt dịch vụ";
export const PAYMENT_POLICY_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 25 tháng 10 năm 2026.";
export const PAYMENT_POLICY_VERSION = "2026-10-25";

export const PAYMENT_POLICY_INTRO =
  `Chính sách này nói cách trả tiền khi mua phụ kiện trên ${LEGAL_BRAND}, cách hoàn tiền chuyển khoản, và cách bạn nhận lịch tập cùng thực đơn. Gian hàng chỉ nhận tiền hàng của chính TAPTOT.`;

export const PAYMENT_POLICY_SECTIONS: LegalSection[] = [
  {
    id: "1",
    title: "Hai cách thanh toán phụ kiện",
    paragraphs: [
      "Đơn phụ kiện chỉ thanh toán bằng chuyển khoản ngân hàng hoặc COD khi nhận hàng. Bạn chọn một trong hai cách ở bước đặt hàng.",
      "Giá là giá đang hiện trên trang sản phẩm. Phí vận chuyển của đơn do hệ thống tạo hiện bằng không đồng, trừ khi trang sản phẩm ghi khác.",
    ],
  },
  {
    id: "2",
    title: "Chuyển khoản ngân hàng",
    paragraphs: [
      "Sau khi đặt hàng, trang thanh toán hiện mã QR và số tài khoản. Bạn chuyển đúng số tiền và ghi đúng mã đơn vào nội dung chuyển khoản.",
      "Đơn ở trạng thái chờ chuyển khoản cho đến khi người vận hành đối soát và xác nhận tiền đã vào tài khoản. Chưa xác nhận thì đơn chưa được coi là đã trả.",
      "Chuyển sai nội dung, sai số tiền hoặc chuyển từ tài khoản không liên hệ được có thể làm chậm việc ghép giao dịch. Hãy giữ biên lai và báo qua email hoặc Zalo kèm mã đơn.",
    ],
  },
  {
    id: "3",
    title: "COD",
    paragraphs: [
      "COD là trả tiền khi nhận hàng. Trạng thái thanh toán ghi nhận là COD cho đến khi giao xong theo quy trình vận hành.",
      "Nếu bạn không nhận hàng, đơn có thể bị hủy. Tiền chưa thu thì không phát sinh khoản hoàn.",
    ],
  },
  {
    id: "4",
    title: "Hoàn tiền",
    paragraphs: [
      "Hệ thống không hoàn tiền tự động.",
      "Nếu đơn chuyển khoản bị hủy sau khi bạn đã chuyển tiền, hãy gửi yêu cầu tới email liên hệ, kèm mã đơn và bằng chứng chuyển khoản. Chúng tôi hoàn bằng cách chuyển lại vào tài khoản bạn cung cấp sau khi đối soát được giao dịch.",
      "Đơn COD chưa thu tiền thì không có khoản để hoàn. Hàng đã giao và đã trả tiền được hoàn hoặc đổi theo Chính sách bán hàng khi đủ điều kiện đổi trả hoặc khi luật bắt buộc.",
      `Kênh gửi yêu cầu: ${LEGAL_CONTACT_EMAIL} hoặc Zalo ${LEGAL_CONTACT_ZALO}.`,
    ],
  },
  {
    id: "5",
    title: "Lịch tập và thực đơn",
    paragraphs: [
      "Lịch tập và thực đơn là nội dung tạo trên website sau khi bạn điền thông tin và xác nhận điều khoản. Việc tạo lịch không gắn với một khoản thu riêng trên gian hàng phụ kiện.",
      "Bạn xem lịch trên tài khoản hoặc qua liên kết chia sẻ. Lịch bị xóa sau 4 tháng dương lịch kể từ ngày tạo, trừ lịch mẫu công khai được ghim.",
      "Chúng tôi có thể ngừng cho xem lịch nếu bạn vi phạm Điều khoản sử dụng, hoặc khi bạn ngừng dùng và yêu cầu xóa dữ liệu. Nội dung đã hết hạn thì không còn nghĩa vụ cung cấp lại bản cũ.",
      "Lịch và thực đơn không cam kết kết quả tập luyện hay cân nặng.",
    ],
  },
  {
    id: "6",
    title: "Tiền hàng",
    paragraphs: [
      "Số tiền chuyển khoản hoặc COD là tiền mua phụ kiện của TAPTOT. Chúng tôi không nhận hộ, giữ hộ hay chia tiền cho người bán khác trên website này.",
      `Phiên bản: ${PAYMENT_POLICY_VERSION}. Bản mới được đăng trên trang này.`,
    ],
  },
];
