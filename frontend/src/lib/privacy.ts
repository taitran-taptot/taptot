import {
  LEGAL_ADDRESS,
  LEGAL_BRAND,
  LEGAL_CONTACT_EMAIL,
  LEGAL_ENTITY_NAME,
  LEGAL_TAX_ID,
  PRIVACY_HREF,
} from "@/lib/legalMeta";
import type { LegalSection } from "@/lib/legalMeta";

export { PRIVACY_HREF };

export const PRIVACY_TITLE = "Chính sách bảo mật và bảo vệ dữ liệu cá nhân";
export const PRIVACY_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 23 tháng 09 năm 2026.";
export const PRIVACY_VERSION = "2026-09-23";

export const PRIVACY_INTRO =
  `Chính sách này giải thích cách ${LEGAL_BRAND} thu thập, sử dụng, lưu trữ và bảo vệ dữ liệu cá nhân khi bạn dùng website và dịch vụ liên quan. Việc sử dụng dịch vụ đồng nghĩa với việc bạn đã đọc chính sách này. Nội dung dưới đây là khung vận hành sản phẩm; không thay thế tư vấn pháp lý chuyên sâu.`;

export const PRIVACY_SECTIONS: LegalSection[] = [
  {
    id: "1",
    title: "Bên kiểm soát dữ liệu",
    paragraphs: [
      `Dữ liệu được xử lý bởi đơn vị vận hành thương hiệu ${LEGAL_BRAND}.`,
      `Tên pháp nhân / đơn vị: ${LEGAL_ENTITY_NAME}.`,
      `Mã số thuế (MST): ${LEGAL_TAX_ID}.`,
      `Địa chỉ liên hệ: ${LEGAL_ADDRESS}.`,
      `Email liên hệ về dữ liệu cá nhân: ${LEGAL_CONTACT_EMAIL}.`,
    ],
  },
  {
    id: "2",
    title: "Dữ liệu chúng tôi thu thập",
    paragraphs: [
      "Tùy tính năng bạn dùng, chúng tôi có thể thu thập:",
    ],
    bullets: [
      "Tài khoản: họ tên hiển thị, email, mật khẩu đã băm; cookie phiên đăng nhập.",
      "Đăng nhập mạng xã hội (nếu được bật): định danh do Google/Facebook cung cấp theo phạm vi bạn cho phép.",
      "Thể trạng và tập luyện: giới tính, tuổi, chiều cao, cân nặng, mục tiêu, thiết bị, ghi chú sức khỏe, chỉ số baseline (chống đẩy, kéo xà, plank…), lịch tập và thực đơn gắn với tài khoản hoặc phiên khách.",
      "Thương mại: thông tin đơn hàng phụ kiện, ghi chú đơn, mã redeem / ưu đãi (nếu có).",
      "Liên hệ HLV và góp ý: họ tên, số điện thoại/Zalo, email, tuổi (nếu bạn cung cấp), nội dung tin nhắn; góp ý có thể được đồng bộ sang công cụ nội bộ (ví dụ Google Sheets).",
      "Thử thách chống đẩy: số lần đếm được, thời gian phiên, địa chỉ IP và mã ưu đãi ký số — không lưu video camera.",
      "Dữ liệu kỹ thuật tối thiểu: nhật ký lỗi/máy chủ phục vụ vận hành và bảo mật.",
    ],
  },
  {
    id: "3",
    title: "Mục đích xử lý",
    paragraphs: [
      "Chúng tôi xử lý dữ liệu để:",
    ],
    bullets: [
      "Tạo và hiển thị lịch tập, thực đơn, lời khuyên tham khảo.",
      "Quản lý tài khoản, xác thực, khôi phục mật khẩu.",
      "Xử lý đơn hàng phụ kiện, mã ưu đãi và (khi bật) thanh toán gói dịch vụ.",
      "Phản hồi liên hệ HLV, góp ý và hỗ trợ khách hàng.",
      "Bảo mật, chống gian lận, tuân thủ nghĩa vụ pháp lý.",
      "Cải thiện sản phẩm ở mức tổng hợp / nội bộ khi phù hợp.",
    ],
  },
  {
    id: "4",
    title: "Camera và nhận diện chuyển động",
    paragraphs: [
      "Một số thử thách (ví dụ đếm chống đẩy) có thể yêu cầu quyền camera trên thiết bị của bạn.",
      "Việc nhận diện tư thế (pose) được xử lý trên thiết bị của bạn thông qua thư viện chạy cục bộ. Chúng tôi không tải lên máy chủ các khung hình hay video từ camera cho mục đích nhận diện.",
      "Máy chủ chỉ nhận kết quả phiên ở dạng số liệu đã nêu (số lần, thời gian, IP, ticket ưu đãi). Bạn có thể từ chối cấp quyền camera; khi đó tính năng đếm tự động sẽ không hoạt động.",
    ],
  },
  {
    id: "5",
    title: "Cookie và phiên đăng nhập",
    paragraphs: [
      "Hiện tại Hệ thống chủ yếu dùng cookie phiên HttpOnly (ví dụ cookie truy cập và làm mới phiên) để duy trì trạng thái đăng nhập. Đây là cookie cần thiết cho dịch vụ, không phải cookie quảng cáo bên thứ ba.",
      "Trình duyệt của bạn có thể cho phép xóa hoặc chặn cookie; nếu chặn cookie phiên, bạn có thể không đăng nhập được.",
    ],
  },
  {
    id: "6",
    title: "Bên thứ ba và xử lý hộ",
    paragraphs: [
      "Tùy cấu hình vận hành, dữ liệu có thể được xử lý bởi hoặc truyền qua:",
    ],
    bullets: [
      "Nhà cung cấp mô hình AI (ví dụ OpenAI) khi tạo nội dung lịch/gợi ý — chỉ trong phạm vi cần thiết để sinh kết quả.",
      "Nhà cung cấp đăng nhập Google/Facebook (nếu bạn chọn đăng nhập bằng OAuth).",
      "Dịch vụ gửi email giao dịch / xác minh.",
      "Công cụ bảng tính hoặc webhook nội bộ cho góp ý (ví dụ Google Sheets).",
      "CDN / thư viện nhận diện chuyển động tải về trình duyệt (ví dụ MediaPipe).",
      "Cổng thanh toán (ví dụ VNPay) khi bạn thanh toán gói dịch vụ trực tuyến.",
    ],
  },
  {
    id: "7",
    title: "Liên kết chia sẻ lịch",
    paragraphs: [
      "Lịch có thể được xem qua liên kết mang token chia sẻ. Ai có liên kết đều có thể xem nội dung lịch đó. Hãy coi liên kết như thông tin nhạy cảm và chỉ gửi cho người bạn tin tưởng.",
    ],
  },
  {
    id: "8",
    title: "Lưu trữ và xóa",
    paragraphs: [
      "Mọi lịch tập bị xóa tự động sau khoảng 110 ngày kể từ khi tạo, kể cả khi đã gắn tài khoản.",
      "Dữ liệu tài khoản và đơn hàng được lưu trong thời gian cần thiết để cung cấp dịch vụ, giải quyết khiếu nại và tuân thủ pháp luật.",
      `Bạn có thể yêu cầu xóa hoặc xuất dữ liệu cá nhân bằng cách gửi email tới ${LEGAL_CONTACT_EMAIL}. Chúng tôi sẽ phản hồi trong thời gian hợp lý, trừ khi pháp luật yêu cầu giữ lại một phần dữ liệu.`,
    ],
  },
  {
    id: "9",
    title: "Quyền của bạn",
    paragraphs: [
      "Trong phạm vi pháp luật Việt Nam về bảo vệ dữ liệu cá nhân, bạn có thể yêu cầu:",
    ],
    bullets: [
      "Được biết / truy cập dữ liệu cá nhân liên quan đến bạn mà chúng tôi đang xử lý.",
      "Sửa thông tin không chính xác.",
      "Xóa hoặc hạn chế xử lý khi đủ điều kiện.",
      "Rút đồng ý đối với xử lý dựa trên đồng ý (không ảnh hưởng tính hợp pháp của xử lý trước đó).",
    ],
  },
  {
    id: "10",
    title: "Trẻ em",
    paragraphs: [
      "Dịch vụ không dành cho người dưới 16 tuổi. Chúng tôi không cố ý thu thập dữ liệu của trẻ dưới 16 tuổi. Nếu phát hiện, chúng tôi sẽ xóa hoặc hạn chế xử lý khi hợp lý.",
    ],
  },
  {
    id: "11",
    title: "Liên hệ",
    paragraphs: [
      `Mọi yêu cầu về bảo mật và dữ liệu cá nhân: ${LEGAL_CONTACT_EMAIL}.`,
    ],
  },
  {
    id: "12",
    title: "Cập nhật chính sách",
    paragraphs: [
      `Chúng tôi có thể cập nhật chính sách này. Phiên bản hiện hành: ${PRIVACY_VERSION}. Ngày cập nhật được ghi trên đầu trang. Việc tiếp tục sử dụng dịch vụ sau khi cập nhật đồng nghĩa với việc bạn đã biết nội dung mới, trừ khi pháp luật yêu cầu hình thức thông báo khác.`,
    ],
  },
];
