"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { clearAuth, getStoredUser, type AuthUser } from "@/lib/auth";
import { LOGOUT_EVENT } from "@/lib/http";
import { BRAND_NAME, BRAND_SLOGAN } from "@/lib/brand";
import AuthMenu from "./AuthMenu";
import BrandWordmark from "./BrandWordmark";
import BrandMark from "./BrandMark";
import Footer from "./Footer";
import TaptotChatPanel, { useTaptotChat } from "./TaptotChatPanel";
import { HOSO_HREFS, KHO_HREFS, pathStartsWithAny } from "@/lib/todayWorkout";

interface NavItem {
  href: string;
  label: string;
  short: string;
  children?: { href: string; label: string }[];
}

/** Public top-nav: three clear product-oriented entry points. */
const NAV: NavItem[] = [
  {
    href: "/kho-bai-tap",
    label: "Khám phá",
    short: "Khám phá",
    children: [
      { href: "/kho-bai-tap", label: "Kho bài tập" },
      { href: "/kho-thuc-pham", label: "Kho thực phẩm" },
      { href: "/kien-thuc", label: "Kho kiến thức" },
    ],
  },
  { href: "/mua-dung-cu", label: "Dụng cụ", short: "Dụng cụ" },
  {
    href: "/ve-chung-toi",
    label: "Cộng đồng",
    short: "Cộng đồng",
    children: [
      { href: "/ve-chung-toi", label: "Về TAPTOT" },
      { href: "/lien-he", label: "Huấn luyện viên" },
      { href: "/kiemtratheluc", label: "Kiểm tra thể lực" },
      { href: "/thu-thach-100-ngay", label: "Thử thách 100 ngày" },
    ],
  },
];

function isTrainerRole(role?: string | null) {
  return role === "trainer" || role === "admin";
}

const ACCOUNT_TABS: NavItem[] = [
  { href: "/tai-khoan", label: "Hôm nay", short: "Hôm nay" },
  { href: "/tai-khoan/ke-hoach", label: "Lịch của tôi", short: "Lịch" },
  {
    href: "/tai-khoan/kho",
    label: "Kho",
    short: "Kho",
    children: [
      { href: "/tai-khoan/bai-tap", label: "Bài tập" },
      { href: "/tai-khoan/thuc-an", label: "Thức ăn" },
      { href: "/tai-khoan/cach-nau", label: "Cách nấu" },
      { href: "/tai-khoan/kien-thuc", label: "Kiến thức" },
      { href: "/tai-khoan/dung-cu", label: "Dụng cụ" },
      { href: "/tai-khoan/mua-dung-cu", label: "Mua dụng cụ" },
      { href: "/tai-khoan/may-tinh-calo", label: "Máy tính calo" },
      { href: "/tai-khoan/batdau", label: `Tạo với ${BRAND_NAME}` },
    ],
  },
  {
    href: "/tai-khoan/ho-so",
    label: "Tài khoản",
    short: "Tài khoản",
    children: [
      { href: "/tai-khoan/doi-mat-khau", label: "Đổi mật khẩu" },
      { href: "/tai-khoan/don-hang", label: "Đơn hàng" },
      { href: "/tai-khoan/gop-y", label: "Góp ý" },
    ],
  },
];

/** Sidebar trong /tai-khoan — 5 mục chính, admin thêm bên dưới */
function buildAccountNav(role?: string | null): NavItem[] {
  const items: NavItem[] = ACCOUNT_TABS.map((n) => ({
    ...n,
    children: n.children ? [...n.children] : undefined,
  }));
  if (!isTrainerRole(role)) {
    const hoso = items.find((i) => i.href === "/tai-khoan/ho-so");
    hoso?.children?.push({ href: "/lien-he", label: "Tìm huấn luyện viên" });
  }
  if (role === "admin") {
    items.push({
      href: "/tai-khoan/quan-tri/bai-tap",
      label: "Quản trị bài tập",
      short: "Admin BT",
    });
    items.push({
      href: "/tai-khoan/quan-tri/bai-viet",
      label: "Quản trị bài viết",
      short: "Admin BV",
    });
    items.push({
      href: "/tai-khoan/quan-tri/thuc-an",
      label: "Quản trị thức ăn",
      short: "Admin TA",
    });
    items.push({
      href: "/tai-khoan/quan-tri/san-pham",
      label: "Quản trị sản phẩm",
      short: "Admin SP",
    });
    items.push({
      href: "/tai-khoan/quan-tri/don-hang",
      label: "Quản trị đơn hàng",
      short: "Admin ĐH",
    });
    items.push({
      href: "/tai-khoan/quan-tri/ma-qua-tang",
      label: "Mã trên tem",
      short: "Tem mã",
    });
    items.push({
      href: "/spec-lich",
      label: "Spec lịch",
      short: "Spec",
    });
  }
  return items;
}

