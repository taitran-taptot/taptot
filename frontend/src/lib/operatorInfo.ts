import {
  CONTACT_FACEBOOK_DISPLAY,
  CONTACT_PHONE_DISPLAY,
  CONTACT_TIKTOK_DISPLAY,
} from "@/lib/brand";
import {
  LEGAL_ADDRESS,
  LEGAL_BRAND,
  LEGAL_CONTACT_EMAIL,
  LEGAL_CONTACT_ZALO,
  LEGAL_ENTITY_NAME,
  LEGAL_TAX_ID,
  OPERATOR_HREF,
} from "@/lib/legalMeta";
import type { LegalSection } from "@/lib/legalMeta";

export { OPERATOR_HREF };

export const OPERATOR_TITLE = "Thông tin đơn vị vận hành";
export const OPERATOR_UPDATED_LABEL = "Cập nhật lần cuối: Ngày 25 tháng 10 năm 2026.";
export const OPERATOR_VERSION = "2026-10-25";

export const OPERATOR_INTRO =
  `Trang này công khai đơn vị đứng tên website ${LEGAL_BRAND}. Phần tên đăng ký, mã số thuế và địa chỉ trụ sở vẫn đang cập nhật; chưa điền số liệu giả.`;

export const OPERATOR_SECTIONS: LegalSection[] = [
  {
    id: "1",
    title: "Thương hiệu và liên hệ",
    paragraphs: [
      `Tên thương hiệu trên website: ${LEGAL_BRAND}.`,
      `Email: ${LEGAL_CONTACT_EMAIL}.`,
      `Điện thoại và Zalo: ${CONTACT_PHONE_DISPLAY} (Zalo ${LEGAL_CONTACT_ZALO}).`,
      `Facebook: ${CONTACT_FACEBOOK_DISPLAY}. TikTok: ${CONTACT_TIKTOK_DISPLAY}.`,
    ],
  },
  {
    id: "2",
    title: "Đơn vị đứng tên",
    paragraphs: [
      `Tên pháp nhân hoặc hộ kinh doanh: ${LEGAL_ENTITY_NAME}.`,
      `Mã số thuế: ${LEGAL_TAX_ID}.`,
      `Địa chỉ: ${LEGAL_ADDRESS}.`,
      "Khi có giấy đăng ký, các dòng trên sẽ được thay bằng đúng tên, mã số thuế và địa chỉ trên giấy tờ. Trước thời điểm đó, hãy liên hệ bằng email hoặc Zalo ở mục 1.",
    ],
  },
  {
    id: "3",
    title: "Việc website đang làm",
    paragraphs: [
      "TAPTOT tự cung cấp công cụ tạo lịch tập, thực đơn, bài viết kiến thức và kiểm tra thể lực. TAPTOT cũng tự bán phụ kiện thể thao trên gian hàng của mình.",
      "Người mua đặt hàng trực tiếp với TAPTOT. Website không cho tổ chức hay cá nhân khác mở gian hàng để bán hàng hoặc bán dịch vụ.",
      "Form liên hệ huấn luyện viên chỉ nhận yêu cầu hỗ trợ. Form đó không biến website thành sàn môi giới huấn luyện.",
    ],
  },
  {
    id: "4",
    title: "Giấy tờ sẽ được bổ sung",
    paragraphs: [
      "Thông báo hoạt động thương mại điện tử với cơ quan nhà nước, nếu phát sinh nghĩa vụ, sẽ được thực hiện sau khi có tên và mã số thuế. Trang này không đăng số xác nhận chưa được cấp.",
      `Phiên bản: ${OPERATOR_VERSION}.`,
    ],
  },
];
