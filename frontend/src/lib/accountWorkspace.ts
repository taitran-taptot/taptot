import { isAdmin, isHlv } from "./auth";

export type AccountTabId =
  | "ke-hoach"
  | "doi-mat-khau"
  | "tao-hlv"
  | "thong-ke"
  | "bai-tap"
  | "dung-cu"
  | "thuc-an"
  | "bai-viet"
  | "san-pham"
  | "don-hang";

export const ADMIN_DEFAULT_TAB: AccountTabId = "thong-ke";
export const HLV_DEFAULT_TAB: AccountTabId = "ke-hoach";

export const HLV_TABS: AccountTabId[] = ["ke-hoach", "bai-tap", "thuc-an", "doi-mat-khau"];

export const ADMIN_TABS: AccountTabId[] = [
  "ke-hoach",
  "doi-mat-khau",
  "tao-hlv",
  "thong-ke",
  "bai-tap",
  "dung-cu",
  "thuc-an",
  "bai-viet",
  "san-pham",
  "don-hang",
];

export type AccountNavItem = {
  tab: AccountTabId;
  label: string;
  short: string;
  icon: string;
};

const NAV_BY_TAB: Record<AccountTabId, Omit<AccountNavItem, "tab">> = {
  "ke-hoach": { label: "Lịch của tôi", short: "Lịch", icon: "/ke-hoach" },
  "doi-mat-khau": { label: "Đổi mật khẩu", short: "Mật khẩu", icon: "/ho-so" },
  "tao-hlv": { label: "Tạo HLV", short: "HLV", icon: "/dang-nhap" },
  "thong-ke": { label: "Thống kê", short: "Thống kê", icon: "/quan-tri/thong-ke" },
  "bai-tap": { label: "Quản trị bài tập", short: "Bài tập", icon: "/quan-tri/bai-tap" },
  "dung-cu": { label: "Quản trị dụng cụ", short: "Dụng cụ", icon: "/quan-tri/dung-cu" },
  "thuc-an": { label: "Quản trị thức ăn", short: "Thức ăn", icon: "/quan-tri/thuc-an" },
  "bai-viet": { label: "Quản trị bài nấu", short: "Bài nấu", icon: "/quan-tri/bai-viet" },
  "san-pham": { label: "Quản trị sản phẩm", short: "Sản phẩm", icon: "/quan-tri/san-pham" },
  "don-hang": { label: "Quản trị đơn hàng", short: "Đơn hàng", icon: "/quan-tri/don-hang" },
};

const LEGACY_PATHS: Array<{ prefix: string; tab: AccountTabId }> = [
  { prefix: "/tai-khoan/quan-tri/thong-ke", tab: "thong-ke" },
  { prefix: "/tai-khoan/quan-tri/bai-tap", tab: "bai-tap" },
  { prefix: "/tai-khoan/quan-tri/dung-cu", tab: "dung-cu" },
  { prefix: "/tai-khoan/quan-tri/thuc-an", tab: "thuc-an" },
  { prefix: "/tai-khoan/quan-tri/bai-viet", tab: "bai-viet" },
  { prefix: "/tai-khoan/quan-tri/san-pham", tab: "san-pham" },
  { prefix: "/tai-khoan/quan-tri/don-hang", tab: "don-hang" },
  { prefix: "/tai-khoan/quan-tri/ma-qua-tang", tab: "don-hang" },
  { prefix: "/tai-khoan/ke-hoach", tab: "ke-hoach" },
  { prefix: "/tai-khoan/doi-mat-khau", tab: "doi-mat-khau" },
  { prefix: "/tai-khoan/ho-so", tab: "doi-mat-khau" },
];

export function accountTabsForRole(role?: string | null): AccountTabId[] {
  if (isAdmin(role)) return ADMIN_TABS;
  if (isHlv(role)) return HLV_TABS;
  return ["ke-hoach", "doi-mat-khau"];
}

export function accountNavItems(role?: string | null): AccountNavItem[] {
  return accountTabsForRole(role).map((tab) => ({ tab, ...NAV_BY_TAB[tab] }));
}

export function accountShellPath(role?: string | null): string {
  return isAdmin(role) ? "/tai-khoan/quan-tri" : "/tai-khoan";
}

export function defaultAccountTab(role?: string | null): AccountTabId {
  return isAdmin(role) ? ADMIN_DEFAULT_TAB : HLV_DEFAULT_TAB;
}

export function isAccountShellPath(pathname: string): boolean {
  const p = pathname.replace(/\/$/, "") || "/";
  return p === "/tai-khoan" || p === "/tai-khoan/quan-tri";
}

export function parseAccountTab(raw: string | null | undefined, role?: string | null): AccountTabId {
  const allowed = accountTabsForRole(role);
  const fallback = defaultAccountTab(role);
  if (raw && allowed.includes(raw as AccountTabId)) return raw as AccountTabId;
  return fallback;
}

export function accountShellHref(role?: string | null, tab?: string | null): string {
  return `${accountShellPath(role)}?tab=${parseAccountTab(tab, role)}`;
}

export function tabFromLegacyPath(pathname: string): AccountTabId | null {
  const p = pathname.replace(/\/$/, "") || "/";
  if (isAccountShellPath(p)) return null;
  for (const row of LEGACY_PATHS) {
    if (p === row.prefix || p.startsWith(`${row.prefix}/`)) return row.tab;
  }
  return null;
}

export function accountTabFromLocation(
  pathname: string,
  searchTab: string | null | undefined,
  role?: string | null,
): AccountTabId {
  if (pathname.startsWith("/tai-khoan/lich")) return "ke-hoach";
  const legacy = tabFromLegacyPath(pathname);
  if (legacy && accountTabsForRole(role).includes(legacy)) return legacy;
  return parseAccountTab(searchTab, role);
}