/** Public top-nav — không nhồi Tìm HLV vào 5 tab */
function buildPublicNav(_role?: string | null): NavItem[] {
  void _role;
  return [...NAV];
}

function isActive(pathname: string, href: string, children?: { href: string }[]) {
  if (href === "/tai-khoan") {
    return pathname === "/tai-khoan";
  }
  if (href === "/tai-khoan/ke-hoach") {
    return pathname.startsWith("/tai-khoan/ke-hoach") || pathname.startsWith("/tai-khoan/lich");
  }
  if (href === "/tai-khoan/kho") {
    return pathStartsWithAny(pathname, KHO_HREFS);
  }
  if (href === "/tai-khoan/ho-so") {
    return pathStartsWithAny(pathname, HOSO_HREFS);
  }
  if (href === "/kho-bai-tap" || href === "/bai-tap") {
    return (
      pathname === "/kho-bai-tap" ||
      pathname.startsWith("/kho-bai-tap/") ||
      pathname === "/bai-tap" ||
      pathname.startsWith("/bai-tap/") ||
      pathname === "/dung-cu" ||
      pathname.startsWith("/dung-cu/")
    );
  }
  if (href === "/kho-thuc-pham" || href === "/thuc-an") {
    return (
      pathname === "/thuc-an" ||
      pathname.startsWith("/thuc-an/") ||
      pathname.startsWith("/cach-nau") ||
      pathname === "/kho-thuc-pham" ||
      pathname.startsWith("/kho-thuc-pham/")
    );
  }
  if (href === "/" || href === "/hlv") return pathname === href;
  if (pathname === href || pathname.startsWith(`${href}/`)) return true;
  return !!children?.some((c) => pathname === c.href || pathname.startsWith(`${c.href}/`));
}

function mobileNavItems(items: NavItem[]): { href: string; short: string }[] {
  return items.map((n) => ({ href: n.href, short: n.short }));
}

