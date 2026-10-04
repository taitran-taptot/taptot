export const SHARE_SLUG_MIN = 3;
export const SHARE_SLUG_MAX = 48;
const SHARE_SLUG_RE = /^[a-z0-9][a-z0-9-]{1,46}[a-z0-9]$/;

export function sanitizeShareSlugInput(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "");
}

export function isValidShareSlug(raw: string): boolean {
  const s = (raw || "").trim().toLowerCase();
  if (!s) return true;
  return SHARE_SLUG_RE.test(s);
}

export function shareSlugError(raw: string): string {
  const s = (raw || "").trim().toLowerCase();
  if (!s) return "";
  if (!SHARE_SLUG_RE.test(s)) {
    return "Slug 3–48 ký tự: a-z, 0-9, dấu gạch ngang; không bắt đầu/kết thúc bằng '-'.";
  }
  return "";
}
