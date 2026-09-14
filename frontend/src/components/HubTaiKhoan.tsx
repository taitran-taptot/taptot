"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { getStoredUser, clearAuth } from "@/lib/auth";
import { LOGOUT_EVENT } from "@/lib/http";

const LINKS = [
  { href: "/tai-khoan/doi-mat-khau", title: "Đổi mật khẩu", desc: "Bảo vệ tài khoản của bạn." },
  { href: "/tai-khoan/don-hang", title: "Đơn hàng", desc: "Dụng cụ đã đặt." },
  { href: "/tai-khoan/gop-y", title: "Góp ý", desc: "Nói cho TAPTOT biết cần sửa gì." },
  { href: "/lien-he", title: "Tìm huấn luyện viên", desc: "Muốn có người kèm riêng." },
];

export default function HubTaiKhoan() {
  const router = useRouter();
  const user = getStoredUser();

  async function logout() {
    const { authApi } = await import("@/lib/authApi");
    await authApi.logout();
    clearAuth();
    window.dispatchEvent(new CustomEvent(LOGOUT_EVENT));
    router.push("/");
  }

  return (
    <section className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Tài khoản</h1>
        <p className="mt-1 text-sm text-slate-500">
          {user?.display_name || user?.email || "Người tập TAPTOT"}
        </p>
      </div>
      <div className="space-y-3">
        {LINKS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="block rounded-2xl bg-white p-5 shadow-soft transition hover:ring-2 hover:ring-brand-200"
          >
            <h2 className="font-bold text-slate-800">{item.title}</h2>
            <p className="mt-1 text-sm text-slate-500">{item.desc}</p>
          </Link>
        ))}
      </div>
      <button
        type="button"
        onClick={() => void logout()}
        className="w-full rounded-xl border border-rose-200 bg-white px-4 py-3 text-sm font-bold text-rose-600 hover:bg-rose-50"
      >
        Đăng xuất
      </button>
    </section>
  );
}
