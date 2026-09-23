/** Format and read sticker gift codes (TT-XXXX-XXXX) plus the reusable test code `1`. */

export const DEV_TEST_GIFT_CODE = "1";

export function compactGiftCode(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

export function isDevTestGiftCode(raw: string): boolean {
  return compactGiftCode(raw) === DEV_TEST_GIFT_CODE;
}

export function formatGiftCodeInput(raw: string): string {
  const compact = compactGiftCode(raw);
  if (compact === DEV_TEST_GIFT_CODE) return DEV_TEST_GIFT_CODE;
  let body = compact.startsWith("TT") ? compact.slice(2) : compact;
  body = body.slice(0, 8);
  if (!body) return "";
  if (body.length <= 4) return `TT-${body}`;
  return `TT-${body.slice(0, 4)}-${body.slice(4)}`;
}

export function giftCodeFromQuery(): string {
  if (typeof window === "undefined") return "";
  return formatGiftCodeInput(new URLSearchParams(window.location.search).get("code") || "");
}

export function giftCodeFromPathname(pathname: string): string {
  const match = pathname.match(/\/batdau\/([^/?#]+)/i);
  if (!match) return "";
  try {
    return formatGiftCodeInput(decodeURIComponent(match[1]));
  } catch {
    return formatGiftCodeInput(match[1]);
  }
}

export function giftStartHref(code: string, _loggedIn?: boolean): string {
  const formatted = formatGiftCodeInput(code);
  if (!formatted) return "/batdau";
  return `/batdau/${encodeURIComponent(formatted)}`;
}

export function giftCodeReady(code: string): boolean {
  const formatted = formatGiftCodeInput(code);
  if (formatted === DEV_TEST_GIFT_CODE) return true;
  return formatted.replace(/-/g, "").length >= 10;
}
