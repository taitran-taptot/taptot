/** Shared legal routes and entity placeholders (fill MST / registered name later). */

import {
  BRAND_NAME,
  CONTACT_EMAIL,
  CONTACT_ZALO_DISPLAY,
  CONTACT_ZALO_HREF,
} from "@/lib/brand";

export const TERMS_HREF = "/dieu-khoan";
export const PRIVACY_HREF = "/chinh-sach-bao-mat";
export const SALES_POLICY_HREF = "/chinh-sach-ban-hang";

/** Display brand; replace LEGAL_ENTITY_NAME when a registered company is confirmed. */
export const LEGAL_BRAND = BRAND_NAME;

/** Placeholder — replace with registered company / hộ kinh doanh name. */
export const LEGAL_ENTITY_NAME = "TAPTOT (đơn vị vận hành sẽ cập nhật tên pháp nhân đăng ký)";

/** Placeholder — mã số thuế / MST. */
export const LEGAL_TAX_ID = "Đang cập nhật";

/** Placeholder — địa chỉ trụ sở / liên hệ chính thức. */
export const LEGAL_ADDRESS = "TP. Hồ Chí Minh, Việt Nam";

export const LEGAL_CONTACT_EMAIL = CONTACT_EMAIL;
export const LEGAL_CONTACT_ZALO = CONTACT_ZALO_DISPLAY;
export const LEGAL_CONTACT_ZALO_HREF = CONTACT_ZALO_HREF;

export type LegalSection = {
  id: string;
  title: string;
  paragraphs: string[];
  bullets?: string[];
};