function Icon({ href, className }: { href: string; className: string }) {
  const key = href
    .replace(/^\/tai-khoan/, "")
    .replace(/\/$/, "") || "/tai-khoan";
  const paths: Record<string, React.ReactNode> = {
    "/": <path d="M3 10.5 12 3l9 7.5M5 9.5V21h14V9.5M9.5 21v-6h5v6" />,
    "/ve-chung-toi": (
      <>
        <circle cx="9" cy="8" r="2.5" />
        <circle cx="16" cy="9" r="2" />
        <path d="M4 19c.8-3 2.8-4.5 5-4.5s4.2 1.5 5 4.5" />
        <path d="M14 19c.4-1.8 1.6-2.8 3.2-2.8 1.4 0 2.5.8 3 2.3" />
      </>
    ),
    "/tai-khoan": (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    "/ke-hoach": (
      <>
        <rect x="4" y="4" width="16" height="16" rx="2" />
        <path d="M8 9h8M8 13h5M8 17h3" />
      </>
    ),
    "/kho": (
      <>
        <path d="M4 8h16v12H4z" />
        <path d="M4 8 12 3l8 5" />
        <path d="M12 8v12" />
      </>
    ),
    "/ho-so": (
      <>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M5 20c1.4-3.5 4-5.5 7-5.5s5.6 2 7 5.5" />
      </>
    ),
    "/dang-nhap": (
      <>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M5 20c1.4-3.5 4-5.5 7-5.5s5.6 2 7 5.5" />
      </>
    ),
    "/batdau": (
      <>
        <rect x="4" y="5" width="16" height="16" rx="2" />
        <path d="M8 3v4M16 3v4M4 10h16M12 13v4M10 15h4" />
      </>
    ),
    "/tao-lich-tap": (
      <>
        <rect x="4" y="5" width="16" height="16" rx="2" />
        <path d="M8 3v4M16 3v4M4 10h16M12 13v4M10 15h4" />
      </>
    ),
    "/bai-tap": <path d="M6.5 6.5h11M6.5 17.5h11M4 9v6M20 9v6M9 12h6" />,
    "/kho-bai-tap": <path d="M6.5 6.5h11M6.5 17.5h11M4 9v6M20 9v6M9 12h6" />,
    "/quan-tri/bai-tap": (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 3v2M12 19v2M5 5l1.5 1.5M17.5 17.5 19 19M3 12h2M19 12h2M5 19l1.5-1.5M17.5 6.5 19 5" />
      </>
    ),
    "/dung-cu": (
      <>
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
      </>
    ),
    "/mua-dung-cu": (
      <>
        <path d="M6 6h15l-1.5 9h-12z" />
        <path d="M6 6 5 3H2" />
        <circle cx="9" cy="20" r="1" />
        <circle cx="18" cy="20" r="1" />
      </>
    ),
    "/gio-hang": (
      <>
        <path d="M6 6h15l-1.5 9h-12z" />
        <path d="M6 6 5 3H2" />
        <circle cx="9" cy="20" r="1" />
        <circle cx="18" cy="20" r="1" />
      </>
    ),
    "/don-hang": (
      <>
        <rect x="5" y="3" width="14" height="18" rx="2" />
        <path d="M8 8h8M8 12h8M8 16h5" />
      </>
    ),
    "/quan-tri/bai-viet": (
      <>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </>
    ),
    "/quan-tri/thuc-an": <path d="M4 3v8a2 2 0 0 0 4 0V3M6 11v10M16 3c-1.5 0-3 2-3 5s1.5 4 3 4 3-1 3-4-1.5-5-3-5Zm0 9v9" />,
    "/quan-tri/san-pham": (
      <>
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      </>
    ),
    "/quan-tri/don-hang": (
      <>
        <rect x="5" y="3" width="14" height="18" rx="2" />
        <path d="M8 8h8M8 12h8M8 16h5" />
      </>
    ),
    "/quan-tri/ma-qua-tang": (
      <>
        <rect x="4" y="4" width="16" height="16" rx="2" />
        <path d="M8 8h3M8 12h8M8 16h5" />
      </>
    ),
    "/cach-nau": <path d="M4 3v8a2 2 0 0 0 4 0V3M6 11v10M16 3c-1.5 0-3 2-3 5s1.5 4 3 4 3-1 3-4-1.5-5-3-5Zm0 9v9" />,
    "/thuc-an": <path d="M4 3v8a2 2 0 0 0 4 0V3M6 11v10M16 3c-1.5 0-3 2-3 5s1.5 4 3 4 3-1 3-4-1.5-5-3-5Zm0 9v9" />,
    "/kho-thuc-pham": <path d="M4 3v8a2 2 0 0 0 4 0V3M6 11v10M16 3c-1.5 0-3 2-3 5s1.5 4 3 4 3-1 3-4-1.5-5-3-5Zm0 9v9" />,
    "/may-tinh-calo": (
      <>
        <rect x="5" y="3" width="14" height="18" rx="2" />
        <path d="M9 7h6M9 11h0M12 11h0M15 11h0M9 15h0M12 15h0M15 15h0" />
      </>
    ),
    "/kien-thuc": <path d="M4 5a2 2 0 0 1 2-2h9v16H6a2 2 0 0 0-2 2V5ZM15 3h3a2 2 0 0 1 2 2v14a2 2 0 0 0-2-2h-3" />,
    "/lien-he": (
      <>
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
      </>
    ),
    "/gop-y": (
      <>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </>
    ),
    "/hlv": (
      <>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6" />
      </>
    ),
    "/hlv/hoc-vien": (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3 20c1.2-3.2 3.6-4.8 6-4.8s4.8 1.6 6 4.8" />
        <path d="M16 4.5a3 3 0 0 1 0 6M18.5 20c-.5-1.6-1.3-2.9-2.4-3.9" />
      </>
    ),
    "/hlv/profile": (
      <>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6" />
        <path d="M19 4v4M17 6h4" />
      </>
    ),
  };
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className} aria-hidden>
      {paths[key] ?? paths["/tai-khoan"] ?? null}
    </svg>
  );
}

