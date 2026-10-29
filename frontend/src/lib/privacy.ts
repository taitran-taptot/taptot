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
export const PRIVACY_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 25 tháng 10 năm 2026.";
export const PRIVACY_VERSION = "2026-10-25";

export const PRIVACY_INTRO =
  `Chính sách này mô tả cách ${LEGAL_BRAND} thu thập, sử dụng, lưu trữ và bảo vệ dữ liệu cá nhân khi bạn dùng website. Nội dung căn cứ Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 và Nghị định 356/2025/NĐ-CP, có hiệu lực từ ngày 01 tháng 01 năm 2026. Đây là bản công khai để bạn đọc trước khi dùng dịch vụ, không thay thế ý kiến luật sư.`;

export const PRIVACY_SECTIONS: LegalSection[] = [
  {
    id: "1",
    title: "Bên xử lý dữ liệu",
    paragraphs: [
      `Dữ liệu được xử lý bởi đơn vị vận hành thương hiệu ${LEGAL_BRAND}.`,
      `Tên pháp nhân / đơn vị: ${LEGAL_ENTITY_NAME}.`,
      `Mã số thuế: ${LEGAL_TAX_ID}.`,
      `Địa chỉ liên hệ: ${LEGAL_ADDRESS}.`,
      `Email về dữ liệu cá nhân: ${LEGAL_CONTACT_EMAIL}.`,
    ],
  },
  {
    id: "2",
    title: "Dữ liệu thông thường",
    paragraphs: ["Tùy tính năng bạn dùng, chúng tôi có thể thu thập:"],
    bullets: [
      "Tài khoản: họ tên hiển thị, email, mật khẩu đã băm, cookie phiên đăng nhập.",
      "Đăng nhập Google hoặc Facebook, nếu bạn chọn cách này: định danh mà nhà cung cấp trả về trong phạm vi bạn cho phép.",
      "Đơn phụ kiện: họ tên người nhận, số điện thoại, địa chỉ giao hàng, ghi chú đơn, mã đơn và mã ưu đãi nếu có.",
      "Liên hệ huấn luyện viên và góp ý: họ tên, số điện thoại hoặc Zalo, email, tuổi nếu bạn ghi, và nội dung tin nhắn.",
      "Nhật ký lỗi và máy chủ ở mức cần cho vận hành và bảo mật.",
    ],
  },
  {
    id: "3",
    title: "Dữ liệu sức khỏe và thể trạng",
    paragraphs: [
      "Khi tạo lịch hoặc làm kiểm tra thể lực, chúng tôi có thể xử lý giới tính, tuổi, chiều cao, cân nặng, mục tiêu tập, dụng cụ đang có, ghi chú sức khỏe hoặc hạn chế vận động, chỉ số kiểm tra (chống đẩy, kéo xà, plank) cùng lịch tập và thực đơn gắn với tài khoản hoặc phiên của bạn.",
      "Ghi chú sức khỏe, hạn chế vận động và kết quả kiểm tra thể lực được xử lý như dữ liệu về tình trạng sức khỏe. Chúng tôi chỉ dùng các dữ liệu này để lọc bài tập, lập lịch, thực đơn và lưu phiên kiểm tra thể lực mà bạn đã yêu cầu.",
      "Cơ sở xử lý là sự đồng ý của bạn khi tick xác nhận trước lúc tạo lịch hoặc làm thử thách, và việc dữ liệu này cần thiết để tạo đúng nội dung bạn yêu cầu. Bạn có thể không điền ghi chú sức khỏe; khi đó bộ lọc chấn thương sẽ không có thông tin đó.",
    ],
  },
  {
    id: "4",
    title: "Mục đích xử lý",
    paragraphs: ["Chúng tôi xử lý dữ liệu để:"],
    bullets: [
      "Tạo và hiển thị lịch tập, thực đơn và nội dung tham khảo.",
      "Quản lý tài khoản, xác thực và khôi phục mật khẩu.",
      "Nhận đơn phụ kiện, mã ưu đãi, giao hàng và đối soát chuyển khoản hoặc COD.",
      "Phản hồi form liên hệ huấn luyện viên, góp ý và yêu cầu hỗ trợ.",
      "Bảo mật, chống gian lận mã ưu đãi hoặc kết quả thử thách, và thực hiện nghĩa vụ pháp lý.",
      "Cải thiện sản phẩm ở dạng thống kê nội bộ khi phù hợp.",
    ],
  },
  {
    id: "5",
    title: "Camera và nhận diện chuyển động",
    paragraphs: [
      "Thử thách chống đẩy hoặc plank có thể xin quyền camera trên thiết bị của bạn.",
      "Nhận diện tư thế chạy trên chính thiết bị đó. Chúng tôi không tải khung hình hay video camera lên máy chủ để nhận diện.",
      "Máy chủ chỉ nhận số liệu của phiên: số lần hoặc thời gian, địa chỉ IP và mã ưu đãi đã ký. Bạn có thể từ chối camera; khi đó đếm tự động không chạy.",
    ],
  },
  {
    id: "6",
    title: "Cookie",
    paragraphs: [
      "Hệ thống dùng cookie phiên HttpOnly để giữ đăng nhập. Đây là cookie cần cho dịch vụ, không phải cookie quảng cáo.",
      "Nếu trình duyệt chặn cookie phiên, bạn có thể không đăng nhập được.",
    ],
  },
  {
    id: "7",
    title: "Bên xử lý hộ và dữ liệu ra ngoài Việt Nam",
    paragraphs: [
      "Tùy cách bạn dùng và cách hệ thống được cấu hình, dữ liệu có thể đi qua:",
    ],
    bullets: [
      "Google hoặc Facebook, chỉ khi bạn đăng nhập bằng tài khoản của họ.",
      "Dịch vụ gửi email giao dịch hoặc email xác minh.",
      "Google Sheets, khi góp ý hoặc đơn hàng được cấu hình để đồng bộ sang bảng tính.",
      "Thư viện nhận diện chuyển động tải về trình duyệt, ví dụ MediaPipe. Thư viện này chạy trên máy bạn.",
    ],
  },
  {
    id: "8",
    title: "Chuyển dữ liệu ra nước ngoài",
    paragraphs: [
      "Google, Facebook và Google Sheets có thể xử lý dữ liệu trên máy chủ ngoài Việt Nam. Chúng tôi không khẳng định đã nộp hồ sơ đánh giá tác động chuyển dữ liệu xuyên biên giới.",
      "Đơn hàng và lịch tập được lưu trên hạ tầng Chúng tôi đang dùng để vận hành website. Nếu hạ tầng đó đặt ngoài Việt Nam, việc lưu trữ cũng là chuyển dữ liệu ra nước ngoài trong phạm vi cần để cung cấp dịch vụ.",
    ],
  },
  {
    id: "9",
    title: "Liên kết chia sẻ lịch",
    paragraphs: [
      "Ai có liên kết chia sẻ đều xem được nội dung lịch, gồm các chỉ số thể trạng đang hiện trên lịch đó. Hãy coi liên kết là thông tin riêng và chỉ gửi cho người bạn tin.",
    ],
  },
  {
    id: "10",
    title: "Thời gian lưu và xóa",
    paragraphs: [
      "Lịch tập bị xóa sau 4 tháng dương lịch kể từ ngày tạo, kể cả khi đã gắn tài khoản. Lịch mẫu công khai được ghim có thể được giữ lâu hơn.",
      "Dữ liệu tài khoản và đơn hàng được giữ trong thời gian cần để giao hàng, đối soát, giải quyết khiếu nại và lưu chứng từ theo pháp luật. Chúng tôi không ấn định một số năm cố định trên trang này khi chưa có căn cứ lưu trữ riêng.",
      `Bạn có thể yêu cầu xóa hoặc xem dữ liệu bằng email tới ${LEGAL_CONTACT_EMAIL}. Chúng tôi trả lời trong thời gian hợp lý. Phần dữ liệu pháp luật yêu cầu giữ lại sẽ không bị xóa hết.`,
    ],
  },
  {
    id: "11",
    title: "Quyền của bạn",
    paragraphs: [
      "Theo Luật Bảo vệ dữ liệu cá nhân, bạn có thể yêu cầu:",
    ],
    bullets: [
      "Được biết và xem dữ liệu cá nhân của bạn mà chúng tôi đang xử lý.",
      "Sửa thông tin sai.",
      "Xóa hoặc hạn chế xử lý khi đủ điều kiện.",
      "Rút đồng ý đối với phần xử lý dựa trên đồng ý. Việc rút đồng ý không làm mất hiệu lực của xử lý đã diễn ra trước đó.",
      "Khiếu nại với Chúng tôi qua trang Khiếu nại, hoặc với cơ quan nhà nước có thẩm quyền về bảo vệ dữ liệu cá nhân.",
    ],
  },
  {
    id: "12",
    title: "Trẻ em",
    paragraphs: [
      "Dịch vụ không dành cho người dưới 16 tuổi. Chúng tôi không cố ý thu thập dữ liệu của trẻ dưới 16 tuổi. Nếu phát hiện, chúng tôi sẽ xóa hoặc hạn chế xử lý khi có thể.",
    ],
  },
  {
    id: "13",
    title: "Liên hệ và bản cập nhật",
    paragraphs: [
      `Yêu cầu về dữ liệu cá nhân: ${LEGAL_CONTACT_EMAIL}.`,
      `Phiên bản hiện hành: ${PRIVACY_VERSION}. Ngày cập nhật ghi ở đầu trang. Bạn tiếp tục dùng dịch vụ sau khi chính sách đổi nghĩa là bạn đã biết nội dung mới, trừ khi pháp luật yêu cầu cách thông báo khác.`,
    ],
  },
];
