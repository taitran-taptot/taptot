const API_BASE_ABS =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000/api/v1";

/**
 * Browser default: same-origin `/api/v1` (Next rewrites to FastAPI).
 * Server / long AI calls: absolute FastAPI URL (avoids rewrite proxy timeout).
 */
export const API_BASE = typeof window === "undefined" ? API_BASE_ABS : "/api/v1";

/** Direct FastAPI base — use for long-running generate so Next rewrite cannot 30s-timeout. */
export const API_BASE_DIRECT = API_BASE_ABS;

/**
 * Public media root. Browser default is same-origin `/media` (Next rewrites to FastAPI)
 * so photos work on both localhost and 127.0.0.1.
 */
export const MEDIA_BASE =
  process.env.NEXT_PUBLIC_MEDIA_BASE?.replace(/\/$/, "") || "/media";

export const GIF_BASE = process.env.NEXT_PUBLIC_GIF_BASE?.replace(/\/$/, "") || "";

export const PAGE_SIZE = 12;

/** Header Đăng nhập / Đăng ký. Gen AI vẫn dùng được khi false (chỉ ẩn nút). */
export const AUTH_UI_ENABLED = true;

/**
 * true = hiện cổng «Mở khóa lượt tạo lịch» (cần mã tem).
 * false = tạm bỏ cổng để gen thử (khớp REQUIRE_REDEEM_CODE_FOR_GENERATE trên API).
 */
export const REQUIRE_REDEEM_CODE =
  (process.env.NEXT_PUBLIC_REQUIRE_REDEEM_CODE || "true").toLowerCase() !== "false";