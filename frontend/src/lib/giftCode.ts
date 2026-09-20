/** Format and read sticker gift codes (TT-XXXX-XXXX). */

export function formatGiftCodeInput(raw: string): string {
  let compact = raw.toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (compact.startsWith("TT")) compact = compact.slice(2);
  compact = compact.slice(0, 8);
  if (!compact) return "";
  if (compact.length <= 4) return `TT-${compact}`;
  return `TT-${compact.slice(0, 4)}-${compact.slice(4)}`;
}

export function giftCodeFromQuery(): string {
  if (typeof window === "undefined") return "";
  return formatGiftCodeInput(new URLSearchParams(window.location.search).get("code") || "");
}

export function giftStartHref(code: string, loggedIn: boolean): string {
  const q = `code=${encodeURIComponent(code)}`;
  return loggedIn ? `/tai-khoan/batdau?${q}` : `/batdau?${q}`;
}
