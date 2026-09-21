"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { clearAuth, getStoredUser, type AuthUser } from "@/lib/auth";
import { AUTH_UI_ENABLED } from "@/lib/config";
import { AUTH_EVENT, LOGOUT_EVENT } from "@/lib/http";

export default function AuthMenu() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setUser(getStoredUser());
    const onLogout = () => setUser(null);
    const onAuth = (e: Event) => {
      const detail = (e as CustomEvent<AuthUser>).detail;
      if (detail) setUser(detail);
    };
    window.addEventListener(LOGOUT_EVENT, onLogout);
    window.addEventListener(AUTH_EVENT, onAuth);
    return () => {
      window.removeEventListener(LOGOUT_EVENT, onLogout);
      window.removeEventListener(AUTH_EVENT, onAuth);
    };
  }, []);

  async function logout() {
    const { authApi } = await import("@/lib/authApi");
    await authApi.logout();
    setUser(null);
    clearAuth();
    window.dispatchEvent(new CustomEvent(LOGOUT_EVENT));
    window.location.href = "/";
  }

  if (!user) {
    if (!AUTH_UI_ENABLED) return null;
    return (
      <Link
        href="/dang-nhap"
        className="inline-flex min-h-10 items-center justify-center rounded-full bg-brand-600 px-4 text-xs font-bold text-white shadow-sm transition hover:bg-brand-700 sm:px-5 sm:text-sm"
      >
        Đăng nhập
      </Link>
    );
  }

  return (
    <div className="relative flex items-center gap-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="max-w-[120px] truncate rounded-lg px-2.5 py-2 text-xs font-semibold text-slate-600 hover:bg-brand-50 hover:text-brand-600 sm:max-w-[160px] sm:px-3 sm:text-sm"
        title={user.email || ""}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {user.display_name || user.email}
      </button>
      {open && (
        <>
          <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label="Đóng" onClick={() => setOpen(false)} />
          <div
            role="menu"
            className="absolute right-0 top-full z-50 mt-1 w-48 overflow-hidden rounded-xl border border-slate-100 bg-white py-1 shadow-soft"
          >
            <Link
              href="/tai-khoan/ke-hoach"
              className="block px-4 py-2 text-sm font-medium text-slate-600 hover:bg-brand-50 hover:text-brand-600"
              onClick={() => setOpen(false)}
            >
              Tài khoản
            </Link>
            <Link
              href="/gio-hang"
              className="block px-4 py-2 text-sm font-medium text-slate-600 hover:bg-brand-50 hover:text-brand-600"
              onClick={() => setOpen(false)}
            >
              Giỏ hàng
            </Link>
            <Link
              href="/tai-khoan/doi-mat-khau"
              className="block px-4 py-2 text-sm font-medium text-slate-600 hover:bg-brand-50 hover:text-brand-600"
              onClick={() => setOpen(false)}
            >
              Đổi mật khẩu
            </Link>
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