function HeaderUserMenu({ user }: { user: AuthUser }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  async function logout() {
    const { authApi } = await import("@/lib/authApi");
    await authApi.logout();
    clearAuth();
    window.dispatchEvent(new CustomEvent(LOGOUT_EVENT));
    router.push("/");
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="max-w-[140px] truncate rounded-lg px-2 py-1.5 text-sm font-semibold text-slate-600 hover:bg-brand-50"
        title={user.email || ""}
      >
        {user.display_name || user.email}
      </button>
      {open && (
        <>
          <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label="Đóng" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full z-50 mt-1 w-52 overflow-hidden rounded-xl border border-slate-100 bg-white py-1 shadow-soft">
            <Link
              href="/tai-khoan/doi-mat-khau"
              className="block px-4 py-2 text-sm font-medium text-slate-600 hover:bg-brand-50 hover:text-brand-600"
              onClick={() => setOpen(false)}
            >
              Đổi mật khẩu
            </Link>
            <Link
              href="/tai-khoan/gop-y"
              className="block px-4 py-2 text-sm font-medium text-slate-600 hover:bg-brand-50 hover:text-brand-600"
              onClick={() => setOpen(false)}
            >
              Góp ý
            </Link>
            {isTrainerRole(user.role) ? (
              <>
                <Link
                  href="/hlv"
                  className="block px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
                  onClick={() => setOpen(false)}
                >
                  HLV — Giao lịch
                </Link>
                <Link
                  href="/hlv/hoc-vien"
                  className="block px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
                  onClick={() => setOpen(false)}
                >
                  Quản lý khách hàng
                </Link>
                <Link
                  href="/hlv/profile"
                  className="block px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
                  onClick={() => setOpen(false)}
                >
                  Hồ sơ HLV
                </Link>
              </>
            ) : (
              <Link
                href="/lien-he"
                className="block px-4 py-2 text-sm font-medium text-slate-600 hover:bg-brand-50 hover:text-brand-600"
                onClick={() => setOpen(false)}
              >
                Tìm huấn luyện viên
              </Link>
            )}
            <button
              type="button"
              onClick={() => void logout()}
              className="w-full px-4 py-2 text-left text-sm font-medium text-rose-600 hover:bg-rose-50"
            >
              Đăng xuất
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function SideNav({ pathname, items }: { pathname: string; items: NavItem[] }) {
  const pathRef = useRef(pathname);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  if (pathRef.current !== pathname) {
    pathRef.current = pathname;
    setOpen({});
  }

  return (
    <aside className="hidden w-56 shrink-0 md:block">
      <nav className="sticky top-20 space-y-1 rounded-2xl bg-white p-3 shadow-soft">
        {items.map((n) => {
          const active = isActive(pathname, n.href, n.children);
          const expanded = n.children ? (open[n.href] ?? active) : false;
          const rowClass = `flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-semibold transition ${
            active ? "bg-brand-50 text-brand-700" : "text-slate-500 hover:bg-brand-50 hover:text-brand-600"
          }`;

          return (
            <div key={n.href}>
              {n.children ? (
                <button
                  type="button"
                  className={rowClass}
                  aria-expanded={expanded}
                  onClick={() => setOpen((prev) => ({ ...prev, [n.href]: !expanded }))}
                >
                  <Icon href={n.href} className="h-5 w-5 shrink-0" />
                  <span className="min-w-0 flex-1">{n.label}</span>
                  <svg
                    className={`h-4 w-4 shrink-0 transition ${expanded ? "rotate-180" : ""}`}
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    aria-hidden
                  >
                    <path d="m6 9 6 6 6-6" />
                  </svg>
                </button>
              ) : (
                <Link href={n.href} className={rowClass}>
                  <Icon href={n.href} className="h-5 w-5 shrink-0" />
                  {n.label}
                </Link>
              )}
              {n.children && expanded && (
                <div className="ml-7 mt-0.5 space-y-0.5 border-l border-slate-100 pl-2">
                  {n.children.map((c) => (
                    <Link
                      key={c.href}
                      href={c.href}
                      className={`block rounded-lg px-2 py-1.5 text-xs font-medium transition ${
                        pathname === c.href || pathname.startsWith(`${c.href}/`)
                          ? "bg-brand-50 font-semibold text-brand-700"
                          : "text-slate-500 hover:text-brand-600"
                      }`}
                    >
                      {c.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}

function AccountLayout({
  user,
  pathname,
  children,
}: {
  user: AuthUser;
  pathname: string;
  children: React.ReactNode;
}) {
  const accountNav = buildAccountNav(user.role);
  const chat = useTaptotChat();
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    setChatOpen(false);
    chat.cancelPending();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only abort in-flight chat on route change
  }, [pathname]);

  return (
    <div className="min-h-screen pb-24 md:pb-0">
      <header className="sticky top-0 z-40 border-b border-slate-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[96rem] items-center justify-between gap-4 px-4">
          <Link href="/tai-khoan" className="flex shrink-0 items-center gap-2">
            <BrandMark className="h-9 w-9 shrink-0" />
            <div className="hidden sm:block">
              <p className="text-lg leading-none font-extrabold tracking-tight">
                <BrandWordmark />
              </p>
              <p className="mt-0.5 text-[11px] leading-none text-slate-400">Tài khoản của bạn</p>
            </div>
          </Link>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-xl bg-brand-50 px-3 py-1.5 text-sm font-semibold text-brand-700 hover:bg-brand-100 xl:hidden"
              onClick={() => setChatOpen(true)}
            >
              Chat {BRAND_NAME}
            </button>
            <HeaderUserMenu user={user} />
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[96rem] gap-5 px-4 py-6">
        <SideNav pathname={pathname} items={accountNav} />
        <main className="min-w-0 flex-1">{children}</main>
        <aside className="sticky top-20 hidden h-[calc(100vh-6rem)] w-[22rem] shrink-0 xl:block xl:w-96">
          <TaptotChatPanel {...chat} inputId="taptot-chat-desktop" />
        </aside>
      </div>

      {chatOpen && (
        <div className="fixed inset-0 z-50 xl:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/40"
            aria-label="Đóng chat"
            onClick={() => setChatOpen(false)}
          />
          <div className="absolute inset-y-0 right-0 flex w-full max-w-md p-3">
            <div className="h-full w-full">
              <TaptotChatPanel
                {...chat}
                inputId="taptot-chat-overlay"
                onClose={() => setChatOpen(false)}
              />
            </div>
          </div>
        </div>
      )}

      <nav className="fixed inset-x-0 bottom-0 z-40 flex border-t border-slate-100 bg-white md:hidden">
        {ACCOUNT_TABS.map((n) => {
          const active = isActive(pathname, n.href, n.children);
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`flex min-w-0 flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium transition ${
                active ? "text-brand-600" : "text-slate-400"
              }`}
            >
              <Icon href={n.href} className="h-6 w-6" />
              {n.short}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [openNav, setOpenNav] = useState<string | null>(null);
  const isPublicTrainerShare = pathname.startsWith("/hlv/p/");
  const isAccount =
    !isPublicTrainerShare &&
    (pathname.startsWith("/tai-khoan") || pathname === "/hlv" || pathname.startsWith("/hlv/"));

  useEffect(() => {
    setUser(getStoredUser());
    setAuthReady(true);
  }, [pathname]);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener(LOGOUT_EVENT, onLogout);
    return () => window.removeEventListener(LOGOUT_EVENT, onLogout);
  }, []);

  useEffect(() => {
    if (!authReady || !isAccount) return;
    if (!getStoredUser()) {
      const next =
        typeof window !== "undefined"
          ? `${pathname}${window.location.search}`
          : pathname;
      router.replace(`/dang-nhap?next=${encodeURIComponent(next)}`);
    }
  }, [authReady, isAccount, pathname, router]);

  useEffect(() => {
    setOpenNav(null);
  }, [pathname]);

  if (isAccount && !authReady) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-slate-400">
        Đang tải tài khoản…
      </div>
    );
  }

  if (isAccount && !user) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-slate-400">
        Đang chuyển hướng đăng nhập…
      </div>
    );
  }

  if (isAccount && user) {
    return (
      <AccountLayout user={user} pathname={pathname}>
        {children}
      </AccountLayout>
    );
  }

  const publicNav = buildPublicNav(user?.role);

  return (
    <div className={`min-h-screen pb-24 md:pb-0 ${pathname === "/" ? "bg-white" : ""}`}>
      <header className="sticky top-0 z-40 border-b border-slate-100 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-[4.5rem] max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link href="/" className="flex shrink-0 items-center gap-2">
            <BrandMark className="h-9 w-9 shrink-0" />
            <div className="hidden sm:block">
              <p className="text-lg leading-none font-extrabold tracking-tight">
                <BrandWordmark />
              </p>
              <p className="mt-0.5 text-[11px] leading-none text-slate-400">{BRAND_SLOGAN}</p>
            </div>
          </Link>

          <nav className="hidden min-w-0 flex-1 flex-nowrap items-center justify-center gap-3 md:flex">
            {publicNav.map((n) => {
              const active = isActive(pathname, n.href, n.children);
              const base = `whitespace-nowrap rounded-lg px-3 py-2 text-[13px] font-semibold transition lg:px-4 lg:text-sm ${
                active
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-600 hover:bg-brand-50 hover:text-brand-700"
              }`;
              if (n.children) {
                const open = openNav === n.href;
                return (
                  <div key={n.href} className="relative shrink-0">
                    <button
                      type="button"
                      className={`${base} inline-flex items-center gap-1`}
                      aria-expanded={open}
                      aria-haspopup="menu"
                      onClick={() => setOpenNav(open ? null : n.href)}
                    >
                      {n.label}
                      <svg
                        className={`h-3.5 w-3.5 shrink-0 transition ${open ? "rotate-180" : ""}`}
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path d="m6 9 6 6 6-6" />
                      </svg>
                    </button>
                    {open && (
                      <>
                        <button
                          type="button"
                          className="fixed inset-0 z-[55] cursor-default"
                          aria-label="Đóng menu"
                          onClick={() => setOpenNav(null)}
                        />
                        <div className="absolute left-0 top-full z-[60] pt-1">
                          <div
                            role="menu"
                            className="min-w-[12rem] overflow-hidden rounded-xl border border-slate-100 bg-white py-1 shadow-soft"
                          >
                            {n.children.map((c) => (
                              <Link
                                key={c.href}
                                href={c.href}
                                role="menuitem"
                                onClick={() => setOpenNav(null)}
                                className={`block whitespace-nowrap px-4 py-2 text-sm font-medium transition hover:bg-brand-50 hover:text-brand-600 ${
                                  pathname === c.href ? "text-brand-700" : "text-slate-600"
                                }`}
                              >
                                {c.label}
                              </Link>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                );
              }
              return (
                <Link key={n.href} href={n.href} className={`${base} shrink-0`}>
                  {n.label}
                </Link>
              );
            })}
          </nav>

          <div className="shrink-0">
            <AuthMenu />
          </div>
        </div>
      </header>

      <main
        className={`mx-auto min-w-0 overflow-x-hidden px-3 sm:px-4 ${
          pathname === "/" ? "max-w-7xl" : "max-w-6xl"
        } ${
          pathname === "/lien-he" ? "py-2 sm:py-3" : "py-6"
        }`}
      >
        {children}
      </main>

      <div
        className={`mx-auto min-w-0 overflow-x-hidden px-3 sm:px-4 ${
          pathname === "/" ? "max-w-7xl" : "max-w-6xl"
        }`}
      >
        <Footer />
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-40 flex border-t border-slate-100 bg-white md:hidden">
        {mobileNavItems(publicNav).map((n) => {
          const active = isActive(pathname, n.href);
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`flex min-w-0 flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium transition ${
                active ? "text-brand-600" : "text-slate-400"
              }`}
            >
              <Icon href={n.href} className="h-6 w-6" />
              {n.short}
            </Link>
          );
        })}
        <Link
          href={user ? "/tai-khoan" : "/dang-nhap"}
          className={`flex min-w-0 flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium transition ${
            pathname.startsWith("/dang-nhap") || pathname.startsWith("/dang-ky")
              ? "text-brand-600"
              : "text-slate-400"
          }`}
        >
          <Icon href="/dang-nhap" className="h-6 w-6" />
          {user ? "Tài khoản" : "Đăng nhập"}
        </Link>
      </nav>
    </div>
  );
}
